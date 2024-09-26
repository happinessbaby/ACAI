# import extra_streamlit_components as stx
# import time
# import jwt
import os
import json
import streamlit as st
# from datetime import datetime, timedelta, date
# from streamlit_cookies_controller import CookieController
from utils.aws_manager import get_client
from streamlit_cookies_manager import EncryptedCookieManager
from streamlit_utils import set_streamlit_page_config_once
import streamlit as st
# from streamlit_js_eval import set_cookie, get_cookie
# from streamlit_js import st_js

set_streamlit_page_config_once()


from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file


cookie_name = os.environ["COOKIE_NAME"]
user_cookie_key=os.environ["USER_COOKIE_KEY"]
cookie_password = os.environ["COOKIE_PASSWORD"]
# controller = CookieController(key='cookies')
def init_cookies():
    # if "cookies" not in st.session_state:
    st.session_state["cookies"] = EncryptedCookieManager(
        # This prefix will get added to all your cookie names.
        # This way you can run your app on Streamlit Cloud without cookie name clashes with other apps.
        prefix=cookie_name,
        # You should really setup a long COOKIES_PASSWORD secret if you're running on Streamlit Cloud.
        password=cookie_password,
    )
    if not st.session_state.cookies.ready():
        # Wait for the component to load and send us current cookies.
        st.stop()
    # else:
    st.session_state["init_cookies"]=True

STORAGE = os.environ['STORAGE']

if STORAGE=="CLOUD":
    login_file = os.environ["S3_LOGIN_FILE_PATH"]
       # Download the JSON file from S3
    bucket_name = os.environ["BUCKET_NAME"]
    s3 = get_client('s3')
elif STORAGE=="LOCAL":
    login_file = os.environ["LOGIN_FILE_PATH"]

def retrieve_users() -> dict:
    # Save the dictionary as a JSON file
    if STORAGE=="LOCAL":
        with open(login_file, 'r') as file:
            users = json.load(file)
    elif STORAGE=="CLOUD":
        response = s3.get_object(Bucket=bucket_name, Key=login_file)
        json_data = response['Body'].read().decode('utf-8')
        # Convert the JSON string back to a dictionary
        users = json.loads(json_data)
    return users


USERS=retrieve_users()

# NOTE: wrapper class for extra_extreamlit_component's CookieManager
# class CookieManager():

#     def __init__(self,):

#         self.cookie=None
#         self.userId=None
#         self.cookie_manager = self.get_cookie_manager()
#         # self.cookies=self.cookie_manager.cookies


#     def get_cookie_manager(_self, ):

#         return stx.CookieManager(key="init_cookie_manager")


#     def encode_jwt(self, name, username, key, exp_date=1) -> str:
#         """
#         Encodes the contents of the reauthentication cookie.

#         Returns
#         -------
#         str
#             The JWT cookie for passwordless reauthentication.
#         """
#         return jwt.encode({'name':name,
#             'username':username,
#             'exp_date':exp_date}, key, algorithm='HS256')

#     def decode_jwt(self, token, key):

#         try:
#             decoded_token = jwt.decode(token, key, algorithms=['HS256'])
#             return decoded_token
#         except jwt.ExpiredSignatureError:
#             # Handle expired token
#             print("Token has expired.")
#             return None
#         except jwt.InvalidTokenError:
#             # Handle invalid token
#             print("Invalid token.")
#             return None


#     def get_cookie(self, name):

#         if not self.cookie:
#             return self.cookie_manager.get(cookie=name)
#         return self.cookie

#     def set_cookie(self, name, username, key="setCookie", path="/", expire_at=datetime.now()+timedelta(seconds=3600)):

#         #NOTE: streamlit-authenticator sets the cookie already, this is for google signin only
#         cookie_value = self.encode_jwt(name, username, cookie_key)
#         self.cookie_manager.set(cookie_name, cookie_value, key=key, path=path, expires_at=expire_at)
#         self.cookie = self.get_cookie(cookie_name)

#     def get_all_cookies(self, x=0):

#         return self.cookie_manager.get_all(key=f"get_all_cookie_{x}")

#     def delete_cookie(self, key="deleteCookie"):
        
    
#         if not self.cookies:
#             self.cookies = self.get_all_cookies(x="x")
#         if cookie_name in self.cookies:
#             self.cookie_manager.delete(cookie_name, key)
#             print("successfully deleted cookie")
#         self.userId = None
#         self.cookie=None
        

#     def retrieve_userId(self, max_retries=3, delay=1):

