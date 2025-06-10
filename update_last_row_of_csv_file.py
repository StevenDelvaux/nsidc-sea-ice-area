import os
import numpy as np

def updateLastRowOfCsvFile(shortFilename, data, format):
	
	print('inside update last row', shortFilename)
	filename = shortFilename + '.csv'
	with open(filename, "r+") as file:

		# Move the pointer (similar to a cursor in a text editor) to the end of the file
		file.seek(0, os.SEEK_END)

		# This code means the following code skips the very last character in the file -
		# i.e. in the case the last line is null we delete the last line
		# and the penultimate one
		pos = file.tell() - 1
		foundNewlines = 0

		# Read each character in the file one at a time from the penultimate
		# character going backwards, searching for a newline character
		# If we find a new line, exit the search
		while pos > 0 and foundNewlines < 1:
			pos -= 1
			file.seek(pos, os.SEEK_SET)
			ch = file.read(1)
			if ch == "\n":
				pos += 1
				print('found newline')
				foundNewlines += 1

		# So long as we're not at the start of the file, delete all the characters ahead
		# of this position
		if pos > 0:
			file.seek(pos, os.SEEK_SET)
			file.truncate()
	
	tempname = shortFilename + '_temp.csv'
	tempmergedname = shortFilename + '_merged_temp.csv'
	np.savetxt(tempname, data, delimiter=",", fmt=format)

	filenames = [filename, tempname]
	with open(tempmergedname, 'w') as outfile:
		for fname in filenames:
			with open(fname) as infile:
				outfile.write(infile.read())
	os.remove(filename)
	os.rename(tempmergedname, filename)