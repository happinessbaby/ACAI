import extra_streamlit_components as stx
import streamlit as st
import time

@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()

def get_cookie(name):
    cookie_manager = get_manager()
    time.sleep(2)
    return cookie_manager.get(cookie=name)

def set_cookie(cookie, value, key, path, expire_at):
    cookie_manager = get_manager()
    cookie_manager.set(cookie, value, key=key, path=path, expires_at=expire_at)
    
def get_all_cookies():
    cookie_manager = get_manager()
    return cookie_manager.get_all()

def delete_cookie(name, key):
    cookie_manager = get_manager()
    cookie_manager.delete(name, key)
    