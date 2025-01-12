import get_last_saved_day
import os
import numpy as np

def appendToCsvFile(filenameshort, data, format):
	
	rows = data.shape[0]
	if rows == 0:
		return
	
	firstyear = data[0][0]
	firstday = data[0][1]
	lastyear = data[rows-1][0]
	lastday = data[rows-1][1]
	print('inside append to csv', firstyear, firstday, lastyear, lastday)
	
	filename = filenameshort + '.csv'
	tempname = filenameshort + "-temp.csv"
	tempmergedname = filenameshort + "-temp-merged.csv"
	
	lastSavedYear,lastSavedDay = get_last_saved_day.getLastSavedDay(filename)
	print('last saved day', lastSavedYear, lastSavedDay)
	rowstoadd = int((366 if lastSavedYear % 4 == 0 else 365)*(lastyear - lastSavedYear) + lastday - lastSavedDay)

	if rowstoadd <= 0:
		print('nothing to add to csv file', lastSavedDay)
		return

	data = data[-rowstoadd:,:]
	
	np.savetxt(tempname, data, format)
	
	filenames = [filename, tempname]
	with open(tempmergedname, 'w') as outfile:
		for fname in filenames:
			with open(fname) as infile:
				outfile.write(infile.read())
	os.remove(tempname)
	os.remove(filename)
	os.rename(tempmergedname, filename)
