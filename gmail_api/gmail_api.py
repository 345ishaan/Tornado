import httplib2
import json
import datetime
import dateutil.relativedelta
import os
import operator
import tornado.options
import apiclient.discovery
import oauth2client.client
import oauth2client.file
import oauth2client.tools
import tornado.web
import tornado.websocket
from html import HTML
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, url, HTTPError
from tornado.ioloop import IOLoop
from settings import*
from tornado.template import Loader
from tornado import gen

CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), 'client_secret.json')
OAUTH_STORAGE_FILE = os.path.join(os.path.dirname(__file__), 'oauth2.json')

GMAIL_READ_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'
GMAIL_API_SERVICE_NAME = 'gmail'
GMAIL_API_VERSION = 'v1'
api = None
Bcc_str=None
Cc_str=None
To_str=None
contacts = {} 
n = datetime.date.today()
s = n + dateutil.relativedelta.relativedelta(days=-3)
now=str(n).replace('-','/')
start=str(s).replace('-','/')
query = "after"+":"+start+" "+"before"+":"+now
class App(Application):
    def __init__(self):
        handlers = [
             url(r'/',MainHandler),
             url(r'/conversations_sort', SortHandler)

            ]
        settings = application_handler_setttings
        Application.__init__(self, handlers, **settings)
		
		
class SortHandler(RequestHandler):
    @gen.coroutine
    def get(self):
        messages = []
        global contacts  
        message_list = self.settings['api_s'].users().messages().list(userId='me',labelIds='SENT',q=query).execute()
        flag = False
        if 'messages' in message_list:
            messages = message_list['messages']
            response = yield self.check_values(messages)
        
        while (('nextPageToken' in message_list)):
            page_token = message_list['nextPageToken']
            message_list = yield self.settings['api_s'].users().messages().list(userId='me',labelIds='SENT',pageToken=page_token,q=query).execute()
            if 'messages' in message_list:
                messages = message_list['messages']
                response = yield self.check_values(messages)
        
        self.render_html()              
    
    def check_values(self,messages):
        global contacts
        for i in range(0,len(messages)):
            message_obj = messages[i]
            headers = self.settings['api_s'].users().messages().get(userId='me',id=message_obj['id'],format='metadata',metadataHeaders=['To','Bcc','Cc'],fields='payload').execute()['payload']['headers']
            for ii in range(0,len(headers)):
                if (headers[ii]['name'] == 'Bcc') :
                   Bcc_str = headers[ii]['value']
                   if(contacts.has_key(Bcc_str)) :
                       contacts[Bcc_str]+=1;
                   else:
                       contacts[Bcc_str] = 1;
                if (headers[ii]['name'] == 'Cc') :
                   Cc_str = headers[ii]['value']
                   if(contacts.has_key(Cc_str)) :
                       contacts[Cc_str]+=1;
                   else:
                       contacts[Cc_str] = 1;
                if (headers[ii]['name'] == 'To') :
                   To_str = headers[ii]['value']
                   if(contacts.has_key(To_str)) :
                       contacts[To_str]+=1;
                   else:
                       contacts[To_str] = 1;
        return {}
				   
    def render_html(self):
        global contacts
        contacts_sort = sorted(contacts.items(), key=operator.itemgetter(1))
        loader = Loader(os.path.join('templates'))
        self.finish( loader.load("contacts.html").generate(contacts_list=contacts_sort))
class MainHandler(RequestHandler):
    #@tornado.web.authenticated
    def get(self):
        flow = oauth2client.client.flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope = GMAIL_READ_SCOPE)

        storage = oauth2client.file.Storage(OAUTH_STORAGE_FILE)
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            credentials = oauth2client.tools.run_flow(flow, storage, oauth2client.tools.argparser.parse_args())
        api = apiclient.discovery.build(GMAIL_API_SERVICE_NAME, GMAIL_API_VERSION, http = credentials.authorize(httplib2.Http()))
        self.settings['api_s']=api
        self.redirect('/conversations_sort')

def main():
    tornado.options.parse_command_line()
    http_server = HTTPServer(App())
    http_server.listen(8080)
    IOLoop.instance().start()
if __name__ == "__main__":
    main()
		
