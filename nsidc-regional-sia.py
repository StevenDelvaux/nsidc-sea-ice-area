import numpy as np
from netCDF4 import Dataset
from datetime import date, datetime, timedelta
import os
import requests
from math import sqrt, sin, cos, pi, floor, isnan
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.ticker as ticker
import time
from PIL import Image, ImageGrab, ImageDraw, ImageFont

import upload_to_google_drive
import dropbox_client
import make_animation
import update_last_row_of_csv_file
import get_last_saved_day
import append_to_csv_file
from decouple import config

monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
monthNamesFull = ['Jan','Feb','March','April','May','June','July','Aug','Sep','Oct','Nov','Dec']
monthLengths = [31,28,31,30,31,30,31,31,30,31,30,31]

putOnDropbox = True  # todo
putOnGoogleDrive = True # todo

def padzeros(n):
	"""
	Left pad a number with zeros. 
    """
	return str(n) if n >= 10 else '0'+str(n)

def updateTotalAreaAndExtentFilesAntarctic(filename, year):
	data = np.loadtxt(filename + ".csv", delimiter=",", dtype=str)

	updateTotalFile(14, data, False, year)
	updateTotalFile(15, data, True, year)
	
def updateTotalAreaAndExtentFilesArctic(filename, year):
	data = np.loadtxt(filename + ".csv", delimiter=",", dtype=str)

	updateTotalFile(41, data, False, year)
	updateTotalFile(42, data, True, year)

def getNumberOfYears():
	return 36 if north else 47

def updateTotalFile(col, data, isextent, year):
	regional = data[1:,col]
	regional = np.array([i.lstrip() for i in regional]).astype(float)/1000.0
	offset = 0
	years = getNumberOfYears()
	padded = np.pad(regional, (offset, 365*years - regional.shape[0] - offset), 'constant', constant_values=(np.nan,)) #45
	lastrow = (padded.reshape((years,365)))[-1]
	row = lastrow.tolist()
	row.insert(0, year)
	filename = 'nsidc-' + ('' if north else 'ant') + 'arctic-' + ('extent' if isextent else 'area')
	dropbox_client.downloadFromDropbox([filename + '.csv'])
	format = ','.join(['%i'] + ['%9.3f']*(len(row)-1))
	update_last_row_of_csv_file.updateLastRowOfCsvFile(filename, [row], format)
	
def generateTotalAreaAndExtentFiles(filename, year):
	data = np.loadtxt(filename + ".csv", delimiter=",", dtype=str)

	generateTotalAreaFile(41 if north else 14, data, False, year)
	generateTotalAreaFile(42 if north else 15, data, True, year)

def getRank(row):
	value = row[-1]
	rank = 1
	numberOfYears = len(row) 
	for i in range(numberOfYears-1):
		if row[i] < value:
			rank += 1

	return rank

def getRankString(row):
	rank = getRank(row)
	suffix = 'th'
	if rank == 1:
		suffix = 'st'
	elif rank == 2:
		suffix = 'nd'
	elif rank == 3:
		suffix = 'rd'
	
	return ('  ' if rank < 10 else '') + str(rank) + suffix

def getNextLowest(row, previousMin, previousIndex):
	min = None
	index = None
	numberOfYears = len(row) 
	for i in range(numberOfYears):
		if (min == None or row[i] < min) and (previousMin == None or row[i] > previousMin or (row[i] == previousMin and i > previousIndex)):
			min = row[i]
			index = i
	
	return min,index
	
def generateDecadeSummary(filename, extent):
	data = np.loadtxt(filename + ".csv", delimiter=",", dtype=str)
	regional = data[1:,42 if extent and north else 41 if north else 15 if extent else 14]
	extenttype = 'extent' if extent else 'area'
	regional = np.array([i.lstrip() for i in regional]).astype(float)/1000.0
	offset = 0
	years = getNumberOfYears()
	padded = np.pad(regional, (offset, 365*years - regional.shape[0] - offset), 'constant', constant_values=(np.nan,)) #45
	matrix = padded.reshape((years,365))
	day = regional.shape[0] - 365*(years-1) -1
	
	lastSavedYear,lastSavedDay = get_last_saved_day.getLastSavedDay(filename + '.csv')
	date = getDateFromDayOfYear(lastSavedDay, lastSavedYear)
	
	filename = 'empty-image.png'
	im = Image.open(filename)
	im = im.convert("RGBA")
	width, height = im.size
	printimtext = ImageDraw.Draw(im)
	
	fontsize=16
	largeFontsize=17
	smallFontsize=16
	superscriptFontsize=10
	font = ImageFont.truetype("arial.ttf", fontsize)
	largeFont = ImageFont.truetype("arialbd.ttf", largeFontsize)
	smallFont = ImageFont.truetype("arialbd.ttf", smallFontsize)
	superscriptFont = ImageFont.truetype("arialbd.ttf", superscriptFontsize)	
	color = (0,0,0)
	
	row = matrix[:, day]
	rank = getRank(row)
	value = None
	index = None
	
	color = (0,0,0)
	hemisphere = 'Arctic' if north else 'Antarctic'	
	printimtext.text((37 + (12 if north else 0) + (0 if extenttype == 'extent' else 8), 4), 'NSIDC ' + hemisphere + ' sea ice ' + extenttype + ': last ' + str(days) + ' days', color, font=largeFont)
	verticalOffset = 34
	printimtext.text((26, verticalOffset), 'decade', color, font=smallFont)
	printimtext.text((113, verticalOffset), extenttype + ' (M km )', color, font=smallFont)
	printimtext.text((193 + (14 if extent else 0), verticalOffset-4), '2', color, font=superscriptFont)
	printimtext.text((226, verticalOffset), 'daily change (km )', color, font=smallFont)
	printimtext.text((353, verticalOffset-4), '2', color, font=superscriptFont)
	
	counter = -1
	decadeStartYears = [1980,1990,2000,2010,2020,2014,2024]
	decadeEndYears = [1989,1999,2009,2019,2023,2023,2024]
	decadeNames = ['1980s','1990s','2000s','2010s','2020s','2014-2023']
	for i in range(6):
		decadeStartYear = decadeStartYears[i]
		decadeEndYear = decadeEndYears[i]
		decadeName = decadeNames[i]
		date = lastSavedDate
		value = matrix[-1, day]
		rank = getRankString(matrix[:, day])
		dailyDelta = round(1000*(value-previousValue))
		dailyDeltaStr = ('  ' if abs(dailyDelta) < 100 else '') + ('  ' if abs(dailyDelta) < 10 else '') + ('+' if dailyDelta >= 0 else ' ') + str(dailyDelta) + 'k' # km'
		print('last daily value',value,rank,date)
		verticalOffset = 60 + 21*counter
		if counter == days - 1:
			color = (255,0,0)
		printimtext.text((6, verticalOffset), decadeNames[i], color, font=font)
		printimtext.text((148, verticalOffset), '{:.3f}'.format(round(value,3)), color, font=font) #+ ' M km  '
		#printimtext.text((221-(10 if value < 10 else 0), verticalOffset-4), '2', color, font=superscriptFont)		
		printimtext.text((260, verticalOffset), dailyDeltaStr, color, font=font)
		#printimtext.text((327, verticalOffset-4), '2', color, font=superscriptFont)
		printimtext.text((370, verticalOffset), rank + ' lowest', color, font=font)		
		previousValue = value
		
	hemisphere = 'arctic' if north else 'antarctic'
	saveFileName = 'nsidc-' + hemisphere + '-' + extenttype + '-decades.png'
	im.save(saveFileName)
	print('image size', width, height)
	return saveFileName
	
