import streamlit as st
from utils.basic_utils import binary_file_downloader_html
import streamlit_antd_components as sac
import json
from utils.cookie_manager import CookieManager
from pages.streamlit_utils import nav_to, user_menu, progress_bar, set_streamlit_page_config_once

set_streamlit_page_config_once()
class Download():

    def __init__(self):
        st.session_state["current_page"] = "download"
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
        self.display_downloads()

    def display_downloads(self, ):
        progress_bar(2)
        _, download_col, _=st.columns([1, 1, 1])
        with download_col:
            if "selected_docx_resume" in st.session_state:
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.markdown(binary_file_downloader_html(st.session_state["selected_docx_resume"], "Download as DOCX"), unsafe_allow_html=True)
                with c2:
                    st.markdown(binary_file_downloader_html(st.session_state["selected_pdf_resume"], "Download as PDF"), unsafe_allow_html=True)
                self.leave_feedback()
            else:
                st.write("Please go back and select a resume template")


    def leave_feedback(self, ):
        with st.container(border=True):
            st.write("How did you like it?")
            helpfulness = sac.rate(label='helpfulness', color="yellow", align='center', )
            use= sac.rate(label='ease of use', color="yellow",align='center',)
            speed = sac.rate(label='speed', color="yellow",align='center')
            suggestion = st.text_area("suggestion", )
            st.button("submit", on_click=self.save_feedback, args = (helpfulness, use, speed, suggestion, ))

    def save_feedback(self, helpfulness, use, speed, suggestion,):
        if self.userId:
            feedback = {self.userId:{"helpfulness":helpfulness, "ease of use":use, "speed":speed, "suggestion":suggestion}}
            with open("user_feedback.json", "w") as f:
                json.dump(feedback, f)

        



          

if __name__ == '__main__':

    download=Download()
    