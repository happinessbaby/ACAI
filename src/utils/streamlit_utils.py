import streamlit as st
import time
from streamlit_modal import Modal

@st.experimental_dialog(" ", )
def loading(text, container=st.empty(), interval=5):
    with container.container():
        with st.spinner(text):
            time.sleep(interval)

def nav_to(url):
    nav_script = """
        <meta http-equiv="refresh" content="0; url='%s'">
    """ % (url)
    st.write(nav_script, unsafe_allow_html=True)