def generateRankSummary(filename, extent):
	data = np.loadtxt(filename + ".csv", delimiter=",", dtype=str)
	regional = data[1:,42 if extent and north else 41 if north else 15 if extent else 14]
	extenttype = 'extent' if extent else 'area'
	regional = np.array([i.lstrip() for i in regional]).astype(float)/1000.0
	offset = 0
	years = getNumberOfYears()
	padded = np.pad(regional, (offset, 365*years - regional.shape[0] - offset), 'constant', constant_values=(np.nan,)) #45
	matrix = padded.reshape((years,365))
	day = regional.shape[0] - 365*(years-1) -1
	
	lastSavedYear,lastSavedDay = get_last_saved_day.getLastSavedDay(filename + '.csv')
	date = getDateFromDayOfYear(lastSavedDay, lastSavedYear)
	
	filename = 'empty-image-long.png'
	im = Image.open(filename)
	im = im.convert("RGBA")
	width, height = im.size
	printimtext = ImageDraw.Draw(im)
	
	fontsize=16
	largeFontsize=16
	smallFontsize=16
	superscriptFontsize=10
	font = ImageFont.truetype("arial.ttf", fontsize)
	largeFont = ImageFont.truetype("arialbd.ttf", largeFontsize)
	smallFont = ImageFont.truetype("arialbd.ttf", smallFontsize)
	superscriptFont = ImageFont.truetype("arialbd.ttf", superscriptFontsize)	
	color = (0,0,0)
	
	row = matrix[:, day]
	rank = getRank(row)
	value = None
	index = None
	
	hemisphere = 'Arctic' if north else 'Antarctic'	
	printimtext.text((0, 4), 'NSIDC ' + hemisphere + ' sea ice ' + extenttype + ' on ' + str(date.day) + ' ' + monthNamesFull[date.month-1], color, font=largeFont)
	verticalOffset = 34
	printimtext.text((5, verticalOffset), 'rank', color, font=smallFont)
	printimtext.text((50, verticalOffset), 'year', color, font=smallFont)
	printimtext.text((113, verticalOffset), extenttype + ' (M km )', color, font=smallFont)
	printimtext.text((193 + (14 if extent else 0), verticalOffset-4), '2', color, font=superscriptFont)
	
	for i in range(15):
		value,index = getNextLowest(row,value,index)
		currentRank = i+1
		if i == 14 and rank > 15:
			value,index = row[-1],years-1
			currentRank = rank
		verticalOffset = 60 + 21*i
		year = (1990 if north else 1979) + index
		if year == 2025:
			color = (255,0,0)
		else:
			color = (0,0,0)
		printimtext.text((10, verticalOffset), str(currentRank), color, font=font)
		printimtext.text((50, verticalOffset), str(year), color, font=font)
		printimtext.text((113, verticalOffset), '{:.3f}'.format(round(value,3)), color, font=font)
	hemisphere = 'arctic' if north else 'antarctic'
	saveFileName = 'nsidc-' + hemisphere + '-' + extenttype + '-daily-ranks-latest.png'
	im.save(saveFileName)
	print('image size', width, height)
	return saveFileName

def generateSummary(filename, extent):
	data = np.loadtxt(filename + ".csv", delimiter=",", dtype=str)
	regional = data[1:,42 if extent and north else 41 if north else 15 if extent else 14]
	extenttype = 'extent' if extent else 'area'
	regional = np.array([i.lstrip() for i in regional]).astype(float)/1000.0
	offset = 0
	years = getNumberOfYears()
	padded = np.pad(regional, (offset, 365*years - regional.shape[0] - offset), 'constant', constant_values=(np.nan,)) #45
	matrix = padded.reshape((years,365))
	day = regional.shape[0] - 365*(years-1) -1
	
	lastSavedYear,lastSavedDay = get_last_saved_day.getLastSavedDay(filename + '.csv')
	lastSavedDate = getDateFromDayOfYear(lastSavedDay, lastSavedYear)
	
	filename = 'empty-image.png'
	im = Image.open(filename)
	im = im.convert("RGBA")
	width, height = im.size
	printimtext = ImageDraw.Draw(im)
	
	fontsize=16
	largeFontsize=20
	smallFontsize=16
	superscriptFontsize=10
	font = ImageFont.truetype("arial.ttf", fontsize)
	largeFont = ImageFont.truetype("arialbd.ttf", largeFontsize)
	smallFont = ImageFont.truetype("arialbd.ttf", smallFontsize)
	superscriptFont = ImageFont.truetype("arialbd.ttf", superscriptFontsize)
	
	days = 7

	counter = 0
	dayList = []
	total = -1
	plotday = lastSavedDate + timedelta(days = 1)
	while counter <= days:
		total += 1
		plotday = plotday - timedelta(days = 1)
		if plotday in missingdates:
			continue
		dayList.append(total)
		counter += 1
	earliestDay = dayList.pop()
	dayList.reverse()
	
	previousValue = matrix[-1, day-earliestDay] if day-earliestDay >=0 else matrix[-2, day-earliestDay]
	color = (0,0,0)
	hemisphere = 'Arctic' if north else 'Antarctic'	
	printimtext.text((37 + (12 if north else 0) + (0 if extenttype == 'extent' else 8), 4), 'NSIDC ' + hemisphere + ' sea ice ' + extenttype + ': last ' + str(days) + ' days', color, font=largeFont)
	verticalOffset = 34
	printimtext.text((26, verticalOffset), 'date', color, font=smallFont)
	printimtext.text((113, verticalOffset), extenttype + ' (M km )', color, font=smallFont)
	printimtext.text((193 + (14 if extent else 0), verticalOffset-4), '2', color, font=superscriptFont)
	printimtext.text((226, verticalOffset), 'daily change (km )', color, font=smallFont)
	printimtext.text((353, verticalOffset-4), '2', color, font=superscriptFont)
	printimtext.text((400, verticalOffset), 'rank', color, font=smallFont)
	

	
	counter = -1
	for offset in dayList:
		date = lastSavedDate - timedelta(days = offset)
		print('summary date: ',counter,offset,date)
		counter += 1 
		value = matrix[-1, day-offset] if day-offset >=0 else matrix[-2, day-offset]
		rank = getRankString(matrix[:, day-offset] if day-offset >=0 else matrix[0:-1, day-offset])
		dailyDelta = round(1000*(value-previousValue))
		dailyDeltaStr = ('  ' if abs(dailyDelta) < 100 else '') + ('  ' if abs(dailyDelta) < 10 else '') + ('+' if dailyDelta >= 0 else ' ') + str(dailyDelta) + 'k' # km'
		print('last daily value',value,rank,date)
		verticalOffset = 60 + 21*counter
		if counter == days - 1:
			color = (255,0,0)
		printimtext.text((6, verticalOffset), padzeros(date.day) + ' ' + monthNames[date.month-1] + ' ' + str(date.year), color, font=font)
		printimtext.text((148, verticalOffset), '{:.3f}'.format(round(value,3)), color, font=font) #+ ' M km  '
		#printimtext.text((221-(10 if value < 10 else 0), verticalOffset-4), '2', color, font=superscriptFont)		
		printimtext.text((260, verticalOffset), dailyDeltaStr, color, font=font)
		#printimtext.text((327, verticalOffset-4), '2', color, font=superscriptFont)
		printimtext.text((370, verticalOffset), rank + ' lowest', color, font=font)		
		previousValue = value
		
	hemisphere = 'arctic' if north else 'antarctic'
	saveFileName = 'nsidc-' + hemisphere + '-' + extenttype + '-recent-days.png'
	im.save(saveFileName)
	print('image size', width, height)
	return saveFileName

def generateTotalAreaFile(col, data, isextent, year):
	regional = data[1:,col]
	regional = np.array([i.lstrip() for i in regional]).astype(float)/1000.0
	offset = 0
	years = getNumberOfYears()
	padded = np.pad(regional, (offset, 365*years - regional.shape[0] - offset), 'constant', constant_values=(np.nan,)) #45
	matrix = padded.reshape((years,365))
	lastrow = matrix[-1]
	
	yearscolumn = np.arange((1990 if north else 1979), year+1)
	fullmatrix = np.concatenate((yearscolumn[:, np.newaxis], matrix), axis = 1)

	filename = 'nsidc-' + ('' if north else 'ant') + 'arctic-' + ('extent' if isextent else 'area') + '-temp'
	format = ','.join(['%i'] + ['%9.3f']*(365))
	np.savetxt(filename + '.csv', fullmatrix, delimiter=",", fmt=format)

