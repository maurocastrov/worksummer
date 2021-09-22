

__version__    = "2.5"
__tabversion__ = "2.4"       # Table version



yaccdebug   = 1                # Debugging mode.  If set, yacc generates a
                               # a 'parser.out' file in the current directory

debug_file  = 'parser.out'     # Default name of the debugging file
tab_module  = 'parsetab'       # Default name of the table module
default_lr  = 'LALR'           # Default LR table generation method

error_count = 3                # Number of symbols that must be shifted to leave recovery mode

yaccdevel   = 0                # Set to True if developing yacc.  This turns off optimized
                               # implementations of certain functions.

import re, types, sys, cStringIO, md5, os.path

# Exception raised for yacc-related errors
class YaccError(Exception):   pass

# Exception raised for errors raised in production rules
class SyntaxError(Exception): pass


# Available instance types.  This is used when parsers are defined by a class.
# it's a little funky because I want to preserve backwards compatibility
# with Python 2.0 where types.ObjectType is undefined.

try:
    _INSTANCETYPE = (types.InstanceType, types.ObjectType)
except AttributeError:
    _INSTANCETYPE = types.InstanceType
    class object: pass     # Note: needed if no new-style classes present

#-----------------------------------------------------------------------------
#                        ===  LR Parsing Engine ===
#
# The following classes are used for the LR parser itself.  These are not
# used during table construction and are independent of the actual LR
# table generation algorithm
#-----------------------------------------------------------------------------

# This class is used to hold non-terminal grammar symbols during parsing.
# It normally has the following attributes set:
#        .type       = Grammar symbol type
#        .value      = Symbol value
#        .lineno     = Starting line number
#        .endlineno  = Ending line number (optional, set automatically)
#        .lexpos     = Starting lex position
#        .endlexpos  = Ending lex position (optional, set automatically)

class YaccSymbol:
    def __str__(self):    return self.type
    def __repr__(self):   return str(self)



class YaccProduction:
    def __init__(self,s,stack=None):
        self.slice = s
        self.stack = stack
        self.lexer = None
        self.parser= None
    def __getitem__(self,n):
        if n >= 0: return self.slice[n].value
        else: return self.stack[n].value

    def __setitem__(self,n,v):
        self.slice[n].value = v

    def __getslice__(self,i,j):
        return [s.value for s in self.slice[i:j]]

    def __len__(self):
        return len(self.slice)

    def lineno(self,n):
        return getattr(self.slice[n],"lineno",0)

    def linespan(self,n):
        startline = getattr(self.slice[n],"lineno",0)
        endline = getattr(self.slice[n],"endlineno",startline)
        return startline,endline

    def lexpos(self,n):
        return getattr(self.slice[n],"lexpos",0)

    def lexspan(self,n):
        startpos = getattr(self.slice[n],"lexpos",0)
        endpos = getattr(self.slice[n],"endlexpos",startpos)
        return startpos,endpos

    def error(self):
       raise SyntaxError


# The LR Parsing engine.   This is defined as a class so that multiple parsers
# can exist in the same process.  A user never instantiates this directly.
# Instead, the global yacc() function should be used to create a suitable Parser
# object.

