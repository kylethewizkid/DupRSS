#!/var/chroot/home/content/20/9302720/html/cgi/myenv/bin/python2.7
import cgi, cgitb, urllib, sys, os, tempfile
import xml.etree.ElementTree as ET
import zipfile
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import tostring
from shutil import copyfileobj
import datetime
import sys
import feedparser
import ast
import HTMLParser
from bs4 import BeautifulSoup
#import BeautifulSoup
from django.template import Template
import PyRSS2Gen

cgitb.enable()
form = cgi.FieldStorage()

def urlGiven():
	submitted = form.getvalue('submitted')
	try:
        	return submitted
    	except:
        	return False
    

def getFormHtml():
	formHtml = """
	<form action='#' method='POST'>
    	URL: <input type='text' name='rssUrl'><br />
    	<input type='hidden' name='submitted' value='True' />
    	<input type='submit' value='Submit' />
    	</form>
    	"""
    	return formHtml

def getFeedHtml(tempDir, zipFile):
	rssUrl = form.getvalue('rssUrl')
	try:
   		tryUrl = urllib.urlopen(rssUrl)
    	except:
		rssUrl = "http://" + rssUrl
	rssUrl = urllib.urlopen(rssUrl)
	rssFile = rssUrl.read()
	rssUrl.close()
	soup = BeautifulSoup("".join(rssFile))
	h = HTMLParser.HTMLParser()
	for i in soup.find_all('item'):
	    	d = BeautifulSoup(h.unescape(i.description.string))
    		try:
			tempFile = tempfile.NamedTemporaryFile(delete=False, dir=tempDir)
        	        tempName = tempFile.name
                	tempFile.write(urllib.urlopen(d.img['src']).read())
                	tempFile.close()
			d.img['src'] = "/images/" + os.path.basename(tempName)
	                zipFile.write(tempName,"RSS Feed/images/" + os.path.basename(tempName))
			#print i
			i.description.string = str(d)
			#print "***"
			#print i
		except Exception, e:
			pass
			#print e
	#print("Content-type: text/html")
	#print
	#print str(soup)
	parsed_feed = feedparser.parse(str(soup))

	items = [
    		PyRSS2Gen.RSSItem(
        	title = x.title,
        	link = x.link,
        	description = x.summary,
  	        guid = x.link,
	        #pubDate = datetime.datetime(
			#x.modified_parsed[0],
    		        #x.modified_parsed[1],
       		     	#x.modified_parsed[2],
            		#x.modified_parsed[3],
           		#x.modified_parsed[4],
            		#x.modified_parsed[5])
        	)

    	for x in parsed_feed.entries
	]

	# make the RSS2 object
	# Try to grab the title, link, language etc from the orig feed

	rss = PyRSS2Gen.RSS2(
    		title = parsed_feed['feed'].get("title"),
    		link = parsed_feed['feed'].get("link"),
    		description = parsed_feed['feed'].get("description"),
		#image = parsed_feed['feed'].get("image"),	
    		language = parsed_feed['feed'].get("language"),
    		copyright = parsed_feed['feed'].get("copyright"),
    		managingEditor = parsed_feed['feed'].get("managingEditor"),
    		webMaster = parsed_feed['feed'].get("webMaster"),
   		pubDate = parsed_feed['feed'].get("pubDate"),
    		lastBuildDate = parsed_feed['feed'].get("lastBuildDate"),
		
    		categories = parsed_feed['feed'].get("categories"),
    		generator = parsed_feed['feed'].get("generator"),
    		docs = parsed_feed['feed'].get("docs"),
		
    		items = items
	)

	actualRss = str(soup)
	return actualRss

def compileFeed(actualRss, tempDir):
	tempFile = tempfile.NamedTemporaryFile(delete=False, dir=tempDir, suffix='.rss')
	tempFile.write(actualRss)
	tempFile.close()
	return tempFile


def main():
	feedName = "NONE"
    	if (urlGiven()):
		rssUrl = form.getvalue('rssUrl')
		tempDir = tempfile.mkdtemp()
		zipFile = zipfile.ZipFile(tempDir + 'z', 'w')
        	actualRss = getFeedHtml(tempDir, zipFile)
		tempFile = compileFeed(actualRss, tempDir)
		tempName = tempFile.name
		zipFile.write(tempName,"RSS Feed/" + os.path.basename(tempName))
		zipFile.close()
		pass
		print 'Content-Type:application/octet-stream; name=' + rssUrl + '.zip' 
		print 'Content-Disposition: attachment; filename=' + rssUrl + '.zip'
		print
		with open(tempDir + 'z','rb') as zipped:
			print zipped.read()
	else:
		print("Content-type: text/html")
		print
		print "<html>"
		print "<body>"
    		formHtml = getFormHtml()
    		print formHtml
        	print "</body>"
		print "</html>"
main()
