#!/usr/bin/python
try:
    import cgi, cgitb, urllib, sys, os, HTMLParser, re, subprocess, MySQLdb
    import ntpath, copy, json, boto
    from globVars import *
    from boto.s3.connection import S3Connection
    from dateutil.parser import parse
    from xml.etree import ElementTree as ET
    from bs4 import BeautifulSoup
    from hashlib import md5
    from time import localtime
    from urlparse import urljoin
except Exception, e:
    print "ERROR"
    print e

cgitb.enable()

rssUrl, db, dbConn, feedId, localDirLoc, form = "", "", "", "", "", ""
s3Conn = S3Connection(s3PublicKey, s3PrivateKey)
drBucket = s3Conn.get_bucket(s3Bucket)

def connectToDB():
    """
        connectToDB connects to the database that stores the users, feeds, and
        items.
        PARAMS: NONE
        RETURN: NONE
    """
    global db, dbConn
    try:
        db = MySQLdb.connect(host = dbHost, # your host, usually localhost
                             user = dbUser, # your username
                             passwd = dbPasswd, # your password
                             db = dbDb) # name of the data base
        dbConn = db.cursor()
    except MySQLdb.IntegrityError, e:
        print "Could not connect to database: " + e

def validateUrl():
    """
        validateUrl ensures that the URL is properly formatted (and exists).
        PARAMS: NONE
        RETURN: True if the URL is valid.
    """
    global rssUrl
    valUrl = rssUrl
    try:
        ET.parse(urllib.urlopen(valUrl))
    except:
        valUrl = "http://" + valUrl
        try:
            ET.parse(urllib.urlopen(valUrl))
        except:
            return False
    return True

def urlGiven():
        """
        urlGiven determines if the user has submitted the form
        and is waiting for a file to be parsed.
        PARAMS: NONE
        RETURN: BOOL -- True if user is waiting for RSS file
                False otherwise
        """
        submitted = form.getvalue('submitted')
        try:
                return submitted
        except:
                return False


def getFormHtml():
        """
        getFormHtml outputs HTML for the form
        PARAMS: NONE
        RETURN: The HTML for the form
        """
        formHtml = """
            <div class="container">
            <form id='duprssForm' action='#' method='POST' novalidate \
            autocomplete='off'>
            <div class="inputs">
            <div class="header">
            <h3>DupRSS</h3>
            <p>A tool to mirror RSS Feeds</p>
            </div>
            <div class="sep"></div><br />
            <input type="url" name='rssUrl' id = 'rssUrl' \
            placeholder="RSS Link" noValidate autofocus required />
            <a id="check" href="#">Check Feed</a>
            <a id="submit" href="#">Mirror Feed</a>
            </div>
            </form>
            </div>
            """
        return formHtml

def checkFeed():
    """
        insertFeed inserts the feed that corresponds to the URL input by the
        user if it has not yet been inserted.
        PARAMS: NONE
        RETURN: NONE
    """
    global rssUrl, dbConn, feedId, localDirLoc
    
    try:
        # Tests if a feed from this URL exists for this user. Set feedId.
        rssUrl = rssUrl.replace('www.','') # Remove www.
        try:
            tryUrl = urllib.urlopen(rssUrl)
        except:
            rssUrl = "http://" + rssUrl
        sql = """SELECT Feed_id, Feed_folder FROM 
            Feeds_DupRSS WHERE Feed_url = %s"""
        dbConn.execute(sql, (rssUrl,))
        feeds = dbConn.fetchall()
        if (feeds):
            return updateFoundFeed(feeds)
        # If feed does not exist for this user, insert one. Set feedId.
        else:
            return insertFeed()
    except:
        print "Something went wrong when checking if feed exists"

def insertFeed():
    """
        insertFeed() puts the feed into the database 
        PARAMS: NONE
        RETURN: The feed's ID number
    """
    global feedId, localDirLoc
    
    try:
        rand = getRand()
        sql = """INSERT INTO Feeds_DupRSS(Feed_url, Feed_folder) VALUES 
            (%s, %s)"""
        dbConn.execute(sql, (rssUrl, rand))
        feedId = dbConn.lastrowid
        localDirLoc = "/feeds/" + rand
        rssFile = drBucket.new_key(localDirLoc + '/index.rss')
        rssFile.set_contents_from_string('NO RSS FOUND')
        rssFile.set_acl('public-read');
        db.commit()
    
    except:
        print "Something went wrong while inserting the feed"
        f = open(errorLoc,'w')
        f.write("Something went wrong while inserting the feed") # python will convert \n to os.linesep
        f.close() # you can omit in most cases as the destructor will call if
    return feedId