class Parser:
    def __init__(self,magic=None):

        # This is a hack to keep users from trying to instantiate a Parser
        # object directly.

        if magic != "xyzzy":
            raise YaccError, "Can't directly instantiate Parser. Use yacc() instead."

        # Reset internal state
        self.productions = None          # List of productions
        self.errorfunc   = None          # Error handling function
        self.action      = { }           # LR Action table
        self.goto        = { }           # LR goto table
        self.require     = { }           # Attribute require table
        self.method      = "Unknown LR"  # Table construction method used

    def errok(self):
        self.errorok     = 1

    def restart(self):
        del self.statestack[:]
        del self.symstack[:]
        sym = YaccSymbol()
        sym.type = '$end'
        self.symstack.append(sym)
        self.statestack.append(0)

    def parse(self,input=None,lexer=None,debug=0,tracking=0,tokenfunc=None):
        if debug or yaccdevel:
            return self.parsedebug(input,lexer,debug,tracking,tokenfunc)
        elif tracking:
            return self.parseopt(input,lexer,debug,tracking,tokenfunc)
        else:
            return self.parseopt_notrack(input,lexer,debug,tracking,tokenfunc)
        

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parsedebug().
    #
    # This is the debugging enabled version of parse().  All changes made to the
    # parsing engine should be made here.   For the non-debugging version,
    # copy this code to a method parseopt() and delete all of the sections
    # enclosed in:
    #
    #      #--! DEBUG
    #      statements
    #      #--! DEBUG
    #
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def parsedebug(self,input=None,lexer=None,debug=0,tracking=0,tokenfunc=None):
        lookahead = None                 # Current lookahead symbol
        lookaheadstack = [ ]             # Stack of lookahead symbols
        actions = self.action            # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto              # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions       # Local reference to production list (to avoid lookup on self.)
        pslice  = YaccProduction(None)   # Production object passed to grammar rules
        errorcount = 0                   # Used during error recovery 
        endsym  = "$end"                 # End symbol
        # If no lexer was given, we will try to use the lex module
        if not lexer:
            import lex
            lexer = lex.lexer
        
        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
           # Tokenize function
           get_token = lexer.token
        else:
           get_token = tokenfunc

        # Set up the state and symbol stacks

        statestack = [ ]                # Stack of parsing states
        self.statestack = statestack
        symstack   = [ ]                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = endsym
        symstack.append(sym)
        state = 0
        while 1:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            # --! DEBUG
            if debug > 1:
                print 'state', state
            # --! DEBUG

            if not lookahead:
                if not lookaheadstack:
                    lookahead = get_token()     # Get the next token
                else:
                    lookahead = lookaheadstack.pop()
                if not lookahead:
                    lookahead = YaccSymbol()
                    lookahead.type = endsym

            # --! DEBUG
            if debug:
                errorlead = ("%s . %s" % (" ".join([xx.type for xx in symstack][1:]), str(lookahead))).lstrip()
            # --! DEBUG

            # Check the action table
            ltype = lookahead.type
            t = actions[state].get(ltype)

            # --! DEBUG
            if debug > 1:
                print 'action', t
            # --! DEBUG

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    if ltype is endsym:
                        # Error, end of input
                        sys.stderr.write("yacc: Parse error. EOF\n")
                        return
                    statestack.append(t)
                    state = t
                    
                    # --! DEBUG
                    if debug > 1:
                        sys.stderr.write("%-60s shift state %s\n" % (errorlead, t))
                    # --! DEBUG

                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount: errorcount -=1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None

                    # --! DEBUG
                    if debug > 1:
                        sys.stderr.write("%-60s reduce %d\n" % (errorlead, -t))
                    # --! DEBUG

                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym

                        # --! TRACKING
                        if tracking:
                           t1 = targ[1]
                           sym.lineno = t1.lineno
                           sym.lexpos = t1.lexpos
                           t1 = targ[-1]
                           sym.endlineno = getattr(t1,"endlineno",t1.lineno)
                           sym.endlexpos = getattr(t1,"endlexpos",t1.lexpos)

                        # --! TRACKING

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ
                        
                        try:
                            # Call the grammar rule with our special slice object
                            p.func(pslice)
                            del symstack[-plen:]
                            del statestack[-plen:]
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
                    else:

                        # --! TRACKING
                        if tracking:
                           sym.lineno = lexer.lineno
                           sym.lexpos = lexer.lexpos
                        # --! TRACKING

                        targ = [ sym ]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            p.func(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    return getattr(n,"value",None)

            if t == None:

                # --! DEBUG
                if debug:
                    sys.stderr.write(errorlead + "\n")
                # --! DEBUG

                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = 0
                    errtoken = lookahead
                    if errtoken.type is endsym:
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        global errok,token,restart
                        errok = self.errok        # Set some special functions available in error recovery
                        token = get_token
                        restart = self.restart
                        tok = self.errorfunc(errtoken)
                        del errok, token, restart   # Delete special functions

                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken,"lineno"): lineno = lookahead.lineno
                            else: lineno = 0
                            if lineno:
                                sys.stderr.write("yacc: Syntax error at line %d, token=%s\n" % (lineno, errtoken.type))
                            else:
                                sys.stderr.write("yacc: Syntax error, token=%s" % errtoken.type)
                        else:
                            sys.stderr.write("yacc: Parse error in input. EOF\n")
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type is not endsym:
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type is endsym:
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        lookahead = None
                        continue
                    t = YaccSymbol()
                    t.type = 'error'
                    if hasattr(lookahead,"lineno"):
                        t.lineno = lookahead.lineno
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    symstack.pop()
                    statestack.pop()
                    state = statestack[-1]       # Potential bug fix

                continue

            # Call an error function here
            raise RuntimeError, "yacc: internal parser error!!!\n"

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parseopt().
    #
    # Optimized version of parse() method.  DO NOT EDIT THIS CODE DIRECTLY.
    # Edit the debug version above, then copy any modifications to the method
    # below while removing #--! DEBUG sections.
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


    def parseopt(self,input=None,lexer=None,debug=0,tracking=0,tokenfunc=None):
        lookahead = None                 # Current lookahead symbol
        lookaheadstack = [ ]             # Stack of lookahead symbols
        actions = self.action            # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto              # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions       # Local reference to production list (to avoid lookup on self.)
        pslice  = YaccProduction(None)   # Production object passed to grammar rules
        errorcount = 0                   # Used during error recovery 

        # If no lexer was given, we will try to use the lex module
        if not lexer:
            import lex
            lexer = lex.lexer
        
        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
           # Tokenize function
           get_token = lexer.token
        else:
           get_token = tokenfunc

        # Set up the state and symbol stacks

        statestack = [ ]                # Stack of parsing states
        self.statestack = statestack
        symstack   = [ ]                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = '$end'
        symstack.append(sym)
        state = 0
        while 1:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            if not lookahead:
                if not lookaheadstack:
                    lookahead = get_token()     # Get the next token
                else:
                    lookahead = lookaheadstack.pop()
                if not lookahead:
                    lookahead = YaccSymbol()
                    lookahead.type = '$end'

            # Check the action table
            ltype = lookahead.type
            t = actions[state].get(ltype)

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    if ltype == '$end':
                        # Error, end of input
                        sys.stderr.write("yacc: Parse error. EOF\n")
                        return
                    statestack.append(t)
                    state = t

                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount: errorcount -=1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None

                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym

                        # --! TRACKING
                        if tracking:
                           t1 = targ[1]
                           sym.lineno = t1.lineno
                           sym.lexpos = t1.lexpos
                           t1 = targ[-1]
                           sym.endlineno = getattr(t1,"endlineno",t1.lineno)
                           sym.endlexpos = getattr(t1,"endlexpos",t1.lexpos)

                        # --! TRACKING

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ
                        
                        try:
                            # Call the grammar rule with our special slice object
                            p.func(pslice)
                            del symstack[-plen:]
                            del statestack[-plen:]
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
                    else:

                        # --! TRACKING
                        if tracking:
                           sym.lineno = lexer.lineno
                           sym.lexpos = lexer.lexpos
                        # --! TRACKING

                        targ = [ sym ]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            p.func(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    return getattr(n,"value",None)

            if t == None:

                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = 0
                    errtoken = lookahead
                    if errtoken.type == '$end':
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        global errok,token,restart
                        errok = self.errok        # Set some special functions available in error recovery
                        token = get_token
                        restart = self.restart
                        tok = self.errorfunc(errtoken)
                        del errok, token, restart   # Delete special functions

                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken,"lineno"): lineno = lookahead.lineno
                            else: lineno = 0
                            if lineno:
                                sys.stderr.write("yacc: Syntax error at line %d, token=%s\n" % (lineno, errtoken.type))
                            else:
                                sys.stderr.write("yacc: Syntax error, token=%s" % errtoken.type)
                        else:
                            sys.stderr.write("yacc: Parse error in input. EOF\n")
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != '$end':
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == '$end':
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        lookahead = None
                        continue
                    t = YaccSymbol()
                    t.type = 'error'
                    if hasattr(lookahead,"lineno"):
                        t.lineno = lookahead.lineno
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    symstack.pop()
                    statestack.pop()
                    state = statestack[-1]       # Potential bug fix

                continue

            # Call an error function here
            raise RuntimeError, "yacc: internal parser error!!!\n"

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parseopt_notrack().
    #
    # Optimized version of parseopt() with line number tracking removed. 
    # DO NOT EDIT THIS CODE DIRECTLY. Copy the optimized version and remove
    # code in the #--! TRACKING sections
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def parseopt_notrack(self,input=None,lexer=None,debug=0,tracking=0,tokenfunc=None):
        lookahead = None                 # Current lookahead symbol
        lookaheadstack = [ ]             # Stack of lookahead symbols
        actions = self.action            # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto              # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions       # Local reference to production list (to avoid lookup on self.)
        pslice  = YaccProduction(None)   # Production object passed to grammar rules
        errorcount = 0                   # Used during error recovery 

        # If no lexer was given, we will try to use the lex module
        if not lexer:
            import lex
            lexer = lex.lexer
        
        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
           # Tokenize function
           get_token = lexer.token
        else:
           get_token = tokenfunc

        # Set up the state and symbol stacks

        statestack = [ ]                # Stack of parsing states
        self.statestack = statestack
        symstack   = [ ]                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = '$end'
        symstack.append(sym)
        state = 0
        while 1:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            if not lookahead:
                if not lookaheadstack:
                    lookahead = get_token()     # Get the next token
                else:
                    lookahead = lookaheadstack.pop()
                if not lookahead:
                    lookahead = YaccSymbol()
                    lookahead.type = '$end'

            # Check the action table
            ltype = lookahead.type
            t = actions[state].get(ltype)

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    if ltype == '$end':
                        # Error, end of input
                        sys.stderr.write("yacc: Parse error. EOF\n")
                        return
                    statestack.append(t)
                    state = t

                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount: errorcount -=1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None

                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ
                        
                        try:
                            # Call the grammar rule with our special slice object
                            p.func(pslice)
                            del symstack[-plen:]
                            del statestack[-plen:]
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
                    else:

                        targ = [ sym ]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            p.func(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    return getattr(n,"value",None)

            if t == None:

                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = 0
                    errtoken = lookahead
                    if errtoken.type == '$end':
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        global errok,token,restart
                        errok = self.errok        # Set some special functions available in error recovery
                        token = get_token
                        restart = self.restart
                        tok = self.errorfunc(errtoken)
                        del errok, token, restart   # Delete special functions

                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken,"lineno"): lineno = lookahead.lineno
                            else: lineno = 0
                            if lineno:
                                sys.stderr.write("yacc: Syntax error at line %d, token=%s\n" % (lineno, errtoken.type))
                            else:
                                sys.stderr.write("yacc: Syntax error, token=%s" % errtoken.type)
                        else:
                            sys.stderr.write("yacc: Parse error in input. EOF\n")
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != '$end':
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == '$end':
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        lookahead = None
                        continue
                    t = YaccSymbol()
                    t.type = 'error'
                    if hasattr(lookahead,"lineno"):
                        t.lineno = lookahead.lineno
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    symstack.pop()
                    statestack.pop()
                    state = statestack[-1]       # Potential bug fix

                continue

            # Call an error function here
            raise RuntimeError, "yacc: internal parser error!!!\n"





