import extra_streamlit_components as stx
import time
import jwt
import os
import time
from datetime import datetime, timedelta, date


from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file


cookie_name = os.environ["COOKIE_NAME"]
cookie_key=os.environ["COOKIE_KEY"]

# NOTE: wrapper class for extra_extreamlit_component's CookieManager
class CookieManager():

    def __init__(self,):

        self.cookie=None
        self.userId=None
        self.cookie_manager = self.get_cookie_manager()
        # self.cookies=self.cookie_manager.cookies

    # @st.cache_resource(experimental_allow_widgets=True)
    def get_cookie_manager(_self, ):

        return stx.CookieManager(key="init_cookie_manager")


    def encode_jwt(self, name, username, key, exp_date=1) -> str:
        """
        Encodes the contents of the reauthentication cookie.

        Returns
        -------
        str
            The JWT cookie for passwordless reauthentication.
        """
        return jwt.encode({'name':name,
            'username':username,
            'exp_date':exp_date}, key, algorithm='HS256')

    def decode_jwt(self, token, key):

        try:
            decoded_token = jwt.decode(token, key, algorithms=['HS256'])
            return decoded_token
        except jwt.ExpiredSignatureError:
            # Handle expired token
            print("Token has expired.")
            return None
        except jwt.InvalidTokenError:
            # Handle invalid token
            print("Invalid token.")
            return None


    def get_cookie(self, name):

        if not self.cookie:
            return self.cookie_manager.get(cookie=name)
        return self.cookie

    def set_cookie(self, name, username, key="setCookie", path="/", expire_at=datetime.now()+timedelta(seconds=3600)):

        #NOTE: streamlit-authenticator sets the cookie already, this is for google signin only
        cookie_value = self.encode_jwt(name, username, cookie_key)
        self.cookie_manager.set(cookie_name, cookie_value, key=key, path=path, expires_at=expire_at)
        self.cookie = self.get_cookie(cookie_name)

    def get_all_cookies(self, x=0):

        return self.cookie_manager.get_all(key=f"get_all_cookie_{x}")

    def delete_cookie(self, key="deleteCookie"):
        
        if not self.cookies:
            self.cookies = self.get_all_cookies(x="x")
        if cookie_name in self.cookies:
            self.cookie_manager.delete(cookie_name, key)
        self.userId = None
        self.cookie=None
        

    def retrieve_userId(self, max_retries=3, delay=1):

        if not self.userId:
            for attempt in range(max_retries):
                if not self.cookie:
                    self.cookies = self.get_all_cookies(x=attempt)
                    if cookie_name in self.cookies:
                        self.cookie = self.get_cookie(cookie_name)
                    else:
                        print(f"Attempt {attempt + 1}: user not logged in, retrying in {delay} seconds...")
                        time.sleep(delay)
            if self.cookie:
                    self.userId = str(self.decode_jwt(self.cookie, cookie_key).get('username'))
                    print("userId:", self.userId)
        return self.userId
        