def plotRegionalGraphsAntarctic(filename):
	data = np.loadtxt(filename + ".csv", delimiter=",", dtype=str)

	saveRegionalPlot(2, 0, 6.5, data, "Weddell NSIDC sea ice area", "nsidc-area-weddell.png", 4) #6.3
	saveRegionalPlot(3, 0, 7.5, data, "Weddell NSIDC sea ice extent", "nsidc-extent-weddell.png", 4) # 7.4
	saveRegionalPlot(4, 0, 2.5, data, "Bellingshausen-Amundsen NSIDC sea ice area", "nsidc-area-bellamu.png", 2) #2.3
	saveRegionalPlot(5, 0, 3.5, data, "Bellingshausen-Amundsen NSIDC sea ice extent", "nsidc-extent-bellamu.png", 4) #3.4
	saveRegionalPlot(6, 0, 4, data, "Ross NSIDC sea ice area", "nsidc-area-ross.png", 4) #4
	saveRegionalPlot(7, 0, 5, data, "Ross NSIDC sea ice extent", "nsidc-extent-ross.png", 4) # 5
	saveRegionalPlot(8, 0.0, 2.0, data, "Pacific Southern Ocean NSIDC sea ice area", "nsidc-area-pacific.png", 4) #2
	saveRegionalPlot(9, 0, 2.5, data, "Pacific Southern Ocean NSIDC sea ice extent", "nsidc-extent-pacific.png", 4) #2.4
	saveRegionalPlot(10, 0.0, 3.5, data, "Indian Southern Ocean NSIDC sea ice area", "nsidc-area-indian.png", 2) #3.7
	saveRegionalPlot(11, 0.0, 5, data, "Indian Southern Ocean NSIDC sea ice extent", "nsidc-extent-indian.png", 4) #4.4
	
	filenameAntarcticArea = "nsidc-area-antarctic.png"
	filenameAntarcticExtent = "nsidc-extent-antarctic.png"
	filenameAntarcticAreaAnomaly = "nsidc-area-antarctic-anomaly.png"
	filenameAntarcticExtentAnomaly = "nsidc-extent-antarctic-anomaly.png"
	filenameAntarcticCompactness = "nsidc-compactness-antarctic.png"
	
	saveRegionalPlot(14, 7, 16.5, data, "NSIDC Antarctic sea ice area", filenameAntarcticArea, 4)
	saveRegionalPlot(15, 9, 21, data, "NSIDC Antarctic sea ice extent", filenameAntarcticExtent, 4)
	saveRegionalPlot(14, -3, 2, data, "NSIDC Antarctic sea ice area anomaly vs. 1990-2019", filenameAntarcticAreaAnomaly, 2, True)
	saveRegionalPlot(15, -3, 2.0, data, "NSIDC Antarctic sea ice extent anomaly vs. 1990-2019", filenameAntarcticExtentAnomaly, 2, True)
	saveRegionalPlot(-3, 0.74, 0.85, data, "NSIDC Antarctic sea ice compactness (area divided by extent)", filenameAntarcticCompactness, 1)

	if putOnDropbox:
		dropbox_client.uploadToDropbox([filenameAntarcticCompactness, filenameAntarcticArea, filenameAntarcticExtent, filenameAntarcticAreaAnomaly, filenameAntarcticExtentAnomaly])

def plotRegionalGraphsArctic(filename):
	data = np.loadtxt(filename + ".csv", delimiter=",", dtype=str)
	legendpos = 8
	saveRegionalPlot(2, 1.5, 4.4, data, "Central Arctic NSIDC sea ice area", "nsidc-area-cab.png", 3)
	saveRegionalPlot(3, 2.5, 4.6, data, "Central Arctic NSIDC sea ice extent", "nsidc-extent-cab.png", 3)
	saveRegionalPlot(4, 0, 0.7, data, "Beaufort NSIDC sea ice area", "nsidc-area-beaufort.png", 1)
	saveRegionalPlot(5, 0, 0.7, data, "Beaufort NSIDC sea ice extent", "nsidc-extent-beaufort.png", 3)
	saveRegionalPlot(6, 0, 0.7, data, "Chukchi NSIDC sea ice area", "nsidc-area-chukchi.png", 1)
	saveRegionalPlot(7, 0, 0.8, data, "Chukchi NSIDC sea ice extent", "nsidc-extent-chukchi.png", 1)
	saveRegionalPlot(8, 0, 0.72, data, "East Siberian NSIDC sea ice area", "nsidc-area-ess.png", 1)
	saveRegionalPlot(9, 0, 0.72, data, "East Siberian NSIDC sea ice extent", "nsidc-extent-ess.png", 3)
	saveRegionalPlot(10, 0, 0.5, data, "Laptev NSIDC sea ice area", "nsidc-area-laptev.png", 1)
	saveRegionalPlot(11, 0, 0.5, data, "Laptev NSIDC sea ice extent", "nsidc-extent-laptev.png", 1)
	saveRegionalPlot(12, 0, 0.8, data, "Kara NSIDC sea ice area", "nsidc-area-kara.png", 1)
	saveRegionalPlot(13, 0, 1, data, "Kara NSIDC sea ice extent", "nsidc-extent-kara.png", 1)
	saveRegionalPlot(14, 0, 0.3, data, "Barents NSIDC sea ice area", "nsidc-area-barents.png", 1)
	saveRegionalPlot(15, 0, 0.6, data, "Barents NSIDC sea ice extent", "nsidc-extent-barents.png", 1)
	saveRegionalPlot(16, 0, 0.5, data, "Greenland Sea NSIDC ice area", "nsidc-area-greenland.png", 1)
	saveRegionalPlot(17, 0, 0.8, data, "Greenland Sea NSIDC ice extent", "nsidc-extent-greenland.png", 1)
	saveRegionalPlot(18, 0, 0.7, data, "Baffin Bay NSIDC sea ice area", "nsidc-area-baffin.png", 1)
	saveRegionalPlot(19, 0, 1.0, data, "Baffin Bay NSIDC sea ice extent", "nsidc-extent-baffin.png", 1)
	saveRegionalPlot(22, 0, 1.0, data, "Hudson Bay NSIDC sea ice area", "nsidc-area-hudson.png", 1)
	saveRegionalPlot(23, 0, 1.3, data, "Hudson Bay NSIDC sea ice extent", "nsidc-extent-hudson.png", 1)
	saveRegionalPlot(24, 0, 0.8, data, "Canadian Archipelago NSIDC sea ice area", "nsidc-area-caa.png", 3)
	saveRegionalPlot(25, 0, 0.82, data, "Canadian Archipelago NSIDC sea ice extent", "nsidc-extent-caa.png", 3)
	saveRegionalPlot(26, 0, 0.2, data, "Bering NSIDC sea ice area", "nsidc-area-bering.png", 1)
	saveRegionalPlot(27, 0, 0.4, data, "Bering NSIDC sea ice extent", "nsidc-extent-bering.png", 1)
	saveRegionalPlot(28, 0, 0.2, data, "Okhotsk NSIDC sea ice area", "nsidc-area-okhotsk.png", 1)
	saveRegionalPlot(29, 0, 0.2, data, "Okhotsk NSIDC sea ice extent", "nsidc-extent-okhotsk.png", 1)
	
	filenameArcticCompactness = "nsidc-compactness-arctic.png"
	filenameArcticBasinArea = "nsidc-area-arctic-basin.png"
	filenameArcticBasinExtent = "nsidc-extent-arctic-basin.png"
	
	saveRegionalPlot(-3, 0.55, 0.87, data, "NSIDC Arctic sea ice compactness (area divided by extent)", filenameArcticCompactness, 3)
	saveRegionalPlot(-2, 2.5, 7.4, data, "Arctic Basin NSIDC sea ice extent", filenameArcticBasinExtent, 3)
	saveRegionalPlot(-1, 1.5, 6.8, data, "Arctic Basin NSIDC sea ice area", filenameArcticBasinArea, 3)
		
	filenameArcticArea = "nsidc-area-arctic.png"
	filenameArcticExtent = "nsidc-extent-arctic.png"
	filenameArcticAreaAnomaly = "nsidc-area-arctic-anomaly.png"
	filenameArcticExtentAnomaly = "nsidc-extent-arctic-anomaly.png"
	
	saveRegionalPlot(41, 2, 10.7, data, "NSIDC Arctic sea ice area", filenameArcticArea, 3)
	saveRegionalPlot(42, 3, 12.3, data, "NSIDC Arctic sea ice extent", filenameArcticExtent, 1)	
	saveRegionalPlot(41, -2, 0.3, data, "NSIDC Arctic sea ice area anomaly vs. 1990-2019", filenameArcticAreaAnomaly, 3, True)
	saveRegionalPlot(42, -2.5, 0.2, data, "NSIDC Arctic sea ice extent anomaly vs. 1990-2019", filenameArcticExtentAnomaly, 3, True)
	if putOnDropbox:
		dropbox_client.uploadToDropbox([filenameArcticArea, filenameArcticExtent, filenameArcticAreaAnomaly, filenameArcticExtentAnomaly, filenameArcticCompactness])