# -----------------------------------------------------------------------------
#                           === GRAMMAR FUNCTIONS ===
#
# The following global variables and functions are used to store, manipulate,
# and verify the grammar rules specified by the user.
# -----------------------------------------------------------------------------

# Initialize all of the global variables used during grammar construction
def initialize_vars():
    global Productions, Prodnames, Prodmap, Terminals
    global Nonterminals, First, Follow, Precedence, UsedPrecedence, LRitems
    global Errorfunc, Signature, Requires

    Productions  = [None]  # A list of all of the productions.  The first
                           # entry is always reserved for the purpose of
                           # building an augmented grammar

    Prodnames    = { }     # A dictionary mapping the names of nonterminals to a list of all
                           # productions of that nonterminal.

    Prodmap      = { }     # A dictionary that is only used to detect duplicate
                           # productions.

    Terminals    = { }     # A dictionary mapping the names of terminal symbols to a
                           # list of the rules where they are used.

    Nonterminals = { }     # A dictionary mapping names of nonterminals to a list
                           # of rule numbers where they are used.

    First        = { }     # A dictionary of precomputed FIRST(x) symbols

    Follow       = { }     # A dictionary of precomputed FOLLOW(x) symbols

    Precedence   = { }     # Precedence rules for each terminal. Contains tuples of the
                           # form ('right',level) or ('nonassoc', level) or ('left',level)

    UsedPrecedence = { }   # Precedence rules that were actually used by the grammer.
                           # This is only used to provide error checking and to generate
                           # a warning about unused precedence rules.

    LRitems      = [ ]     # A list of all LR items for the grammar.  These are the
                           # productions with the "dot" like E -> E . PLUS E

    Errorfunc    = None    # User defined error handler

    Signature    = md5.new()   # Digital signature of the grammar rules, precedence
                               # and other information.  Used to determined when a
                               # parsing table needs to be regenerated.
    
    Signature.update(__tabversion__)

    Requires     = { }     # Requires list

    # File objects used when creating the parser.out debugging file
    global _vf, _vfc
    _vf           = cStringIO.StringIO()
    _vfc          = cStringIO.StringIO()



