import streamlit as st
import time
from streamlit_modal import Modal
import os
import extra_streamlit_components as stx
# Note that you can also import these from streamlit directly
from st_pages import get_pages, get_script_run_ctx 
import streamlit_antd_components as sac


lance_users_table = os.environ["LANCE_USERS_TABLE"]



pages = get_pages("")
ctx = get_script_run_ctx()



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
                        st.switch_page("streamlit_main.py")
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


def progress_bar(page):
    #TODO create a custoprogress==1 and m one
    # progress = stx.stepper_bar(steps=["Step 1: Upgrade your profile", "Step 2: Pick a template", "Step 3: Download your resume"], lock_sequence=False)
    # if progress==1:
    #     if "current_page" in st.session_state and st.session_state.current_page!="streamlit_reformat":
    #         st.switch_page("pages/streamlit_reformat.py")
    # elif progress==0:
    #     if page=="profile":
    #         if "current_page" in st.session_state and st.session_state.current_page!="streamlit_user":
    #             st.switch_page("pages/streamlit_user.py")
    step = sac.steps(
        items=[
            sac.StepsItem(title="Step 1", subtitle="Update your profile"),
            sac.StepsItem(title="Step 2", subtitle="Pick a template"), 
            sac.StepsItem(title="Step 3", subtitle="Download your resume")
        ], index = page,  color="#FF6347"
    )
    if step=="Step 1":
        if "current_page" in st.session_state and st.session_state.current_page!="profile":
            # st.session_state["current_page"]="profile"
            st.switch_page("pages/streamlit_user.py")
    elif step=="Step 2":
        if "current_page" in st.session_state and st.session_state.current_page!="template":
            # st.session_state["current_page"] = "template"
            st.switch_page("pages/streamlit_reformat.py")

    