def saveRegionalPlot(col, ymin, ymax, data, name, filename, legendpos=1, anomaly=False):
	print('inside saveRegionalPlot', name)
	fig, axs = plt.subplots(figsize=(8, 5))
	printRegionalData(data, axs, col, ymin, ymax, name, legendpos, anomaly)
	if col == -1:
		plt.text(35,6.5,'CAB+Beaufort+Chukchi+ESS+Laptev', fontsize=10,color='black')
	elif col == -2:
		plt.text(35,7.15,'CAB+Beaufort+Chukchi+ESS+Laptev', fontsize=10,color='black')	
	
	fig.savefig(filename)

def getPlotMatrix(data, col):
	regional = data[1:,col]
	regional = np.array([i.lstrip() for i in regional]).astype(float)/1000.0
	offset = 214 #245 #275 #306 #334 #31 #61 #92 #122 #153 #184 #214 #275 #61 # 0
	years = getNumberOfYears() + 1
	print('plot matrix shape: ', 365*years, regional.shape)
	padded = np.pad(regional, (offset, 365*years - regional.shape[0] - offset), 'constant', constant_values=(np.nan,)) #45	
	matrix = padded.reshape((years,365))
	return matrix

def printRegionalData(data, ax, col, ymin, ymax, name, legendpos=1, anomaly=False):
	print('inside printRegionalData', name, ymin, ymax)

	iscompactness = 'compactness' in name
	isextent = 'extent' in name 
	if col > 0:
		matrix = getPlotMatrix(data, col)
	elif col == -1:
		matrix = getPlotMatrix(data, 2)
		matrix = matrix + getPlotMatrix(data, 4)
		matrix = matrix + getPlotMatrix(data, 6)
		matrix = matrix + getPlotMatrix(data, 8)
		matrix = matrix + getPlotMatrix(data, 10)
	elif col == -2:
		matrix = getPlotMatrix(data, 3)
		matrix = matrix + getPlotMatrix(data, 5)
		matrix = matrix + getPlotMatrix(data, 7)
		matrix = matrix + getPlotMatrix(data, 9)
		matrix = matrix + getPlotMatrix(data, 11)
	elif col == -3:
		areamatrix = getPlotMatrix(data, 41 if north else 14)
		print('areamx', type(areamatrix), areamatrix.shape)
		extentmatrix = getPlotMatrix(data, 42 if north else 15)
		print('extentmx', type(extentmatrix), extentmatrix.shape)
		floormx = np.ones(extentmatrix.shape)
		print('floormx', type(floormx), floormx.shape)
		denominator = np.maximum(extentmatrix,floormx)
		print('denominator', type(denominator), denominator.shape)
		denominatorinverted = 1/denominator
		print('denominatorinverted', type(denominatorinverted), denominatorinverted.shape)
		matrix = np.multiply(areamatrix, denominatorinverted)
		print('matrix', type(matrix), matrix.shape)
	
	
	if anomaly:
		avg = np.mean((matrix[1:31,:] if north else matrix[12:42,:]), axis=0)
	else:
		avg = np.zeros(365)
	
	dates = np.arange(0,365) # (0,366)
		
	ax.plot(dates, matrix[-16,:]-avg, label='2010', color=(0.65,0.65,0.65));
	ax.plot(dates, matrix[-15,:]-avg, label='2011', color=(0.44,0.19,0.63));
	ax.plot(dates, matrix[-14,:]-avg, label='2012', color=(0.0,0.13,0.38));
	ax.plot(dates, matrix[-13,:]-avg, label='2013', color=(0,0.44,0.75));
	ax.plot(dates, matrix[-12,:]-avg, label='2014', color=(0.0,0.69,0.94));
	ax.plot(dates, matrix[-11,:]-avg, label='2015', color=(0,0.69,0.31));
	ax.plot(dates, matrix[-10,:]-avg, label='2016', color=(0.57,0.82,0.31));
	ax.plot(dates, matrix[-9,:]-avg, label='2017', color=(1.0,0.75,0));
	ax.plot(dates, matrix[-8,:]-avg, label='2018', color=(0.9,0.4,0.05));
	ax.plot(dates, matrix[-7,:]-avg, label='2019', color=(1.0,0.5,0.5));
	ax.plot(dates, matrix[-6,:]-avg, label='2020', color=(0.58,0.54,0.33));
	ax.plot(dates, matrix[-5,:]-avg, label='2021', color=(0.4,0,0.2));
	ax.plot(dates, matrix[-4,:]-avg, label='2022', color=(0.7,0.2,0.3));
	ax.plot(dates, matrix[-3,:]-avg, label='2023', color=(0.5,0.3,0.1));
	ax.plot(dates, matrix[-2,:]-avg, label='2024', color=(0.75,0,0));
	ax.plot(dates, matrix[-1,:]-avg, label='2025', color=(1.0,0,0), linewidth=3);
	ax.set_ylabel("Sea ice " + ('compactness' if iscompactness else 'extent' if isextent else 'area') + (' anomaly' if anomaly else '') + (" (million km$^2\!$)" if not iscompactness else ""))
	ax.set_title(name)
	ax.legend(loc=legendpos, prop={'size': 8})
	ax.axis([0, 122, ymin, ymax]) #365
	ax.grid(True);
	

	months = ['Jun','Jul','Aug','Sep']
	#ax.set_xticks([0,30,61,92,120,151], ['', '', '', '', '', ''])
	ax.set_xticks([0,30,61,92,122], ['', '', '', '', '']) #, 211,242,272,303,333,364, '', '', '', '', '', ''])
	#ax.set_xticks([0,31,59,90,120,151,181], ['', '', '', '', '', '', '']) #, 211,242,272,303,333,364, '', '', '', '', '', ''])
	ax.xaxis.set_minor_locator(ticker.FixedLocator([15,45.5,76.5,107])) #,196,226.5,257,287.5,318,348.5]))
	#ax.xaxis.set_minor_locator(ticker.FixedLocator([15.5,45,74.5,105,135.5,166])) #,196,226.5,257,287.5,318,348.5]))
	#ax.xaxis.set_minor_locator(ticker.FixedLocator([15,45.5,76,106,135.5]))
	# months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
	# ax.set_xticks([0,31,59,90,120,151,181,212,243,273,304,334,365], ['', '', '', '', '', '', '', '', '', '', '', '', ''])
	# ax.xaxis.set_minor_locator(ticker.FixedLocator([15.5,45,74.4,105,135.5,166,196.5,227.5,258,288.5,319,349.5]))
	ax.xaxis.set_minor_formatter(ticker.FixedFormatter(months))
	ax.tick_params(which='minor', length=0)

def getversion(date):
	return '18' if date >= datetime(2023,10,1) else '17' if date >= datetime(2008,1,1) else '13' if date >= datetime(1995,9,30) else '11' if date >= datetime(1991,12,19) else '08' if date >= datetime(1987,8,21) else '07'

def getfilenameprefix(date, north=False):
	return 'NSIDC00' + ('81' if date >= datetime(2023,10,1) else '51') + '_SEAICE_PS_' + ('N' if north else 'S') + '25km_' + str(date.year) + padzeros(date.month) + padzeros(date.day) + '_v2.0'

def getfilenamenc(date, north=False):
	return getfilenameprefix(date, north) + '.nc'

def getfilenamepng(date, north=False):
	return getfilenameprefix(date, north) + '_F18.png'

def getfilenamepngBackup(date, north=False):
	return getfilenameprefix(date, north) + '_F18_1.png'