class Production:
    def __init__(self,**kw):
        for k,v in kw.items():
            setattr(self,k,v)
        self.lr_index = -1
        self.lr0_added = 0    # Flag indicating whether or not added to LR0 closure
        self.lr1_added = 0    # Flag indicating whether or not added to LR1
        self.usyms = [ ]
        self.lookaheads = { }
        self.lk_added = { }
        self.setnumbers = [ ]

    def __str__(self):
        if self.prod:
            s = "%s -> %s" % (self.name," ".join(self.prod))
        else:
            s = "%s -> <empty>" % self.name
        return s

    def __repr__(self):
        return str(self)

    # Compute lr_items from the production
    def lr_item(self,n):
        if n > len(self.prod): return None
        p = Production()
        p.name = self.name
        p.prod = list(self.prod)
        p.number = self.number
        p.lr_index = n
        p.lookaheads = { }
        p.setnumbers = self.setnumbers
        p.prod.insert(n,".")
        p.prod = tuple(p.prod)
        p.len = len(p.prod)
        p.usyms = self.usyms

        # Precompute list of productions immediately following
        try:
            p.lrafter = Prodnames[p.prod[n+1]]
        except (IndexError,KeyError),e:
            p.lrafter = []
        try:
            p.lrbefore = p.prod[n-1]
        except IndexError:
            p.lrbefore = None

        return p

class MiniProduction:
    pass

# regex matching identifiers
_is_identifier = re.compile(r'^[a-zA-Z0-9_-]+$')


