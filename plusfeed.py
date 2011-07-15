from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
import re
import logging
from google.appengine.api import memcache

from google.appengine.dist import use_library
use_library('django', '1.2')

from django.utils import simplejson as json
from django.utils import feedgenerator
from django.utils.html import strip_tags
from datetime import datetime

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write("""
            <html>
                <head>
                <title>Google Plus Feed</title>
                </head>
                <body>
                    <h1>Unofficial Google+ User Feed</h1>
                    <p>
                    Add the Google+ user number at the end of this URL for their profile feed. Like this: <a href="http://plusfeed.appspot.com/104961845171318028721">http://plusfeed.appspot.com/104961845171318028721</a>.
                    </p>
                    <p>
                    Note: The feed will only display *public* items - if none of your posts are public, the feed won't work.
                    </p>
                    <p>
                    You can grab the source for this app here: <a href="http://www.russellbeattie.com/download/plusfeed.zip">http://www.russellbeattie.com/download/plusfeed.zip</a>
                    </p>
                </body>
              </html>""")


class FeedPage(webapp.RequestHandler):
    def get(self, p):
        
        op = memcache.get(p)
        if op is not None:
            self.response.headers['Content-Type'] = 'application/atom+xml'
            self.response.out.write(op)
            return
    
        try:
            url = 'https://plus.google.com/_/stream/getactivities/' + p + '/?sp=[1,2,"' + p + '",null,null,null,null,"social.google.com",[]]'
            result = urlfetch.fetch(url)
            if result.status_code == 200:
                regex = re.compile(',,',re.M)
                txt = result.content
                txt = txt[5:]
                txt = regex.sub(',null,',txt)
                txt = regex.sub(',null,',txt)
                txt = txt.replace('[,','[null,')
                txt = txt.replace(',]',',null]')
                obj = json.loads(txt)
                
                posts = obj[1][0]

                if not posts:
                    self.error(400)
                    self.response.out.write('<h1>400 - No Public Items Found</h1>')
                    return


                author = posts[0][3]
                
                feed = feedgenerator.Atom1Feed(
                    title = "Google Plus User Feed - " + author, 
                    link = "https://plus.google.com/" + p,
                    description = "Unofficial feed for Google Plus",
                    language = "en",
                    author_name = author,
                    feed_url = "http://plusfeeds.appspot.com/" + p)
                
                # self.response.headers['Content-Type'] = 'text/plain'
                for post in posts:
                    logging.info('post ' + post[21])
                    dt = datetime.fromtimestamp(float(post[5])/1000)
                    permalink = "https://plus.google.com/" + post[21]
                    
                    desc = ''
                    
                    if post[47]:
                        desc = post[47]                    
                    elif post[4]:
                        desc = post[4]

                    if post[44]:
                        desc = desc + ' <br/><br/><a href="https://plus.google.com/' + post[44][1] + '">' + post[44][0] + '</a> originally shared this post: ';
                    
                    if post[66]:
                        
                        if post[66][0][1]:                        
                            desc = desc + ' <br/><br/><a href="' + post[66][0][1] + '">' + post[66][0][3] + '</a>'

                        if post[66][0][6]:
                            if post[66][0][6][0][1].find('image') > -1:
                                desc = desc + ' <p><img src="http:' + post[66][0][6][0][2] + '"/></p>'
                            else:
                                desc = desc + ' <a href="' + post[66][0][6][0][8] + '">' + post[66][0][6][0][8] + '</a>'
                    
                    if desc == '':
                        desc = permalink                    
                    
                    ptitle = strip_tags(desc)[:75]
                    
                    feed.add_item(
                        title = ptitle,
                        link = permalink,
                        pubdate = dt, 
                        description = desc
                    )
                
                output = feed.writeString('UTF-8')
                memcache.add(p, output, 15 * 60)
                
                self.response.headers['Content-Type'] = 'application/atom+xml'
                self.response.out.write(output)

            
            else:
                self.error(404)
                self.response.out.write('<h1>404 Not Found</h1>')
        
        except Exception, err:
            self.error(500)
            self.response.out.write('<h1>500 Server Error</h1><p>' + str(err) + '</p>')

application = webapp.WSGIApplication([('/', MainPage), (r'/(.+)', FeedPage)],debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()