def getfilenamepngBackupBis(date, north=False):
	return getfilenameprefix(date, north) + '_F17.png'
	
def downloadDailyFiles(date, north, imageOnly=False):
	prefixshort = 'n5eil01u.ecs.nsidc.org/PM/' + ('NSIDC-0051.002/' if date < datetime(2023,10,1) else 'NSIDC-0081.002/')
	prefix = 'https://' + prefixshort
	nsidcfolder = prefix + str(date.year) + '.' + padzeros(date.month) + '.' + padzeros(date.day) + '/'
	filenamenc = getfilenamenc(date, north)
	filenamepng = getfilenamepng(date, north)	
	if imageOnly:
		filenames = [filenamepng]
	elif date.year >= 2024:
		filenames = [filenamenc, filenamepng]
	else:
		filenames = [filenamenc]
	username = config('NSIDC_USERNAME')
	password = config('NSIDC_PASSWORD')
		
	session = requests.session()
	
	for filename in filenames:
		print('downloading ' + filename)
		localfolder = './data/' + str(date.year)
		if not os.path.isdir(localfolder):
			os.makedirs(localfolder, exist_ok=True)
		localpath = localfolder + '/' + filename
		url = nsidcfolder + filename
		
		s = session.get(url)
		with session.get(s.url,auth=(username,password)) as r:
			if r.status_code == 200:
				with open(localpath, 'wb') as f:
					f.write(r.content)
			elif url.endswith(".png"):
				print('got status code', r.status_code)
				filenameBackup = getfilenamepngBackup(date, north)
				url = nsidcfolder + filenameBackup
				print('downloading ' + filenameBackup)
				with session.get(url, auth=(username,password)) as r:
					if r.status_code == 200:
						with open(localpath, 'wb') as f:
							f.write(r.content)
					else:
						print('got status code', r.status_code)
						filenameBackup = getfilenamepngBackupBis(date, north)
						url = nsidcfolder + filenameBackup
						print('downloading ' + filenameBackup)
						with session.get(url, auth=(username,password)) as r:
							if r.status_code == 200:
								with open(localpath, 'wb') as f:
									f.write(r.content)
							else:
								 raise ValueError(f"Failed to fetch the URL. Status code: {r.status_code}")
			else:
				 raise ValueError(f"Failed to fetch the URL. The status code: {r.status_code}")
			
def trydownloadDailyFiles(date, north, imageOnly=False):
	try:
		downloadDailyFiles(date, north, imageOnly)
	except:
		print('an exception occurred!!!!')
		time.sleep(2)
		downloadDailyFiles(date, north, imageOnly)

def getSic(date, north = False):
	filename = getfilenamenc(date, north)
	#print('file',filename)
	localFilename = './data/' + str(date.year) + '/' + filename
	if not os.path.isfile(localFilename):
		trydownloadDailyFiles(date, north)
	
	f = Dataset(localFilename, 'r', format="NETCDF4")
	
	# read sea ice concentration	
	sic = f.variables[('F' if date >= datetime(1987,8,21) else 'N') +  getversion(date) + '_ICECON'][0] #.squeeze()
	f.close()
	return sic

def calculateArea(date, north=False, previousSic = None, twoDaysAgoSic = None, nextSic = None, nsidcGridCellAreas= None, regionalMask= None, validIceFlag= None):
	"""
	Calculate sea ice area for a daily gridded sea ice concentration file. 
    """
	print('date',str(date.year) + '-' + padzeros(date.month) + '-' + padzeros(date.day))
	
	sic = getSic(date, north)
	polehole =  29.234 if (north and date.year >= 2008) else 310.770 if north else 0
	rows = sic.shape[0] #332s #448n
	cols = sic.shape[1] #316s #304n
	totalarea = totalextent = otherarea = otherextent = 0
	wedarea = wedextent = indarea = indextent = pacarea = pacextent = rosarea = rosextent = belarea = belextent = 0
	cabarea = cabextent = beaarea = beaextent = chuarea = chuextent = essarea = essextent = laparea = lapextent = kararea = karextent = 0
	bararea = barextent = grearea = greextent = bafarea = bafextent = lawarea = lawextent = hudarea = hudextent = caaarea = caaextent = 0
	berarea = berextent = okharea = okhextent = japarea = japextent = yelarea = yelextent = balarea = balextent = alaarea = alaextent = 0
	
	for row in range(rows):
		for col in range(cols):
			cellconcentration = sic[row][col]
			valid = validIceFlag[row][col] if north else 1
			if not cellconcentration >= 0 and valid == 1 and previousSic is not None :
				#print('nan', cellconcentration, row, col)
				cellconcentration = previousSic[row][col]
			if not cellconcentration >= 0 and valid == 1 and nextSic is not None :
				#print('nan', cellconcentration, row, col)
				cellconcentration = nextSic[row][col]
			if not cellconcentration >= 0 and valid == 1 and twoDaysAgoSic is not None :
				#print('nan', cellconcentration, row, col)
				cellconcentration = twoDaysAgoSic[row][col]
			if cellconcentration > 0 and valid == 1 and previousSic is not None and not previousSic[row][col] >= 0 and nextSic is not None and not nextSic[row][col] >= 0:
				#print('nan', cellconcentration, row, col)
				cellconcentration = 0			
			if(cellconcentration > 0.15):
				valid = validIceFlag[row][col] if north else 1
				if valid != 1:
					continue
				cellarea = nsidcGridCellAreas[row][col]
				cellregion = regionalMask[row][col]
				extent = round(float(cellarea/1000000000),4)			
				area = round(float(cellconcentration*extent),4)
			
				totalarea += area
				totalextent += extent
				if(cellregion == 1):
					wedarea += area
					wedextent += extent
				elif(cellregion == 2):
					indarea += area
					indextent += extent
				elif(cellregion == 3):
					pacarea += area
					pacextent += extent
				elif(cellregion == 4):
					rosarea += area
					rosextent += extent
				elif(cellregion == 5):
					belarea += area
					belextent += extent
				elif(cellregion == 6):
					kararea += area
					karextent += extent
				elif(cellregion == 7):
					bararea += area
					barextent += extent
				elif(cellregion == 8):
					grearea += area
					greextent += extent
				elif(cellregion == 9):
					bafarea += area
					bafextent += extent	
				elif(cellregion == 10):
					lawarea += area
					lawextent += extent
				elif(cellregion == 11):
					hudarea += area
					hudextent += extent	
				elif(cellregion == 12):
					caaarea += area
					caaextent += extent	
				elif(cellregion == 13):
					berarea += area
					berextent += extent	
				elif(cellregion == 14):
					okharea += area
					okhextent += extent	
				elif(cellregion == 15):
					japarea += area
					japextent += extent	
				elif(cellregion == 16):
					yelarea += area
					yelextent += extent	
				elif(cellregion == 17):
					balarea += area
					balextent += extent	
				elif(cellregion == 18):
					alaarea += area
					alaextent += extent	
				else:
					print('other', row, col, cellregion, cellconcentration, validIceFlag[row][col])
					otherarea += area
					otherextent += extent
					# if row < 369:
						# print('other:', row, col, cellregion, cellconcentration, validIceFlag[row][col])

	print('total area', totalarea + polehole)
	print('total extent', totalextent + polehole)
	dayofyear = date.timetuple().tm_yday
	aday.append(dayofyear)
	ayear.append(date.year)
	
	atotalarea.append(totalarea + polehole)
	atotalextent.append(totalextent + polehole)
	apolehole.append(polehole)
	awedarea.append(wedarea)
	awedextent.append(wedextent)
	aindarea.append(indarea)
	aindextent.append(indextent)
	apacarea.append(pacarea)
	apacextent.append(pacextent)
	arosarea.append(rosarea)
	arosextent.append(rosextent)
	abelarea.append(belarea)
	abelextent.append(belextent)
	
	aotherarea.append(otherarea)
	aotherextent.append(otherextent)
	
	akararea.append(kararea)
	akarextent.append(karextent)
	abararea.append(bararea)
	abarextent.append(barextent)
	agrearea.append(grearea)
	agreextent.append(greextent)
	abafarea.append(bafarea)
	abafextent.append(bafextent)
	alawarea.append(lawarea)
	alawextent.append(lawextent)
	ahudarea.append(hudarea)
	ahudextent.append(hudextent)
	acaaarea.append(caaarea)
	acaaextent.append(caaextent)
	
	aberarea.append(berarea)
	aberextent.append(berextent)
	aokharea.append(okharea)
	aokhextent.append(okhextent)
	ajaparea.append(japarea)
	ajapextent.append(japextent)
	ayelarea.append(yelarea)
	ayelextent.append(yelextent)
	abalarea.append(balarea)
	abalextent.append(balextent)
	aalaarea.append(alaarea)
	aalaextent.append(alaextent)
	
	return sic
	
