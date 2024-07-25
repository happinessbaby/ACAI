from utils.basic_utils import binary_file_downloader_html
import streamlit_antd_components as sac
import json
from utils.cookie_manager import CookieManager
from streamlit_utils import nav_to, user_menu, progress_bar, set_streamlit_page_config_once
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.buy_me_a_coffee import button
import boto3
import os
import s3fs
import streamlit as st

set_streamlit_page_config_once()

STORAGE = os.environ["STORAGE"]
if STORAGE=="S3":
    bucket_name = os.environ["BUCKET_NAME"]
    s3_save_path = os.environ["S3_CHAT_PATH"]
    session = boto3.Session(         
                    aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"],
                    aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"],
                )
    s3 = session.client('s3')
else:
    bucket_name=None
    s3=None

class Download():


    def __init__(self):
        
        st.session_state["current_page"] = "download"
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
        if not self.userId:
            st.switch_page("pages/streamlit_user.py")
        self._init_display()

    def _init_display(self, ):

        user_menu(self.userId, page="download")
        progress_bar(2)
        add_vertical_space(10)
        self.display_downloads()
        add_vertical_space(5)
        if "feedback" not in st.session_state:       
            self.leave_feedback()
        button(username="Tebbles", floating=False, width=221)
       

    def display_downloads(self, ):

        _, download_col, _=st.columns([1, 1, 1])
        with download_col:
            if "selected_docx_resume" in st.session_state:
                c1, c2 = st.columns([1, 1])
                with c1:
                    with stylable_container(
                        key="custom_download_container",
                            css_styles="""{
                                    border: 3px solid rgba(49, 51, 63, 0.2);
                                    border-radius: 0.5rem;
                                    padding: calc(1em - 1px)
                                }
                        """
                    ):
                        if STORAGE=="LOCAL":
                            with open(st.session_state["selected_docx_resume"], "rb") as f:
                                st.download_button("Download as DOCX", f, st.session_state["selected_docx_resume"])
                            # st.markdown(binary_file_downloader_html(st.session_state["selected_docx_resume"], "Download as DOCX"), unsafe_allow_html=True)
                        elif STORAGE=="CLOUD":
                            s3 = s3fs.S3FileSystem(anon=True)
                            docx_file = os.path.join(bucket_name,st.session_state["selected_docx_resume"])
                            with s3.open(docx_file, 'rb') as f:
                                st.download_button("Download as DOCX", f, docx_file)
                with c2:
                    with stylable_container(
                        key="custom_download_container",
                        css_styles="""{
                                    border: 3px solid rgba(49, 51, 63, 0.2);
                                    border-radius: 0.5rem;
                                    padding: calc(1em - 1px)
                                }
                        """
                    ):
                        if STORAGE=="LOCAL":
                            # st.markdown(binary_file_downloader_html(st.session_state["selected_pdf_resume"], "Download as PDF"), unsafe_allow_html=True)
                            with open(st.session_state["selected_pdf_resume"], "rb") as f:
                                st.download_button("Download as PDF", f, st.session_state["selected_pdf_resume"],)
                        elif STORAGE=="CLOUD":
                            s3 = s3fs.S3FileSystem(anon=True)
                            pdf_file = os.path.join(bucket_name,st.session_state["selected_pdf_resume"])
                            with s3.open('my-bucket/my-file.txt', 'rb') as f:
                                st.download_button("Download as PDF", f, pdf_file)

            else:
                sac.result(label='Please go back and select a template', )


    def leave_feedback(self, ):
        _, c, _ = st.columns([2, 1, 2])
        with c:
            with st.container(border=True):
                st.write("Would you like to give a feedback?")
                helpfulness = sac.rate(label='helpfulness', color="yellow", )
                use= sac.rate(label='ease of use', color="yellow",)
                speed = sac.rate(label='speed', color="yellow",)
                suggestion = st.text_area("suggestion", )
                st.button("submit", on_click=self.save_feedback, args = (helpfulness, use, speed, suggestion, ))

    def save_feedback(self, helpfulness, use, speed, suggestion,):
        st.session_state["feedback"]=True
        if self.userId:
            feedback = {self.userId:{"helpfulness":helpfulness, "ease of use":use, "speed":speed, "suggestion":suggestion}}
            with open("user_feedback.json", "w") as f:
                json.dump(feedback, f)

        

        



          

if __name__ == '__main__':

    download=Download()
    