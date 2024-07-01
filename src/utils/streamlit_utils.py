import streamlit as st
import time
from streamlit_modal import Modal
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

def user_menu(userId, page, ):
    _, c1 = st.columns([10, 1])
    with c1:
        if not userId:
            if st.button("Log in", key="profile_button", type="primary"):
                st.session_state["user_mode"] = "signedout"
                st.switch_page("pages/streamlit_user.py")
        else:
            with st.popover(label="👤",):
                if page!="main":
                    if st.button("Home", type="primary"):
                        nav_to("http://localhost:8501/")
                if page!="profile":
                    if st.button("My profile", type="primary"):
                        st.session_state["user_mode"]="display_profile"
                        st.switch_page("pages/streamlit_user.py")
                st.divider()
                if st.button("Log out", type="primary"):
                    st.session_state["user_mode"]="signout"
                    st.switch_page("pages/streamlit_user.py")
                # if page=="profile":
                #     if st.button("Delete my profile", type="primary"):
                #         st.session_state["user_mode"] = "delete_profile"
                #         st.switch_page("pages/streamlit_user.py")

def site_logo():
    """"""