def appendNan(date):
	print('inside append nan')
	dayofyear = date.timetuple().tm_yday
	aday.append(dayofyear)
	ayear.append(date.year)
	
	atotalarea.append(np.NAN)
	atotalextent.append(np.NAN)
	apolehole.append(np.NAN)
	aotherarea.append(np.NAN)
	aotherextent.append(np.NAN)
	
	awedarea.append(np.NAN)
	awedextent.append(np.NAN)
	aindarea.append(np.NAN)
	aindextent.append(np.NAN)
	apacarea.append(np.NAN)
	apacextent.append(np.NAN)
	arosarea.append(np.NAN)
	arosextent.append(np.NAN)
	abelarea.append(np.NAN)
	abelextent.append(np.NAN)
	
	akararea.append(np.NAN)
	akarextent.append(np.NAN)
	abararea.append(np.NAN)
	abarextent.append(np.NAN)
	agrearea.append(np.NAN)
	agreextent.append(np.NAN)
	abafarea.append(np.NAN)
	abafextent.append(np.NAN)
	alawarea.append(np.NAN)
	alawextent.append(np.NAN)
	ahudarea.append(np.NAN)
	ahudextent.append(np.NAN)
	acaaarea.append(np.NAN)
	acaaextent.append(np.NAN)
	
	aberarea.append(np.NAN)
	aberextent.append(np.NAN)
	aokharea.append(np.NAN)
	aokhextent.append(np.NAN)
	ajaparea.append(np.NAN)
	ajapextent.append(np.NAN)
	ayelarea.append(np.NAN)
	ayelextent.append(np.NAN)
	abalarea.append(np.NAN)
	abalextent.append(np.NAN)
	aalaarea.append(np.NAN)
	aalaextent.append(np.NAN)
	
def readRegionMask(north = False):
	filename = 'masks/NSIDCMaskFile.msk.txt'
	#filename = 'region_' + ('n' if north else 's') + '.msk'
	table = []
	with open(filename, 'rb') as file:
		byte = file.read(300)
		for i in range(448 if north else 332):
			row = []
			for j in range(304 if north else 316):
				byte = file.read(1)
				if(byte == b'\x02'):
					row.append(1)
				elif(byte == b'\x03'):
					row.append(2)
				elif(byte == b'\x04'):
					row.append(3)
				elif(byte == b'\x05'):
					row.append(4)
				elif(byte == b'\x06'):
					row.append(5)
				elif(byte == b'\x07'):
					row.append(6)
				elif(byte == b'\x08'):
					row.append(7)
				elif(byte == b'\x09'):
					row.append(8)
				elif(byte == b'\x0a'):
					row.append(9)
				elif(byte == b'\x0b'):
					row.append(10)
				elif(byte == b'\x0c'):
					row.append(11)
				elif(byte == b'\x0d'):
					row.append(12)
				elif(byte == b'\x0e'):
					row.append(13)
				elif(byte == b'\x0f'):
					row.append(14)
				else:
					print(byte)
					row.append(0)
			table.append(row)
	np.savetxt('masks/' + ('' if north else 'ant') + 'arctic-regional-mask-old-binary.csv', table, delimiter=",", fmt="%.0f")

def appendToRegionalCsvAntarctic(filenameshort):
	
	alldata = np.round(np.transpose([ayear, aday, awedarea, awedextent, abelarea, abelextent, arosarea, arosextent, apacarea, apacextent, aindarea, aindextent, aotherarea, aotherextent, atotalarea, atotalextent]), decimals=3)
	format = "%.0f,  %3.0f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f, %8.3f,  %8.3f,  %9.3f,  %9.3f"
	append_to_csv_file.appendToCsvFile(filenameshort, alldata, format)

def appendToRegionalCsvArctic(filenameshort):
	
	alldata = np.round(np.transpose([ayear, aday, awedarea, awedextent, aindarea, aindextent, apacarea, apacextent, arosarea, arosextent, abelarea, abelextent, akararea, akarextent, abararea, abarextent, agrearea, agreextent, abafarea, abafextent, alawarea, alawextent, ahudarea, ahudextent, acaaarea, acaaextent, aberarea, aberextent, aokharea, aokhextent, ajaparea, ajapextent, ayelarea, ayelextent, abalarea, abalextent, aalaarea, aalaextent, aotherarea, aotherextent, apolehole, atotalarea, atotalextent]), decimals=3)
	format = "%.0f,  %3.0f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %8.3f,  %9.3f,  %9.3f"
	append_to_csv_file.appendToCsvFile(filenameshort, alldata, format)
	
def getDateFromDayOfYear(dayOfYear, year):
	if year % 4 == 0:
		monthLengths[1] = 29
	else:
		monthLengths[1] = 28
	for month in range(12):
		if dayOfYear <= monthLengths[month]:
			return datetime(year, month+1, dayOfYear)
		dayOfYear -= monthLengths[month]

def plotLine(ax, lines, dates, idx, label, color, days, skip, linestyle = 'solid'):
	ax.plot(dates, matrix[idx,:], label=label, color=color);

def plotLineFram(ax, lines, dates, idx, label, color, days, skip=0, linestyle = 'solid'):
	line = lines[idx].split(",")			
	row =  np.array([i.lstrip() for i in np.array(line[skip+1:skip+days+1])])
	numberOfDays = len(row)
	row = row.astype(float)
	if numberOfDays < days:
		row = np.pad(row, (0, days - numberOfDays), 'constant', constant_values=(np.nan,))	
	ax.plot(dates, row, label=label, color=color, linestyle=linestyle, linewidth=(3 if idx==-1 else 1));	

def plotCumSum(ax, lines, dates, idx, label, color, linestyle='solid', days=122, linewidth=1):
	#line = lines[idx].replace(',,', ',0,').replace(',,', ',0,')
	#line = line.split(",")	
	line = lines[idx].split(",")			
	row =  np.array([i.lstrip() for i in np.array(line[32:31+days+1])])
	numberOfDays = len(row)
	row = row.astype(float)
	if numberOfDays < days:
		row = np.pad(row, (0, days - numberOfDays), 'constant', constant_values=(np.nan,))	
	ax.plot(dates, row, label=label, color=color, linestyle=linestyle, linewidth=linewidth);	
	return line

def plotAwiCompactness(inputFileName, outputFileName):
	fig, ax = plt.subplots(figsize=(8, 5))
	dates = np.arange(0,122)	
	with open(inputFileName, 'r') as f:
		lines = f.readlines()
	plotCumSum(ax, lines, dates, -13, '2012', (0.0,0.13,0.38))
	plotCumSum(ax, lines, dates, -12, '2013', (0,0.44,0.75))
	plotCumSum(ax, lines, dates, -11, '2014', (0.0,0.69,0.94))
	plotCumSum(ax, lines, dates, -10, '2015', (0,0.69,0.31))
	plotCumSum(ax, lines, dates, -9, '2016', (0.57,0.82,0.31))
	plotCumSum(ax, lines, dates, -8, '2017', (1.0,0.75,0))
	plotCumSum(ax, lines, dates, -7, '2018', (0.9,0.4,0.05))
	plotCumSum(ax, lines, dates, -6, '2019', (1.0,0.5,0.5))
	plotCumSum(ax, lines, dates, -5, '2020', (0.58,0.54,0.33))
	plotCumSum(ax, lines, dates, -4, '2021', (0.4,0,0.2))
	plotCumSum(ax, lines, dates, -3, '2022', (0.7,0.2,0.3))
	plotCumSum(ax, lines, dates, -2, '2023', (0.6,0,0))
	plotCumSum(ax, lines, dates, -1, '2024', (1,0,0), linewidth=3)
	
	#ax.set_xlabel("day")
	ax.set_ylabel("")
	ax.set_title('AWI AMSR2 Compactness (area divided by extent)')
	ax.legend(loc=3, prop={'size': 8})
	ax.axis([0, 122, 0.78, 0.97])
	ax.grid(True);
	
	months = ['Jun', 'Jul', 'Aug', 'Sep']
	ax.set_xticks([0,30,61,92,122], ['', '', '', '', ''])
	ax.xaxis.set_minor_locator(ticker.FixedLocator([15,45.5,76.5,107]))
	ax.xaxis.set_minor_formatter(ticker.FixedFormatter(months))
	ax.tick_params(which='minor', length=0)
		
	print('gonna save fig: ' + outputFileName)
	fig.savefig(outputFileName)

