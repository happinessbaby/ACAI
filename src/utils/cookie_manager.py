import extra_streamlit_components as stx
import streamlit as st
import time
import jwt

@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager(key="init_cookie_manager")

cookie_manager = get_cookie_manager()

def encode_jwt(name, username, key, exp_date=1) -> str:
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

def decode_jwt(token, key):
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


def get_cookie(name):
    return cookie_manager.get(cookie=name)

def set_cookie(cookie, value, key, path, expire_at):
    cookie_manager.set(cookie, value, key=key, path=path, expires_at=expire_at)
    
def get_all_cookies():
    return cookie_manager.get_all()

def delete_cookie(name, key):
    cookie_manager.delete(name, key)
    