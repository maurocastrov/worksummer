from Parser import parser
from error import compiler_exception
if __name__ == "__main__":
	count=0
	count_incorrect=0	
	for i in range(1,4):
		par_alizer = parser("test/test_parser"+ str(i) +".txt")
		fout = open("out_parser"+ str(i) +".txt", "w")
		try:
			file2 = open("result\\test_parser.txt",'w') 
			parse_res = par_alizer.par_expresion()
			
			fout.write(parse_res.print_result(0))
		except compiler_exception as e:
			if fout.seek():
				fout.write(str(e))
		fout.close()

		fout = open("out_parser"+ str(i) +".txt", "r")	
		tout = fout.read()
		fcorrect=open("test\\test_parser"+ str(i) +"(correct).txt", "r")
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