#         if not self.userId:
#             for attempt in range(max_retries):
#                 if not self.cookie:
#                     self.cookies = self.get_all_cookies(x=attempt)
#                     if cookie_name in self.cookies:
#                         self.cookie = self.get_cookie(cookie_name)
#                         print("retrieved user cookie")
#                     else:
#                         print(f"Attempt {attempt + 1}: user not logged in, retrying in {delay} seconds...")
#                         time.sleep(delay)
#             if self.cookie:
#                     self.userId = str(self.decode_jwt(self.cookie, cookie_key).get('username'))
#                     print("userId:", self.userId)
#         return self.userId
        


def add_user(username, password, first_name=None, last_name=None):
    try:
        user_dict={username:{}}
        user_dict[username].update({"username":username, "password":password})
        if first_name:
            user_dict[username].update({"first_name":first_name})
        if last_name:
            user_dict[username].update({"last_name":last_name})
        USERS.update(user_dict)
        if STORAGE=="LOCAL":
            with open(login_file, 'w') as file:
                json.dump(USERS, file, indent=4)
        elif STORAGE=="CLOUD":
            # Convert the dictionary to a JSON string
            json_data = json.dumps(USERS, indent=4)
            # Upload the JSON string to S3
            s3.put_object(Bucket=bucket_name, Key=login_file, Body=json_data)
        # controller.set(user_cookie_key,username, max_age=8*60*60)
        save_cookie(cookie_value=username, cookie_key=user_cookie_key)
        # set_cookie(user_cookie_key, username, 1)
        print(f"Successfully set cookie: {username}")
        return True
    except Exception as e:
        print(e)
        return False

def check_user():
    try:
        email=st.session_state.signup_email
        if email in USERS:
            print("email exists")
            st.session_state["signup_error_msg"]="email exists"
        if "@" not in email:
            print('email invalid')
            st.session_state["signup_error_msg"]="email invalid"   
    except Exception:
        pass
    try:
        password = st.session_state.signup_password
        if 0<len(password)<6:
            print("password length invalid")
            st.session_state["signup_error_msg"]= "password length"
    except Exception:
        pass
    try:
        email=st.session_state.recover_password_email
        if email not in USERS:
            print("email does not exists")
            st.session_state["recover_error_msg"]="email not exists"
        if "@" not in email:
            print('email invalid')
            st.session_state["recover_error_msg"]="email invalid"   
        else:
            user_password = USERS.get(email, {}).get('password', '')
            st.session_state["recover_password"]=user_password
    except Exception:
        pass

def change_password(username, new_password):

    try:
        USERS[username].update({"password":new_password})
        return True
    except Exception:
        return False

        

def save_cookie(cookie_value, cookie_key=user_cookie_key):

    st.session_state.cookies[cookie_key] = cookie_value
    st.session_state.cookies.save()

def save_cookies(cookie_dict):
    
    for key, value in cookie_dict.items():
        st.session_state.cookies[key]=value
    st.session_state.cookies.save()
    # for key, value in cookie_dict.items():
    #     controller.set(key, value, max_age=8*60*60)

def authenticate(username, password):

    user_info = USERS.get(username, {})
    
    if len(user_info):
        user_password = USERS.get(username, {}).get('password', '')
        if user_password == password:       
            # Save to cookie.
            # controller.set(user_cookie_key,username, max_age=8*60*60)
            save_cookie(cookie_value=username, cookie_key=user_cookie_key)
            # set_cookie(user_cookie_key, username, 1)
            # expiration = f"expires={1 * 24 * 60 * 60};"
            # st.markdown(
            #     f"""
            #     <script>
            #     document.cookie = "{user_cookie_key}={username}; {expiration} path=/";
            #     </script>
            #     """,
            #     unsafe_allow_html=True
            # )
            return username
        else:
            print("username password mistmatch")
            return None
        
def retrieve_cookie(cookie_key=user_cookie_key):
    # Check the contents of cookie.
    # cookies = controller.getAll()
    # time.sleep(1)
    # # Get cookie username and password if there is.
    # cookie_username = controller.get(f'{cookie_name}_username')
    if cookie_key in st.session_state.cookies.keys():
        cookie_username = st.session_state.cookies.get(cookie_key)
        if cookie_username:
            print("Successfully retrieved cookie")
            return cookie_username
        else:
            return None
    else:
        # ss.login_ok = False
        print("Failed to retrieve cookie")
        return None
    # try:
    #     cookie_username = st.context.cookies[cookie_key]
    #     print(f"retrieved cookie for user: {cookie_username}")
    #     return cookie_username
    # except Exception as e:
    #     print("failed to retriever cookie", e)
    #     return None
    
def delete_cookie(cookie_key=user_cookie_key):
    # controller.remove(cookie_key)
    # unset username in cookies
    st.session_state.cookies[cookie_key] = ""
    st.session_state.cookies.save()
    print("Successfully removed cookie")



