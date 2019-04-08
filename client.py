"""
Clients for interacting with different league providers' APIs
"""

import datetime
import json
import os

from lxml import etree
import pandas
import requests
from requests_oauthlib import OAuth2Session


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


class EspnClient(object):
    """
    Client that sets up cookies for authentication.
    """
    def __init__(self, league_directory):
        with open(os.path.join(league_directory, "cookie.txt"), 'r') as f:
            cookie_string = f.read()
        
        cookie = {}

        for x in cookie_string.split(';'):
            k, v = x.strip().split('=')
            cookie[k] = v
        
        self.session = requests.Session()
        # session.cookies = requests.cookies.cookiejar_from_dict(cookie_dict)
        self.session.headers.update({'Cookie': cookie_string})


class YahooClient(object):
    """
    Client that sets up OAuth to get an authorized session.

    Uses the requests_oauthlib library
    """
    token_url = 'https://api.login.yahoo.com/oauth2/get_token'

    def __init__(self, client_id, client_secret, league_directory):
        self.league_directory = league_directory
        self.client_id = client_id
        self.client_secret = client_secret

        self.token_location = os.path.join(
            self.league_directory,
            "yahoo_token.json"
        )

        self.load_token()

        self.session = OAuth2Session(
            client_id=self.client_id,
            token=self.token,
            redirect_uri='oob',
        )
        
        self.refresh_token()
    
    def load_token(self):
        with open(self.token_location, 'r') as f:
            self.token = json.load(f)
    
    def refresh_token(self):
        self.token = self.session.refresh_token(
            self.token_url,
            client_id=self.client_id,
            client_secret=self.client_secret
        )

        with open(self.token_location, 'w') as f:
            json.dump(self.token, f)