def updateFoundFeed(feeds):
    """
        updateFoundFeed() deletes the feed from the MySQL database if it does not
        exist in S3. If it does exist in S3, it updates the files in the bucket.
        PARAMS: feeds -- the feed object from MySQL
        RETURN: The feedId if it exists in S3 or False if the feed object
        does not exist in S3.
    """
    global feedId, localDirLoc
    feedId = feeds[0][0]
    localDirLoc = "/feeds/" + feeds[0][1]
    try:
        if (drBucket.get_key(localDirLoc + "/index.rss")):
            db.commit()
            return feedId
        else:
            sql = """DELETE FROM Feeds_DupRSS WHERE Feed_url = %s"""
            dbConn.execute(sql, (rssUrl,))
            sql = """DELETE FROM Items_DupRSS WHERE Item_feed = %s"""
            dbConn.execute(sql, (feedId,))
            db.commit()
            insertFeed()
            return False
    except:
        f = open(errorLoc,'w')
        f.write("Something went wrong while updating the feed!") # python will convert \n to os.linesep
        f.close() # you can omit in most cases as the destructor will call if

def getRand():
    """
        getRand() generates a pseudo-random string.
        PARAMS: NONE
        RETURN: A pseudo-random string.
    """
    return "%s" % (md5(str(localtime())).hexdigest())


