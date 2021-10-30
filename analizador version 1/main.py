from lexer import Lexer
import os
from error import compiler_exception
if __name__ == "__main__":
	count=0
	count_incorrect=0

	for i in range(1,16):

		fout = open("out"+ str(i) +".txt", "w")
		try:
			ref = Lexer("test\\test"+ str(i) +".txt")
			lex = ref.siguientelexico()
			if lex.save:
				fout.write("line:"+ str(lex.line) + " char:" + str(lex.char) +" lex: " + lex.save+"  " + lex.type+ " type: "  +lex.klen)
				lex = ref.siguientelexico()

			while lex.save:
				fout.write("\n" + "line:"+ str(lex.line) + " char:" + str(lex.char) +" lex: " + lex.save+ "  " + lex.type+ " type: " +lex.klen)
				lex = ref.siguientelexico()

		except compiler_exception as e:
			if fout.tell():
				fout.write("\n" + str(e))
			else:
				fout.write(str(e))

		fout.close()

		fout = open("out"+ str(i) +".txt", "r")	
		tout = fout.read()
		fcorrect=open("test\\test"+ str(i) +"(correct).txt", "r")
		tcorrect=fcorrect.read()
		if tout == tcorrect:
			print("test"+ str(i) +"---->Correct")
			count+=1

		else:
			print("test"+ str(i) +"---->Incorrect")
			count_incorrect+=1
	count_all=count_incorrect+count
	print( "All the tests are " + str(count_all))
	print("All the correct are "  + str(count))
	print("All the incorrect are " + str(count_incorrect ))