def add_production(f,file,line,prodname,syms):

    if Terminals.has_key(prodname):
        sys.stderr.write("%s:%d: Illegal rule name '%s'. Already defined as a token.\n" % (file,line,prodname))
        return -1
    if prodname == 'error':
        sys.stderr.write("%s:%d: Illegal rule name '%s'. error is a reserved word.\n" % (file,line,prodname))
        return -1

    if not _is_identifier.match(prodname):
        sys.stderr.write("%s:%d: Illegal rule name '%s'\n" % (file,line,prodname))
        return -1

    for x in range(len(syms)):
        s = syms[x]
        if s[0] in "'\"":
             try:
                 c = eval(s)
                 if (len(c) > 1):
                      sys.stderr.write("%s:%d: Literal token %s in rule '%s' may only be a single character\n" % (file,line,s, prodname))
                      return -1
                 if not Terminals.has_key(c):
                      Terminals[c] = []
                 syms[x] = c
                 continue
             except SyntaxError:
                 pass
        if not _is_identifier.match(s) and s != '%prec':
            sys.stderr.write("%s:%d: Illegal name '%s' in rule '%s'\n" % (file,line,s, prodname))
            return -1

    # See if the rule is already in the rulemap
    map = "%s -> %s" % (prodname,syms)
    if Prodmap.has_key(map):
        m = Prodmap[map]
        sys.stderr.write("%s:%d: Duplicate rule %s.\n" % (file,line, m))
        sys.stderr.write("%s:%d: Previous definition at %s:%d\n" % (file,line, m.file, m.line))
        return -1

    p = Production()
    p.name = prodname
    p.prod = syms
    p.file = file
    p.line = line
    p.func = f
    p.number = len(Productions)


    Productions.append(p)
    Prodmap[map] = p
    if not Nonterminals.has_key(prodname):
        Nonterminals[prodname] = [ ]

    # Add all terminals to Terminals
    i = 0
    while i < len(p.prod):
        t = p.prod[i]
        if t == '%prec':
            try:
                precname = p.prod[i+1]
            except IndexError:
                sys.stderr.write("%s:%d: Syntax error. Nothing follows %%prec.\n" % (p.file,p.line))
                return -1

            prec = Precedence.get(precname,None)
            if not prec:
                sys.stderr.write("%s:%d: Nothing known about the precedence of '%s'\n" % (p.file,p.line,precname))
                return -1
            else:
                p.prec = prec
                UsedPrecedence[precname] = 1
            del p.prod[i]
            del p.prod[i]
            continue

        if Terminals.has_key(t):
            Terminals[t].append(p.number)
            # Is a terminal.  We'll assign a precedence to p based on this
            if not hasattr(p,"prec"):
                p.prec = Precedence.get(t,('right',0))
        else:
            if not Nonterminals.has_key(t):
                Nonterminals[t] = [ ]
            Nonterminals[t].append(p.number)
        i += 1

    if not hasattr(p,"prec"):
        p.prec = ('right',0)

    # Set final length of productions
    p.len  = len(p.prod)
    p.prod = tuple(p.prod)

    # Calculate unique syms in the production
    p.usyms = [ ]
    for s in p.prod:
        if s not in p.usyms:
            p.usyms.append(s)

    # Add to the global productions list
    try:
        Prodnames[p.name].append(p)
    except KeyError:
        Prodnames[p.name] = [ p ]
    return 0

# Given a raw rule function, this function rips out its doc string
# and adds rules to the grammar

def add_function(f):
    line = f.func_code.co_firstlineno
    file = f.func_code.co_filename
    error = 0

    if isinstance(f,types.MethodType):
        reqdargs = 2
    else:
        reqdargs = 1

    if f.func_code.co_argcount > reqdargs:
        sys.stderr.write("%s:%d: Rule '%s' has too many arguments.\n" % (file,line,f.__name__))
        return -1

    if f.func_code.co_argcount < reqdargs:
        sys.stderr.write("%s:%d: Rule '%s' requires an argument.\n" % (file,line,f.__name__))
        return -1

    if f.__doc__:
        # Split the doc string into lines
        pstrings = f.__doc__.splitlines()
        lastp = None
        dline = line
        for ps in pstrings:
            dline += 1
            p = ps.split()
            if not p: continue
            try:
                if p[0] == '|':
                    # This is a continuation of a previous rule
                    if not lastp:
                        sys.stderr.write("%s:%d: Misplaced '|'.\n" % (file,dline))
                        return -1
                    prodname = lastp
                    if len(p) > 1:
                        syms = p[1:]
                    else:
                        syms = [ ]
                else:
                    prodname = p[0]
                    lastp = prodname
                    assign = p[1]
                    if len(p) > 2:
                        syms = p[2:]
                    else:
                        syms = [ ]
                    if assign != ':' and assign != '::=':
                        sys.stderr.write("%s:%d: Syntax error. Expected ':'\n" % (file,dline))
                        return -1


                e = add_production(f,file,dline,prodname,syms)
                error += e


            except StandardError:
                sys.stderr.write("%s:%d: Syntax error in rule '%s'\n" % (file,dline,ps))
                error -= 1
    else:
        sys.stderr.write("%s:%d: No documentation string specified in function '%s'\n" % (file,line,f.__name__))
    return error