def main():
    global rssUrl, localDirLoc, form
    form = cgi.FieldStorage()
    isSubmitted = urlGiven()
    if (isSubmitted):
        sys.stdout.write("Content-Type: application/json")
        sys.stdout.write("\n")
        sys.stdout.write("\n")
        rssUrl = form.getvalue('rssUrl')
        result = { }
        result['message'] = ""
        isValid = validateUrl();
        if (isValid):
            result['success'] = True
            if (isSubmitted == "submitted"):
                connectToDB()
                result['success'] = True
                feedId = checkFeed()
                cmdTxt = (sys.executable + " " + \
                          os.path.dirname(os.path.abspath(__file__)) + \
                          "/copyFeed.py stdRequest " + rssUrl)
                result['message'] = ("Your feed can be found at: " + serverDir +
                                     localDirLoc + "/index.rss")
                subprocess.Popen(cmdTxt, bufsize=0,
                                 stdin=open("/dev/null", "r"),
                                 stdout=open("/dev/null", "w"),
                                 stderr=open("/dev/null", "w"), shell=True)
        else:
            result['success'] = False
        sys.stdout.write(json.dumps(result,indent=1))
        sys.stdout.write("\n")
        sys.stdout.close()
    else:
            print("Content-type: text/html")
            print
            print "<html>"
            print "<head>"
            print "<title>DupRSS</title>"
            print "<style>"
            print """body {
                background-color: lightgrey;
                font-family: "Helvetica Neue", Helvetica, Arial;
                padding-top: 20px;
                }
                
                .container {
                width: 500px;
                margin: 0 auto;
                margin-left:30%;
                }
                
                #duprssForm {
                padding: 0px 25px 25px;
                background: #fff;
                box-shadow:
                0px 0px 0px 5px rgba( 255,255,255,0.4 ),
                0px 4px 20px rgba( 0,0,0,0.33 );
                -moz-border-radius: 5px;
                -webkit-border-radius: 5px;
                border-radius: 5px;
                display: table;
                position: static;
                }
                
                #duprssForm .header {
                margin-bottom: 20px;
                }
                
                #duprssForm .header h3 {
                color: #333333;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
                }
                
                #duprssForm .header p {
                color: #8f8f8f;
                font-size: 14px;
                font-weight: 300;
                }
                
                #duprssForm .sep {
                height: 1px;
                background: #e8e8e8;
                width: 500px;
                margin: 0px -25px;
                }
                
                #duprssForm .inputs {
                margin-top: 25px;
                }
                
                #duprssForm .inputs label {
                color: #8f8f8f;
                font-size: 12px;
                font-weight: 300;
                letter-spacing: 1px;
                margin-bottom: 7px;
                display: block;
                }
                
                input::-webkit-input-placeholder {
                color:    #b5b5b5;
                }
                
                input:-moz-placeholder {
                color:    #b5b5b5;
                }
                
                #duprssForm .inputs input[type=url] {
                background: #f5f5f5;
                font-size: 2rem;
                -moz-border-radius: 3px;
                -webkit-border-radius: 3px;
                border-radius: 3px;
                border: none;
                padding: 13px 10px;
                width: 500px;
                margin-bottom: 20px;
                box-shadow: inset 0px 2px 3px rgba( 0,0,0,0.1 );
                clear: both;
                }
                
                #duprssForm .inputs input[type=url]:focus {
                background: #fff;
                box-shadow: 0px 0px 0px 3px #fff38e, inset 0px 2px 3px rgba( 0,0,0,0.2 ), 0px 5px 5px rgba( 0,0,0,0.15 );
                outline: none;
                }
                
                #duprssForm .inputs input[type=url]:required:invalid, input[type=url]:focus:invalid {
                    background-image: url(/x.png);
                    background-position: 445px 8px;
                    background-repeat: no-repeat;
                    padding-right:60px;
                }
                
                #duprssForm .inputs input[type=url]:required:valid, input[type=url]:focus:valid {
                background-position: 445 8;
                padding-right:60px;
                
                background-repeat: no-repeat;
                }
                
                #check {
                float: right;
                margin-bottom:10px;
                }
                
                #duprssForm .inputs #submit {
                width: 100%;
                margin-top: 20px;
                padding: 15px 0;
                color: #fff;
                font-size: 14px;
                font-weight: 500;
                letter-spacing: 1px;
                text-align: center;
                text-decoration: none;
                background: -moz-linear-gradient(
                top,
                #b9c5dd 0%,
                #a4b0cb);
                background: -webkit-gradient(
                linear, left top, left bottom, 
                from(#b9c5dd),
                to(#a4b0cb));
                -moz-border-radius: 5px;
                -webkit-border-radius: 5px;
                border-radius: 5px;
                border: 1px solid #737b8d;
                -moz-box-shadow:
                0px 5px 5px rgba(000,000,000,0.1),
                inset 0px 1px 0px rgba(255,255,255,0.5);
                -webkit-box-shadow:
                0px 5px 5px rgba(000,000,000,0.1),
                inset 0px 1px 0px rgba(255,255,255,0.5);
                box-shadow:
                0px 5px 5px rgba(000,000,000,0.1),
                inset 0px 1px 0px rgba(255,255,255,0.5);
                text-shadow:
                0px 1px 3px rgba(000,000,000,0.3),
                0px 0px 0px rgba(255,255,255,0);
                display: table;
                position: static;
                clear: both;
                }
                
                #duprssForm .inputs #submit:hover {
                background: -moz-linear-gradient(
                top,
                #a4b0cb 0%,
                #b9c5dd);
                background: -webkit-gradient(
                linear, left top, left bottom, 
                from(#a4b0cb),
                to(#b9c5dd));
                }"""
            print "</style>"
            print """<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.9.0/jquery.min.js"></script>"""
            print "<script>"
            print """
                $(document).ready(function(){
                    var canSubmit = false
                    $("#rssUrl").on('input paste propertychange hover', checkUrl);
                    $("#check").on('click', checkUrl);
                    $("#submit").css('display', 'none');
                    
                    function checkUrl() {
                        $.ajax({
                            type: "POST",
                            url: "/DupRSS.cgi",
                            data: {rssUrl: $("#rssUrl").val(), submitted: 'validate'},
                            datatype: 'json',
                            success: function(response){
                                if (response.success) {
                                    $("#rssUrl").css('background-image', "url(/check.png)")
                                    $("body").on("click", "#submit", subUrl);
                                    $("#submit").css("display", "block");
                                } else {
                                    $("#rssUrl").css('background-image', "url(/x.png)")
                                    $("body").off("click", "#submit", subUrl);
                                    $("#submit").css("display", "none");
                                }
                            }
                        });
                    }
                    
                    function subUrl() {
                        $.ajax({
                            type: "POST",
                            url: "/DupRSS.cgi",
                            data: {rssUrl: $("#rssUrl").val(), submitted: 'submitted'},
                            datatype: 'json',
                            success: function(response){
                                $(".inputs").html("<div class='header'>" +
                                "<h3>Your feed has been successfully mirrored!</h3>" +
                                "</div>" +
                                "<div class='sep'></div><br />" +
                                response.message);
                                },
                            error: function(xhr,err, status, response)
                            {
                                alert("Something went wrong! See admin for details.")
                            }
                        });
                    }
                    
                    $(function() {
                    
                    $("form").bind("keypress", function(e) {
                    if (e.keyCode == 13) return false;
                    });
                    
                    });
                });
                """
            print "</script>"
            print "</head>"
            print "<body>"
            formHtml = getFormHtml()
            print formHtml
            print "</body>"
            print "</html>"
main()
