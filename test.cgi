#!/usr/local/bin/python2.7
print("Content-type: text/html")
print
import cgi, cgitb, urllib, sys, os, tempfile
import xml.etree.ElementTree as ET
import zipfile
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import tostring
from shutil import copyfileobj
import sys
try:
	import feedparser
except:
	print "BANG"
