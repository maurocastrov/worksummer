import sys
import os
#-*-coding: utf-8 -*-

REL_BIN_OPS = ["<", "<=", ">", ">=", "==", "!=",":=","=",":"]
ARITHM_BIN_OPS = ["+", '-',"*","/"]
BOOL_BIN_OPS = ["&&", "||", "==", "!="]
BOOL_UNARY_OPS = ["!"] 
Final_line=["\n"]
DELIM=[".",";",":",",",")"]
ignore_comment = ["/","{","("]
reservadas = ['array','downto','function','of','repeat','until','begin','else','goto','packed','set','var','case','end','if','procedure','then','while','const','file','label','program','to','with','do','for','nil','record','type'
		]

class lexema(object):
	"""docstring for lexema"""
	def __init__(self, sav , cha, lin, typ ):
		self.save = sav
		self.char=cha
		self.line=lin	
		self.type=typ
class Lexer(object):

	def __init__(self):

		self.condition="S"#start
		self.save=""
		self.lecturaprimersimbolo = " "
		directorio = 'C:/Users/user/Documents/Documentos universidad 4 semestre/Compilador_PL0-master/analizador version 1/test/test.txt'
		self.test =open(directorio,"r")
		self.line=1 
		self.char=0
		self.type=self.condition
		self.conditn = ""
	def siguientelexico(self):
			
		while True:
			if self.condition=="S":
				self.save=""
				self.firstline=self.line
				self.firstchar=self.char
				if self.lecturaprimersimbolo =="":
					break

				elif self.lecturaprimersimbolo.isalpha() or self.lecturaprimersimbolo=="_":
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
				elif self.lecturaprimersimbolo in DELIM:
					self.save+=self.lecturaprimersimbolo
					self.condition="delim"					
				elif self.lecturaprimersimbolo==".":
					self.save+=self.lecturaprimersimbolo
					self.condition="delim"
				elif self.lecturaprimersimbolo =="{" :
					self.condition="{"
				elif self.lecturaprimersimbolo =="/" :
					self.save+=self.lecturaprimersimbolo
					self.condition="/"
				elif self.lecturaprimersimbolo =="(" :
					self.save+=self.lecturaprimersimbolo
					self.condition="("
				elif self.lecturaprimersimbolo=="(*" :
					self.condition="(*"	
				elif self.lecturaprimersimbolo in reservadas:
					self.save+="reservacion"		
	
			elif self.condition=="kotoba":
				if  self.lecturaprimersimbolo.isalpha()or self.lecturaprimersimbolo=="_" or self.lecturaprimersimbolo.isdigit()  :
					self.save+=self.lecturaprimersimbolo
					self.condition="kotoba"
				else:
					# self.condition="finish"
					break
			elif self.condition=="operations":
				if  self.lecturaprimersimbolo in ARITHM_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="operations"
				else:
					# self.condition="finish"
					break
			elif self.condition=="relations":
				if  self.lecturaprimersimbolo in REL_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="relations"

				else:
					# self.condition="finish"
					break
			elif self.condition=="booleanbin":
				if  self.lecturaprimersimbolo in BOOL_BIN_OPS:
					self.save+=self.lecturaprimersimbolo
					self.condition="booleanbin"
				else:
					# self.condition="finish"
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
					# self.condition="finish"
					break	
			elif self.condition=="error":
				raise Exception('Dear Klenin there is a mistake in char: ' + str(self.firstchar)+ ' ,line: ' + str(self.firstline) )

			elif self.condition =="especial":
				self.save+=self.lecturaprimersimbolo
				self.condition="especial"
				if self.lecturaprimersimbolo.isdigit():
					self.condition="especial"
				elif self.lecturaprimersimbolo=="-":
				 	self.condition="negative"						
				else:
					
					print("{:.0f}".format(float(self.save)))
					break
			elif self.condition =="negative":
				self.save+=self.lecturaprimersimbolo
				self.condition="especial"

				if self.lecturaprimersimbolo.isdigit():
					self.condition="negative"						
				else:

					print("{:.21f}".format(float(self.save)))
					break								
			elif self.condition=="ten":
				if  self.lecturaprimersimbolo==".":
					presave=self.save[:-1]
					self.save="."
					self.conditn="Numbers"
					self.condition="delim"
					return lexema(presave,self.firstchar, self.firstline, self.conditn)
				elif self.lecturaprimersimbolo.isdigit(): 	
					self.save+=self.lecturaprimersimbolo
					self.condition="float"																											
				else:
					# self.condition="finish"
					break		
			elif self.condition=="delim":		
				if  self.save=="..":
					# self.condition="finish"
					break
				elif self.lecturaprimersimbolo in DELIM :		
					#self.save+=self.lecturaprimersimbolo
					self.condition="delim"
					break																														
				else:	
					# self.condition="finish"
					break	
			elif self.condition=="float":		
				if  self.lecturaprimersimbolo.isdigit(): 	
					self.save+=self.lecturaprimersimbolo
					self.condition="float"
				elif  self.lecturaprimersimbolo=="E":
				 	self.save+=self.lecturaprimersimbolo
				 	self.condition="especial"

				elif self.lecturaprimersimbolo.isalpha() or self.lecturaprimersimbolo==".":
					self.condition="error"
					#raise Exception('error')																											
				else:	
					# print("{:.0f}".format(float(self.save)))
					# self.condition="finish"
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
			elif self.condition=="(":
			    			
				if  self.lecturaprimersimbolo=="*":
					self.condition="(*"
				elif self.lecturaprimersimbolo==")":
					self.condition=='delim'
					continue
				else: 	
					self.condition='delim'
					continue
					
																													
			elif self.condition=="(*": 
				if self.lecturaprimersimbolo=="*":
					self.condition += "*"	
			elif self.condition == "(**":
				if self.lecturaprimersimbolo==")":
						self.condition = 'S'
						
			elif self.condition=="{":
				if self.lecturaprimersimbolo=="}":
						self.condition= 'S'
				elif self.lecturaprimersimbolo=="" :
					self.condition="error"		
			elif self.condition=="reservacion":
				if	self.lecturaprimersimbolo in reservadas:
					self.save+=self.lecturaprimersimbolo					
					self.condition="reservacion"
				else:

					# self.condition="finish"
					break															
			self.lecturaprimersimbolo=str(self.test.read(1))
			self.char+=1
				
			if self.lecturaprimersimbolo in Final_line:
				self.line+=1
				self.char=0	
		
		conditn = self.condition
		if self.save in REL_BIN_OPS:
			conditn="binary operations"
		elif conditn== "kotoba":
			if self.save.upper() in reservadas:
				conditn="Reservation words"
			else:
				conditn="words"	
		elif self.save in ARITHM_BIN_OPS:
			conditn="arithmetical operations"	
		elif self.save in BOOL_BIN_OPS:
			conditn="Boolean operations"
		elif self.save in BOOL_UNARY_OPS:
			conditn="Boolean  unary operations"				 
		elif conditn =="especial":
			conditn="float"
		elif conditn =="bango":
			conditn="Numbers"

		self.condition='S'
			#return self.saveb
		self.conditn = conditn

		return lexema(self.save,self.firstchar,self.firstline,conditn)
		self.test.close()

	def siguientelexicoget(self):
		return lexema(self.save,self.firstchar,self.firstline,self.conditn)


if __name__ == '__main__':
	lexanalizer = Lexer()
	file2 = open("result\\test.txt",'w') 
	try:
		lex = lexanalizer.siguientelexico()
		while lex.save:
			file2.write("line:"+ str(lex.line) + " char" + str(lex.char) +" lex:" + lex.save+'\n'+lex.type)
			print("line:"+ str(lex.line) + " char" + str(lex.char) +" lex:" + lex.save +" type: "+lex.type)
			lex = lexanalizer.siguientelexico()
	except Exception as e:
		print(e)


		

		



					








	
