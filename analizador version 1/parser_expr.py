from lexer import Lexer
import sys
import os
from error import sintetica, compiler_exception


class Numbernode(object):
    """docstring for Numbernode"""

    def __init__(self, lex):
        self.Numberlex = lex

    def print_result(self, a):
        return (" " * a + self.Numberlex.save)


class Identnode(object):

    def __init__(self, identificador):
        self.ind = identificador

    def print_result(self, a):
        return (" " * a + self.ind.save)


class Binnode(object):
    def __init__(self, left, right, operation_lex):
        self.hidari = left
        self.migi = right
        self.lexluthor = operation_lex

    def print_result(self, a):
        output = (" " * a + self.lexluthor.save)
        return output + "\n" + self.hidari.print_result(a + 1) + "\n" + self.migi.print_result(a + 1)


class parser(object):

    def __init__(self, fin):
        self.test = open(fin, "r")
        self.work = Lexer(fin)

    def par_expresion(self):
        left = self.par_term()
        operation = self.work.siguientelexicoget()
        while operation.save in ["+", "-"]:
            right = self.par_term()
            left = Binnode(left, right, operation)
            operation = self.work.siguientelexicoget()
        return left

    def par_term(self):
        left = self.par_factor()
        operation = self.work.siguientelexico()
        while operation.save in ["/", "*"]:
            right = self.par_factor()
            left = Binnode(left, right, operation)
            operation = self.work.siguientelexico()
        return left

    def par_factor(self):
        left = self.work.siguientelexico()
        if left.save == "(":
            izquierda = self.par_expresion()
            izquierda1 = self.work.siguientelexicoget()
            if izquierda1.save == ")":
                return izquierda
            else:
                raise sintetica('Dear Klenin there is a mistake in char: ' + str(izquierda1.char) + ' ,line: ' + str(
                    izquierda1.line))

        if left.type == "Numbers":
            return Numbernode(left)

        if left.type == "words":
            return Identnode(left)
        else:
            raise sintetica('Dear Klenin there is a mistake in char: ' + str(left.char) + ' ,line: ' + str(left.line))

# if __name__ == '__main__':
# 	par_alizer = parser()
# 	file2 = open("result\\test_parser.txt",'w') 
# 	try:
# 		parse_res = par_alizer.par_expresion()
# 		parse_res.print_result(0)
# 	except compiler_exception as e:
# 		print(e)