def uploadToGoogleDrive():
	print('uploading nsidc files')
	
	upload_to_google_drive.replace_file_in_google_drive('1JaE-x9MojVqbGwXb-9HW1YmHTN8Y01e3',  "nsidc-area-arctic-basin.png")
	upload_to_google_drive.replace_file_in_google_drive('1vGuFTHOXPt45jQyewjqb2dJrk57u9JJB',  "nsidc-extent-arctic-basin.png")
	#upload_to_google_drive.replace_file_in_google_drive('1bVxxS_vL-Me0tZmJFObWXUkuFespRDql', 'animation_nsidc_arctic_latest.gif')
	#upload_to_google_drive.replace_file_in_google_drive('1KolCPopm7yo_dCUJPZCcwNL9FoDo73CF', 'animation_nsidc_antarctic_latest.gif')
	
	#upload_to_google_drive.replace_file_in_google_drive('1m9m5RlLPmFwGGKl36tlIaJysx5zA3i5c', 'nsidc-area-antarctic.png')
	upload_to_google_drive.replace_file_in_google_drive('1KohN9zZgXZGuDl2cpEhBjSH8fpuNVAer', 'nsidc-area-weddell.png')
	upload_to_google_drive.replace_file_in_google_drive('10Ab89xQgiKmGhHT-0-sEhE-w1OPzbPoL', 'nsidc-area-bellamu.png')
	upload_to_google_drive.replace_file_in_google_drive('1DGxMmM0Bb3EE7HCxxWlA2a4GxX5aaK9s', 'nsidc-area-ross.png')
	upload_to_google_drive.replace_file_in_google_drive('11raJp7qK1s3mi1FPKKf2YaYEFS4FPG_D', 'nsidc-area-pacific.png')
	upload_to_google_drive.replace_file_in_google_drive('1ZLTXlWI2bj4RJhyLFR0sK8LpaCHd_nLr', 'nsidc-area-indian.png')
	
	#upload_to_google_drive.replace_file_in_google_drive('1YbC53tcaN7RM_nLctdb3RiIk--tf2yYN', 'nsidc-extent-antarctic.png')
	upload_to_google_drive.replace_file_in_google_drive('1_OwX00I2i4aQWebiskFdwprCgoxMpDPL', 'nsidc-extent-weddell.png')
	upload_to_google_drive.replace_file_in_google_drive('1zfnZ4mTkTg5lthXJlAGWQRN54aGoetMj', 'nsidc-extent-bellamu.png')
	upload_to_google_drive.replace_file_in_google_drive('1T6pYN-Z-wx60l6L9WzGziaS_Nd4t6_vV', 'nsidc-extent-ross.png')
	upload_to_google_drive.replace_file_in_google_drive('1F-qiSsGBrXJ9BN6g55vxnnwS3cXl0H7e', 'nsidc-extent-pacific.png')
	upload_to_google_drive.replace_file_in_google_drive('1OV7L7ltwfwz-Ap8psaPXRHQRIF2YhOLT', 'nsidc-extent-indian.png')
	
	#upload_to_google_drive.replace_file_in_google_drive('1FX_GFw-ERwHKxvdnvFhAVO8ErSfL91Wy', 'nsidc-area-arctic.png')
	upload_to_google_drive.replace_file_in_google_drive('1SK9V27jYpGVDpNtqDTlBUkB4D8ZGneWP', 'nsidc-area-cab.png')
	upload_to_google_drive.replace_file_in_google_drive('1X1lWweMcpsw_2bi3g_pjwv5dZHcsaZZj', 'nsidc-area-beaufort.png')
	upload_to_google_drive.replace_file_in_google_drive('1pWi1bPIpIfNozbk84OKM6iQ8rOmuBh_M', 'nsidc-area-chukchi.png')
	upload_to_google_drive.replace_file_in_google_drive('1sJ__tymFG91z9EEp37y6f-bCpvVlJPBQ', 'nsidc-area-ess.png')
	upload_to_google_drive.replace_file_in_google_drive('1532hxhVKqwAH0fOZ55fwrBsnojdD_uua', 'nsidc-area-laptev.png')
	upload_to_google_drive.replace_file_in_google_drive('1V3FNZ3H-_GhYrQfHYIsEOnt1KQnzUryU', 'nsidc-area-kara.png')
	upload_to_google_drive.replace_file_in_google_drive('1YWbmyOEjpCppxm7qHmSfKpGhrgBqAa5u', 'nsidc-area-barents.png')
	upload_to_google_drive.replace_file_in_google_drive('1MzPsYmCnp_nJW3SX3VGOyc5RygqrC2YO', 'nsidc-area-greenland.png')
	upload_to_google_drive.replace_file_in_google_drive('1zkIim8m5z2aBE7QuUCvo1ERKtc6SSOQo', 'nsidc-area-baffin.png')
	upload_to_google_drive.replace_file_in_google_drive('1pTAR7pGC37rNkSsyKPk_vHdFIZ3uLb9y', 'nsidc-area-hudson.png')
	upload_to_google_drive.replace_file_in_google_drive('1k2ejRQ4zGpP-i7zoadRi3e5yOWUg869l', 'nsidc-area-caa.png')
	upload_to_google_drive.replace_file_in_google_drive('1ZipPCM6whEtbz2Qs9BSIY32v6Kyk_LkM', 'nsidc-area-bering.png')
	upload_to_google_drive.replace_file_in_google_drive('1JVa4hM3S_h8RngUQUsJWvNkkesizJOzH', 'nsidc-area-okhotsk.png')
	
	#upload_to_google_drive.replace_file_in_google_drive('1O_bJCQlEnBQ3pnTcSs4F7uhenffPJfjI', 'nsidc-extent-arctic.png')
	upload_to_google_drive.replace_file_in_google_drive('1a-qWiILcOBiJwaxnjej1LkMU8tPKf1Q4', 'nsidc-extent-cab.png')
	upload_to_google_drive.replace_file_in_google_drive('1BricwOk7b2vhHgSe7kUmWykbtfNZIG6B', 'nsidc-extent-beaufort.png')
	upload_to_google_drive.replace_file_in_google_drive('15D7yItTV-GmvlkFueYoJhrID8-gTl8L2', 'nsidc-extent-chukchi.png')
	upload_to_google_drive.replace_file_in_google_drive('16kZvzbGKeoVfLlKz9iiX98H2PLdvWszU', 'nsidc-extent-ess.png')
	upload_to_google_drive.replace_file_in_google_drive('1uNgIk7EhNagr8CHWBCiu8DbrFJWvlLPO', 'nsidc-extent-laptev.png')
	upload_to_google_drive.replace_file_in_google_drive('1NIP4jd-w_4WV9IpQfaYdomf7Y4iaZPAX', 'nsidc-extent-kara.png')
	upload_to_google_drive.replace_file_in_google_drive('1aDp13YI4cJKghVXmdtUf2bpiq7AFfB9M', 'nsidc-extent-barents.png')
	upload_to_google_drive.replace_file_in_google_drive('10ll8DG31lVwRKdCregVoi1cIh6-Eg5ZQ', 'nsidc-extent-greenland.png')
	upload_to_google_drive.replace_file_in_google_drive('1jwf-jZbJgVy5Z8CDvnwB6hj3Nm9eHtIc', 'nsidc-extent-baffin.png')
	upload_to_google_drive.replace_file_in_google_drive('1XZlRthfiwwI0o7K8oqatkF1xfsXdoet0', 'nsidc-extent-hudson.png')
	upload_to_google_drive.replace_file_in_google_drive('1YHIe3V3fLhGsbYOTlYlaWzls9SNu9FhA', 'nsidc-extent-caa.png')
	upload_to_google_drive.replace_file_in_google_drive('1lnZUbGibYqvsQaNKXyErTQ6rAJdBredB', 'nsidc-extent-bering.png')
	upload_to_google_drive.replace_file_in_google_drive('1g2ofXKXrV7HvFCgtsnz8mggIsO2S_TUI', 'nsidc-extent-okhotsk.png')

