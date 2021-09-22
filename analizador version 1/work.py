
REL_BIN_OPS = ["<", "<=", ">", ">=", "==", "!=",":=","=",":"]
ARITHM_BIN_OPS = ["+", "-", "*", "/"]
BOOL_BIN_OPS = ["&&", "||", "==", "!="]
BOOL_UNARY_OPS = ["!"]
Final_line=["/n"]

class lexema(object):
	"""docstring for lexema"""
	def __init__(self, sav):
		self.save = sav
		
class Lexer(object):

	def __init__(self):

		self.condition="S"#start
		self.save=""
		self.lecturaprimersimbolo = ""
		directorio = 'C:/Users/user/Documents/Documentos universidad 4 semestre/Compilador_PL0-master/analizador version 1/test/test.txt'
		self.test =open(directorio,"r")
		self.count=1
	def siguientelexico(self):
			
		while True:
			if self.lecturaprimersimbolo in Final_line:
				self.count+=1
					
			elif self.condition=="S":
				self.save=""
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
				elif self.lecturaprimersimbolo.is_integer():
					self.save+=self.lecturaprimersimbolo
					self.condition="Numbers"																					
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
			elif self.condition=="Numbers":
				if  self.lecturaprimersimbolo.is_integer():
					self.save+=self.lecturaprimersimbolo
					self.condition="Numbers"
				else:
					self.condition="finish"
					break								
			self.lecturaprimersimbolo=str(self.test.read(1))
				
		self.condition='S'
			#return self.save
		return lexema(self.save)

lexanalizer = Lexer()
lex = lexanalizer.siguientelexico()
while lex.save != "":
	
	print("lex:" + lex.save)
	lex = lexanalizer.siguientelexico()

		

		



					








	