# -----------------------------------------------------------------------------
# add_precedence()
#
# Given a list of precedence rules, add to the precedence table.
# -----------------------------------------------------------------------------

def add_precedence(plist):
    plevel = 0
    error = 0
    for p in plist:
        plevel += 1
        try:
            prec = p[0]
            terms = p[1:]
            if prec != 'left' and prec != 'right' and prec != 'nonassoc':
                sys.stderr.write("yacc: Invalid precedence '%s'\n" % prec)
                return -1
            for t in terms:
                if Precedence.has_key(t):
                    sys.stderr.write("yacc: Precedence already specified for terminal '%s'\n" % t)
                    error += 1
                    continue
                Precedence[t] = (prec,plevel)
        except:
            sys.stderr.write("yacc: Invalid precedence table.\n")
            error += 1

    return error

# -----------------------------------------------------------------------------
# check_precedence()
#
# Checks the use of the Precedence tables.  This makes sure all of the symbols
# are terminals or were used with %prec
# -----------------------------------------------------------------------------

def check_precedence():
    error = 0
    for precname in Precedence.keys():
        if not (Terminals.has_key(precname) or UsedPrecedence.has_key(precname)):
            sys.stderr.write("yacc: Precedence rule '%s' defined for unknown symbol '%s'\n" % (Precedence[precname][0],precname))
            error += 1
    return error

# -----------------------------------------------------------------------------
# augment_grammar()
#
# Compute the augmented grammar.  This is just a rule S' -> start where start
# is the starting symbol.
# -----------------------------------------------------------------------------

def augment_grammar(start=None):
    if not start:
        start = Productions[1].name
    Productions[0] = Production(name="S'",prod=[start],number=0,len=1,prec=('right',0),func=None)
    Productions[0].usyms = [ start ]
    Nonterminals[start].append(0)




# Global variables for the LR parsing engine
def lr_init_vars():
    global _lr_action, _lr_goto, _lr_method
    global _lr_goto_cache, _lr0_cidhash

    _lr_action       = { }        # Action table
    _lr_goto         = { }        # Goto table
    _lr_method       = "Unknown"  # LR method used
    _lr_goto_cache   = { }
    _lr0_cidhash     = { }



def lr_write_tables(modulename=tab_module,outputdir=''):
    if isinstance(modulename, types.ModuleType):
        print >>sys.stderr, "Warning module %s is inconsistent with the grammar (ignored)" % modulename
        return

    basemodulename = modulename.split(".")[-1]
    filename = os.path.join(outputdir,basemodulename) + ".py"
    try:
        f = open(filename,"w")

        f.write("""
# %s
# This file is automatically generated. Do not edit.

_lr_method = %s

_lr_signature = %s
""" % (filename, repr(_lr_method), repr(Signature.digest())))

        # Change smaller to 0 to go back to original tables
        smaller = 1

        # Factor out names to try and make smaller
        if smaller:
            items = { }

            for s,nd in _lr_action.items():
               for name,v in nd.items():
                  i = items.get(name)
                  if not i:
                     i = ([],[])
                     items[name] = i
                  i[0].append(s)
                  i[1].append(v)

            f.write("\n_lr_action_items = {")
            for k,v in items.items():
                f.write("%r:([" % k)
                for i in v[0]:
                    f.write("%r," % i)
                f.write("],[")
                for i in v[1]:
                    f.write("%r," % i)

                f.write("]),")
            f.write("}\n")

            f.write("""
_lr_action = { }
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _lr_action.has_key(_x):  _lr_action[_x] = { }
      _lr_action[_x][_k] = _y
del _lr_action_items
""")

        else:
            f.write("\n_lr_action = { ");
            for k,v in _lr_action.items():
                f.write("(%r,%r):%r," % (k[0],k[1],v))
            f.write("}\n");

        if smaller:
            # Factor out names to try and make smaller
            items = { }

            for s,nd in _lr_goto.items():
               for name,v in nd.items():
                  i = items.get(name)
                  if not i:
                     i = ([],[])
                     items[name] = i
                  i[0].append(s)
                  i[1].append(v)

            f.write("\n_lr_goto_items = {")
            for k,v in items.items():
                f.write("%r:([" % k)
                for i in v[0]:
                    f.write("%r," % i)
                f.write("],[")
                for i in v[1]:
                    f.write("%r," % i)

                f.write("]),")
            f.write("}\n")

            f.write("""
_lr_goto = { }
for _k, _v in _lr_goto_items.items():
   for _x,_y in zip(_v[0],_v[1]):
       if not _lr_goto.has_key(_x): _lr_goto[_x] = { }
       _lr_goto[_x][_k] = _y
del _lr_goto_items
""")
        else:
            f.write("\n_lr_goto = { ");
            for k,v in _lr_goto.items():
                f.write("(%r,%r):%r," % (k[0],k[1],v))
            f.write("}\n");

        # Write production table
        f.write("_lr_productions = [\n")
        for p in Productions:
            if p:
                if (p.func):
                    f.write("  (%r,%d,%r,%r,%d),\n" % (p.name, p.len, p.func.__name__,p.file,p.line))
                else:
                    f.write("  (%r,%d,None,None,None),\n" % (p.name, p.len))
            else:
                f.write("  None,\n")
        f.write("]\n")

        f.close()

    except IOError,e:
        print >>sys.stderr, "Unable to create '%s'" % filename
        print >>sys.stderr, e
        return

