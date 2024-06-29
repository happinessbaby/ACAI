import streamlit as st
import time
from streamlit_modal import Modal
from utils.lancedb_utils import retrieve_lancedb_table
import os


lance_users_table = os.environ["LANCE_USERS_TABLE"]

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

def retrieve_user_profile_dict(userId):
    users_table = retrieve_lancedb_table(lance_users_table)
    try:
        table=users_table.search().where(f"user_id = '{userId}'", prefilter=True).to_pandas().to_dict("list")
        print("Retrieved user profile dict from lancedb")
    except Exception as e:
        print(e)
        table=None
    return table