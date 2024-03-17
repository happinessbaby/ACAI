import streamlit as st

def loading(container):
    with container:
        while True:
            st.spinner(text="please wait...")