def lr_read_tables(module=tab_module,optimize=0):
    global _lr_action, _lr_goto, _lr_productions, _lr_method
    try:
        if isinstance(module,types.ModuleType):
            parsetab = module
        else:
            exec "import %s as parsetab" % module

        if (optimize) or (Signature.digest() == parsetab._lr_signature):
            _lr_action = parsetab._lr_action
            _lr_goto   = parsetab._lr_goto
            _lr_productions = parsetab._lr_productions
            _lr_method = parsetab._lr_method
            return 1
        else:
            return 0

    except (ImportError,AttributeError):
        return 0


# -----------------------------------------------------------------------------
# yacc(module)
#
# Build the parser module
# -----------------------------------------------------------------------------

def yacc(method=default_lr, debug=yaccdebug, module=None, tabmodule=tab_module, start=None, check_recursion=1, optimize=0,write_tables=1,debugfile=debug_file,outputdir=''):
    global yaccdebug
    yaccdebug = debug

    initialize_vars()
    files = { }
    error = 0


    # Add parsing method to signature
    Signature.update(method)

    # If a "module" parameter was supplied, extract its dictionary.
    # Note: a module may in fact be an instance as well.

    if module:
        # User supplied a module object.
        if isinstance(module, types.ModuleType):
            ldict = module.__dict__
        elif isinstance(module, _INSTANCETYPE):
            _items = [(k,getattr(module,k)) for k in dir(module)]
            ldict = { }
            for i in _items:
                ldict[i[0]] = i[1]
        else:
            raise ValueError,"Expected a module"

    else:
        # No module given.  We might be able to get information from the caller.
        # Throw an exception and unwind the traceback to get the globals

        try:
            raise RuntimeError
        except RuntimeError:
            e,b,t = sys.exc_info()
            f = t.tb_frame
            f = f.f_back           # Walk out to our calling function
            if f.f_globals is f.f_locals:   # Collect global and local variations from caller
               ldict = f.f_globals
            else:
               ldict = f.f_globals.copy()
               ldict.update(f.f_locals)

    # Add starting symbol to signature
    if not start:
        start = ldict.get("start",None)
    if start:
        Signature.update(start)

    # Look for error handler
    ef = ldict.get('p_error',None)
    if ef:
        if isinstance(ef,types.FunctionType):
            ismethod = 0
        elif isinstance(ef, types.MethodType):
            ismethod = 1
        else:
            raise YaccError,"'p_error' defined, but is not a function or method."
        eline = ef.func_code.co_firstlineno
        efile = ef.func_code.co_filename
        files[efile] = None

        if (ef.func_code.co_argcount != 1+ismethod):
            raise YaccError,"%s:%d: p_error() requires 1 argument." % (efile,eline)
        global Errorfunc
        Errorfunc = ef
    else:
        print >>sys.stderr, "yacc: Warning. no p_error() function is defined."

    # If running in optimized mode.  We're going to read tables instead

    if (optimize and lr_read_tables(tabmodule,1)):
        # Read parse table
        del Productions[:]
        for p in _lr_productions:
            if not p:
                Productions.append(None)
            else:
                m = MiniProduction()
                m.name = p[0]
                m.len  = p[1]
                m.file = p[3]
                m.line = p[4]
                if p[2]:
                    m.func = ldict[p[2]]
                Productions.append(m)

    else:
        # Get the tokens map
        if (module and isinstance(module,_INSTANCETYPE)):
            tokens = getattr(module,"tokens",None)
        else:
            tokens = ldict.get("tokens",None)

        if not tokens:
            raise YaccError,"module does not define a list 'tokens'"
        if not (isinstance(tokens,types.ListType) or isinstance(tokens,types.TupleType)):
            raise YaccError,"tokens must be a list or tuple."

        # Check to see if a requires dictionary is defined.
        requires = ldict.get("require",None)
        if requires:
            if not (isinstance(requires,types.DictType)):
                raise YaccError,"require must be a dictionary."

            for r,v in requires.items():
                try:
                    if not (isinstance(v,types.ListType)):
                        raise TypeError
                    v1 = [x.split(".") for x in v]
                    Requires[r] = v1
                except StandardError:
                    print >>sys.stderr, "Invalid specification for rule '%s' in require. Expected a list of strings" % r


        # Build the dictionary of terminals.  We a record a 0 in the
        # dictionary to track whether or not a terminal is actually
        # used in the grammar

        if 'error' in tokens:
            print >>sys.stderr, "yacc: Illegal token 'error'.  Is a reserved word."
            raise YaccError,"Illegal token name"

        for n in tokens:
            if Terminals.has_key(n):
                print >>sys.stderr, "yacc: Warning. Token '%s' multiply defined." % n
            Terminals[n] = [ ]

        Terminals['error'] = [ ]

        # Get the precedence map (if any)
        prec = ldict.get("precedence",None)
        if prec:
            if not (isinstance(prec,types.ListType) or isinstance(prec,types.TupleType)):
                raise YaccError,"precedence must be a list or tuple."
            add_precedence(prec)
            Signature.update(repr(prec))

        for n in tokens:
            if not Precedence.has_key(n):
                Precedence[n] = ('right',0)         # Default, right associative, 0 precedence

        # Get the list of built-in functions with p_ prefix
        symbols = [ldict[f] for f in ldict.keys()
               if (type(ldict[f]) in (types.FunctionType, types.MethodType) and ldict[f].__name__[:2] == 'p_'
                   and ldict[f].__name__ != 'p_error')]

        # Check for non-empty symbols
        if len(symbols) == 0:
            raise YaccError,"no rules of the form p_rulename are defined."

        # Sort the symbols by line number
        symbols.sort(lambda x,y: cmp(x.func_code.co_firstlineno,y.func_code.co_firstlineno))

        # Add all of the symbols to the grammar
        for f in symbols:
            if (add_function(f)) < 0:
                error += 1
            else:
                files[f.func_code.co_filename] = None

        # Make a signature of the docstrings
        for f in symbols:
            if f.__doc__:
                Signature.update(f.__doc__)

        lr_init_vars()

        if error:
            raise YaccError,"Unable to construct parser."

        if not lr_read_tables(tabmodule):

            # Validate files
            for filename in files.keys():
                if not validate_file(filename):
                    error = 1

            # Validate dictionary
            validate_dict(ldict)

            if start and not Prodnames.has_key(start):
                raise YaccError,"Bad starting symbol '%s'" % start

            augment_grammar(start)
            error = verify_productions(cycle_check=check_recursion)
            otherfunc = [ldict[f] for f in ldict.keys()
               if (type(f) in (types.FunctionType,types.MethodType) and ldict[f].__name__[:2] != 'p_')]

            # Check precedence rules
            if check_precedence():
                error = 1

            if error:
                raise YaccError,"Unable to construct parser."

            build_lritems()
            compute_first1()
            compute_follow(start)

            if method in ['SLR','LALR']:
                lr_parse_table(method)
            else:
                raise YaccError, "Unknown parsing method '%s'" % method

            if write_tables:
                lr_write_tables(tabmodule,outputdir)

            if yaccdebug:
                try:
                    f = open(os.path.join(outputdir,debugfile),"w")
                    f.write(_vfc.getvalue())
                    f.write("\n\n")
                    f.write(_vf.getvalue())
                    f.close()
                except IOError,e:
                    print >>sys.stderr, "yacc: can't create '%s'" % debugfile,e

    # Made it here.   Create a parser object and set up its internal state.
    # Set global parse() method to bound method of parser object.

    p = Parser("xyzzy")
    p.productions = Productions
    p.errorfunc = Errorfunc
    p.action = _lr_action
    p.goto   = _lr_goto
    p.method = _lr_method
    p.require = Requires

    global parse
    parse = p.parse

    global parser
    parser = p

    # Clean up all of the globals we created
    if (not optimize):
        yacc_cleanup()
    return p

# yacc_cleanup function.  Delete all of the global variables
# used during table construction

def yacc_cleanup():
    global _lr_action, _lr_goto, _lr_method, _lr_goto_cache
    del _lr_action, _lr_goto, _lr_method, _lr_goto_cache

    global Productions, Prodnames, Prodmap, Terminals
    global Nonterminals, First, Follow, Precedence, UsedPrecedence, LRitems
    global Errorfunc, Signature, Requires

    del Productions, Prodnames, Prodmap, Terminals
    del Nonterminals, First, Follow, Precedence, UsedPrecedence, LRitems
    del Errorfunc, Signature, Requires

    global _vf, _vfc
    del _vf, _vfc


# Stub that raises an error if parsing is attempted without first calling yacc()
def parse(*args,**kwargs):
    raise YaccError, "yacc: No parser built with yacc()"