missingdates = [datetime(2024,9,12),datetime(2024,9,13),datetime(2024,9,14),datetime(2024,9,15),datetime(2024,9,16),datetime(2024,9,17),datetime(2025,3,8)]

def processAuto():
	hemisphere = "arctic" if north else "antarctic"
	filename = 'nsidc-' + hemisphere + '-regional-area-and-extent'
	print('inside process auto', north, hemisphere)
	
	dropbox_client.downloadFromDropbox([filename + '.csv'])
	lastSavedYear,lastSavedDay = get_last_saved_day.getLastSavedDay(filename + '.csv')
	lastSavedDayAsDate = getDateFromDayOfYear(lastSavedDay, lastSavedYear)

	yesterday = datetime.today() - timedelta(days = 1)
	yesterday = datetime(yesterday.year, yesterday.month, yesterday.day)
	startdate = lastSavedDayAsDate + timedelta(days = 1) #yesterday + timedelta(days = -5)#todo temp#lastSavedDayAsDate + timedelta(days = 1)
	#startdate = yesterday #temp!!!
	date = startdate
	enddate = yesterday if auto else datetime(2024,2,3) #yesterday + timedelta(days = -1)#todo temp 
	
	print('dates',date,enddate)
	while date <= enddate:
		trydownloadDailyFiles(date, north)		
		date = date + timedelta(days = 1)

	nsidcGridCellAreas = np.loadtxt(open("masks/cell_area_" + hemisphere + ".csv", "rb"), delimiter=",", skiprows=0)
	print(nsidcGridCellAreas.shape)

	regionalMask = np.loadtxt(open('masks/sea_ice_region_arctic.csv' if north else 'masks/antarctic-regional-mask-binary.csv', "rb"), delimiter=",", skiprows=0) #'sea_ice_region_NASA.csv'
	print(regionalMask.shape)
			
	date = startdate
	previousDay = date - timedelta(days = 1)
	twoDaysAgo = date - timedelta(days = 2)
	previousSic = getSic(date - timedelta(days = 1), north) if not previousDay in missingdates else None
	twoDaysAgoSic = getSic(twoDaysAgo, north) if not twoDaysAgo in missingdates else None

	#enddate = yesterday if auto else datetime(2023,12,18)
	nextSic = None
	while date <= enddate:
		try:
			nextDay = date + timedelta(days = 1)
			if date < enddate and not nextDay in missingdates:
				nextSic = getSic(nextDay, north)
			else:
				nextSic = None
	
			validIceFlag = np.loadtxt(open("masks/valid_ice_flag_" + padzeros(date.month) + ".csv", "rb"), delimiter=",", skiprows=0)		
			print('inside process auto bis', north, hemisphere)
			if(date.month != 2 or date.day != 29): # skip leap days
				currentSic = calculateArea(date, north, previousSic, twoDaysAgoSic, nextSic, nsidcGridCellAreas, regionalMask, validIceFlag)
				twoDaysAgoSic = previousSic
				previousSic = currentSic
		except:
			#appendNan(date)
			raise
		date = date + timedelta(days = 1)
	#exit() #todo temp
	animationfilename = 'animation_nsidc_' + hemisphere + '_latest.gif'
	animationdate = yesterday + timedelta(days = 1)
	try:
		frames = 10
		numberOfAddedImages = 0
		missingDatesForImages = []
		while numberOfAddedImages < frames:
			animationdate = animationdate - timedelta(days = 1)
			if animationdate in missingdates:
				print('abort downloading missing date: ', animationdate)
				continue
	
			localfolder = './data/' + str(animationdate.year)
			if not os.path.isdir(localfolder):
				os.makedirs(localfolder, exist_ok=True)
			pngFilename = localfolder + "/" + getfilenamepng(animationdate, north)
			if not os.path.isfile(pngFilename):
				try:
					trydownloadDailyFiles(animationdate, north, True)
				except:
					print('Abort downloading missing date: ', animationdate)
					missingDatesForImages.append(animationdate)
					continue
			numberOfAddedImages += 1
		make_animation.makeAnimation(yesterday, frames, animationfilename, lambda date: "data/" + str(date.year) + "/" + getfilenamepng(date,north), missingDatesForImages)
	except:
		if auto:
			print('exception occurred, removing last data')
			os.remove("data/" + str(enddate.year) + "/" + getfilenamepng(enddate,north))
			os.remove("data/" + str(enddate.year) + "/" + getfilenamenc(enddate,north))
			raise

	#if len(aday) == 0:
	#	exit()
		
	if north:
		appendToRegionalCsvArctic(filename)
		plotRegionalGraphsArctic(filename)
		updateTotalAreaAndExtentFilesArctic(filename, date.year)
		
		extentSummary = generateSummary(filename, True)
		areaSummary = generateSummary(filename, False)
		extentRankSummary = generateRankSummary(filename, True)
		areaRankSummary = generateRankSummary(filename, False)

		filenames = [filename + ".csv", "nsidc-arctic-area.csv", "nsidc-arctic-extent.csv", animationfilename, extentSummary, areaSummary, extentRankSummary, areaRankSummary]
	else:
		appendToRegionalCsvAntarctic(filename)
		plotRegionalGraphsAntarctic(filename)
		updateTotalAreaAndExtentFilesAntarctic(filename, date.year)
		
		extentSummary = generateSummary(filename, True)
		areaSummary = generateSummary(filename, False)
		extentRankSummary = generateRankSummary(filename, True)
		areaRankSummary = generateRankSummary(filename, False)
		
		filenames = [filename + ".csv", "nsidc-antarctic-area.csv", "nsidc-antarctic-extent.csv", animationfilename, extentSummary, areaSummary, extentRankSummary, areaRankSummary] 

	if putOnDropbox:
		dropbox_client.uploadToDropbox(filenames)
	
atotalarea = []
atotalextent = []
apolehole = []
awedarea = []
awedextent = []
aindarea = []
aindextent = []
apacarea = []
apacextent = []
arosarea = []
arosextent = []
abelarea = []
abelextent = []
aotherarea = []
aotherextent = []

acabarea = []
acabextent = []
abeaarea = []
abeaextent = []
achuarea = []
achuextent = []
aessarea = []
aessextent = []
alaparea = []
alapextent = []

akararea = []
akarextent = []
abararea = []
abarextent = []
agrearea = []
agreextent = []
abafarea = []
abafextent = []
alawarea = []
alawextent = []
ahudarea = []
ahudextent = []
acaaarea = []
acaaextent = []

aberarea = []
aberextent = []
aokharea = []
aokhextent = []
ajaparea = []
ajapextent = []
ayelarea = []
ayelextent = []
abalarea = []
abalextent = []
aalaarea = []
aalaextent = []

ayear = []
aday = []

auto = True  # change this to False when running the code manually

if auto:
	north = True
	processAuto()
	
	north = False
	processAuto()
	if putOnGoogleDrive:
		time.sleep(3)	
		uploadToGoogleDrive()
else: # for running the code manually
	putOnDropbox = False
	north = False
	hemisphere = "arctic" if north else "antarctic"
	filename = 'nsidc-' + hemisphere + '-regional-area-and-extent'
	
	#dropbox_client.downloadFromDropbox([filename + '.csv'])

	#updateTotalAreaAndExtentFilesAntarctic(filename, 2025)	
	#extentSummary = generateSummary(filename, True)
	#extentRankSummary = generateRankSummary(filename, True)
	if north:
		plotRegionalGraphsArctic(filename)
	else:
		plotRegionalGraphsAntarctic(filename)
