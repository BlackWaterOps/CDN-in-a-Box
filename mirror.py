#This Software is all Rights Reserved CDN in a Box Copyright, 2008-2014
#CDN in a Box is free for non-commercial use.
#If you run ads on your website, or you sell services or merchandise you are commercial use.
#A license can be obtained through http://www.cdninabox.com/
#Full Versions of this software can be used on Naked Domains, or support multiple domains
#Licensed under Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International
# https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode
import re
import pickle
import hashlib
import webapp2
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.api import mail



#the SendMail has to be an admin of your AppEngine
#the contact mail will get an email if the root page errors. This can just be it being slow.
sendmail = 'you@gmail.com'
contactmail = 'you@gmail.com'


# This only works if the original is a naked domain
# content to mirror
stripcomments = True
stripwhitespace = True

#Wordpress likes to use it's own version of JQ, This swaps it for a version served by Google
jqreplace = True
jqversion = '1.11.1'

#Adds Title Tags to Anchors, and a Description if there is none.
doseo = True

#This is your install location. If running local it will be 'localhost:8080' if Appengine with out domain will be something.appspot.com
defaultinstalldomain = 'localhost:8080'

#Typically this will be the Naked Domain, Set up Appengine to be the www for the domain.
source = 'xyhd.tv'
#todo support multiple domains (paid license only)

#this is the time in seconds URL Fetch will wait. If you set to 60 things will break, if you set to small things may timeout.
howslow = 45

#CACHE_EXPIRE time in Seconds remember that if you set 60 and your content changes you might not see it for a minute.
CACHE_EXPIRE = 3600
CACHE_EXPIRE_ROOT = 120





def bw_proxy(url,method = 'get',postdata = '',domain = '', headers = ''):
    if domain == '':
        domain = defaultinstalldomain
    if method == 'get':
        urlhash = str(hashlib.md5(url))
        urldata = memcache.get(urlhash)
        if urldata is not None:
            result = pickle.loads(urldata)
        else:
            result = urlfetch.fetch(url,deadline=howslow)
            memcache.add(urlhash,pickle.dumps(result),CACHE_EXPIRE)


        #to make a broad proxy don't do the replace below, and adjust the source to be ''
        result.content = (result.content).replace('http://'+ source, 'http://www.'+ source)
        result.content = (result.content).replace('http://www.'+ source, 'http://'+ domain)
    else:
        result = urlfetch.fetch(url,method=urlfetch.POST,payload=postdata,headers=headers)
        #to make a broad proxy don't do the replace below, and adjust the source to be ''
        result.content = (result.content).replace('http://'+ source, 'http://www.'+ source)
        result.content = (result.content).replace('http://www.'+ source, 'http://'+ domain)


    #Detect html crude
    if '</p>' in result.content or '</a>' in result.content:
    #serve Jquery from Google
        if jqreplace == True:
            result.content = re.sub('[\'\"]http://.*?jquery[.]js.*?[\'\"]',"'//ajax.googleapis.com/ajax/libs/jquery/" + jqversion + "/jquery.min.js'",result.content)

    #strip comments
        if stripcomments == True:
            result.content = re.sub('[<][!].*?[-][>]',"",result.content)
            result.content = re.sub('[<][!][-].*?[>]',"",result.content)
        if stripwhitespace == True:
            result.content = re.sub('\t|\n',"",result.content)
        if doseo == True:
            if '<meta name="description"' not in result.content and '<title>' in result.content:
                title = re.search('<title>(.*)</title>', result.content, re.IGNORECASE)
                result.content = result.content.replace('<title>','<meta name="description" content="' + source + ' page about '  + title.group(1) + '"><title>')
            for link in re.findall(r"<a.*?</a>",result.content):
                if 'title' not in link:
                    linktitle = re.search('>(.*)<',link)
                    if '<' not in linktitle.group(1):
                        linkreplacement = link.replace('href','title="'+ linktitle.group(1) +'" href')
                        result.content = result.content.replace(link,linkreplacement )
        result.content = result.content.replace('http:///','http://')
    return result

class mirror(webapp2.RequestHandler):
    def get(self):
        servingdomain = self.request.url.split(self.request.path)[0][7:]
        if self.request.query_string != '':
            urltofetch = 'http://www.' + source + self.request.path +'?'+  self.request.query_string
        else:
            urltofetch = 'http://www.' + source + self.request.path
        try:
            toout = bw_proxy(urltofetch,domain = servingdomain)
        except:
            if len(self.request.path) <= 1:
                message = mail.EmailMessage(sender=sendmail,
                            subject=source + ' is down')

                message.to = contactmail
                message.body = source + ' is down'

                message.send()
        self.response.headers = toout.headers
        if len(self.request.path) <= 1:
            self.response.headers['Cache-Control'] = 'public, max-age=%d' % CACHE_EXPIRE_ROOT
        else:
            self.response.headers['Cache-Control'] = 'public, max-age=%d' % CACHE_EXPIRE
        self.response.headers['Pragma'] = 'Public'
        self.response.out.write(toout.content)

    def post(self):
        servingdomain = self.request.url.split(self.request.path)[0][7:]
        if self.request.query_string != '':
            urltofetch = 'http://www.' + source + self.request.path +'?'+  self.request.query_string
        else:
            urltofetch = 'http://www.' + source + self.request.path
        postdata = self.request.body
        toout = bw_proxy(urltofetch, method = 'post', postdata = postdata,headers = self.request.headers,domain=servingdomain)
        self.response.headers = toout.headers
        self.response.headers['Cache-Control'] = 'public, max-age=%d' % CACHE_EXPIRE
        self.response.headers['Pragma'] = 'Public'
        self.response.out.write(toout.content)


app = webapp2.WSGIApplication([
    (r"/", mirror),
    (r"/.*",mirror)])