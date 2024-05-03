import streamlit as st
import time

def loading(container=st.empty(), text="Please wait"):
    with container:
        with st.spinner(text=text):
            time.sleep(1)


def interview_loading(container=st.empty()):
    with container:
        while True:
            #Temporary 
            st.text("Please fill out the form on the sidebar. The more you provide the more personalized your session will be. ")
            time.sleep(5)
            st.text("If AI cannot hear you, please check if your mic is turned on and check the sound volume. ")
            time.sleep(5)
            st.text("Do not refresh the page or your interview session will restart")
            time.sleep(5)

