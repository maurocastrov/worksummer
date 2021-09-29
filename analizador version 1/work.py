
REL_BIN_OPS = ["<", "<=", ">", ">=", "==", "!=",":=","=",":"]
ARITHM_BIN_OPS = ["+", '-', '*']
BOOL_BIN_OPS = ["&&", "||", "==", "!="]
BOOL_UNARY_OPS = ["!"] 
Final_line=["\n"]
DELIM=[".",";",":",","]
ignore_comment = ["/","{","("]
class lexema(object):
	"""docstring for lexema"""
	def __init__(self, sav , cha, lin ):
		self.save = sav
		self.char=cha
		self.line=lin		
		
class Lexer(object):

	def __init__(self):

		self.condition="S"#start
		self.save=""
		self.lecturaprimersimbolo = ""
		directorio = 'C:/Users/user/Documents/Documentos universidad 4 semestre/Compilador_PL0-master/analizador version 1/test/test.txt'
		self.test =open(directorio,"r")
		self.line=1 
		self.char=0
	def siguientelexico(self):
			
		while True:



			if self.condition=="S":
				self.save=""
				self.firstline=self.line
				self.firstchar=self.char
				if  self.lecturaprimersimbolo.isalpha() or self.lecturaprimersimbolo=="_":
					self.save+=self.lecturaprimersimbolo
					self.condition="kotoba"
				
				elif self.lecturaprimersimbolo.isdigit():
					self.save+=self.lecturaprimersimbolo
					self.condition="bango"
				elif self.lecturaprimersimbolo in ARITHM_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="operations"	
				elif self.lecturaprimersimbolo in REL_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="relations"	
				elif self.lecturaprimersimbolo in BOOL_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="booleanbin"	
				elif self.lecturaprimersimbolo==".":
					self.save+=self.lecturaprimersimbolo
					self.condition="ten"
				elif self.lecturaprimersimbolo =="{" :
					self.condition="{"
				elif self.lecturaprimersimbolo =="/" :
					self.condition="/"
				elif self.lecturaprimersimbolo =="(" :
					self.condition="("
	
	
			elif self.condition=="kotoba":
				if  self.lecturaprimersimbolo.isalpha()or self.lecturaprimersimbolo=="_" or self.lecturaprimersimbolo.isdigit()  :
					self.save+=self.lecturaprimersimbolo
					self.condition="kotoba"
				else:
					self.condition="finish"
					break
			elif self.condition=="operations":
				if  self.lecturaprimersimbolo in ARITHM_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="operations"
				else:
					self.condition="finish"
					break
			elif self.condition=="relations":
				if  self.lecturaprimersimbolo in REL_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="relations"
				else:
					self.condition="finish"
					break
			elif self.condition=="booleanbin":
				if  self.lecturaprimersimbolo in BOOL_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="booleanbin"
				else:
					self.condition="finish"
					break	
			elif self.condition=="bango":
				if  self.lecturaprimersimbolo.isdigit():
					self.save+=self.lecturaprimersimbolo
					self.condition="bango"
				elif self.lecturaprimersimbolo==".":
					self.save+=self.lecturaprimersimbolo
					self.condition="ten"
				elif self.lecturaprimersimbolo.isalpha():
					self.condition="error"																														
				else:
					self.condition="finish"
					break	
			elif self.condition=="error":
				raise Exception('error')
					
			elif self.condition=="ten":
				if  self.lecturaprimersimbolo==".":
					presave=self.save[:-1]
					self.save="."
					self.condition="delim"
					return lexema(presave,self.firstchar, self.firstline)
				elif self.lecturaprimersimbolo.isdigit(): 	
					self.save+=self.lecturaprimersimbolo
					self.condition="float"																											
				else:
					self.condition="finish"
					break		
			elif self.condition=="delim":		
				if  self.save=="..":
					self.condition="finish"
					break
				elif self.lecturaprimersimbolo in DELIM :		
					self.save+=self.lecturaprimersimbolo
					self.condition="delim"																														
				else:	
					self.condition="finish"
					break	
			elif self.condition=="float":		
				if  self.lecturaprimersimbolo.isdigit(): 	
					self.save+=self.lecturaprimersimbolo
					self.condition="float"
				elif self.lecturaprimersimbolo.isalpha() or self.lecturaprimersimbolo==".":
					self.condition="error"
					#raise Exception('error')																											
				else:	
					self.condition="finish"
					break	
			elif self.condition=="/":	
				if self.lecturaprimersimbolo=="/"  :				
					self.condition="//"
				else:    
					
					self.condition="operations"
					continue	
			elif self.condition=="//":
				if self.lecturaprimersimbolo in Final_line: 
					self.condition='S'
			elif self.condition=="{":		
				if  self.lecturaprimersimbolo=="*":
					self.condition="{*"
					if 	self.lecturaprimersimbolo==")"
						self.condition='S'
					
				else: 	
					self.condition=="operations" 																										
			elif self.condition=="{*"
						
			self.lecturaprimersimbolo=str(self.test.read(1))
			self.char+=1	
			if self.lecturaprimersimbolo in Final_line:
				self.line+=1
				self.char=0	
		self.condition='S'
			#return self.save
		return lexema(self.save,self.firstchar,self.firstline)


lexanalizer = Lexer()
lex = lexanalizer.siguientelexico()
while lex.save != "":
	
	print("line:"+ str(lex.line) + " char" + str(lex.char) +" lex:" + lex.save)
	lex = lexanalizer.siguientelexico()

		

		



					








	
