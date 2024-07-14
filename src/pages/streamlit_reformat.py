from backend.upgrade_resume import reformat_resume
import uuid
import streamlit as st
import os
from utils.basic_utils import binary_file_downloader_html, convert_docx_to_img
from css.streamlit_css import general_button
from streamlit_image_select import image_select
from backend.upgrade_resume import tailor_resume
from pages.streamlit_utils import progress_bar, set_streamlit_page_config_once, user_menu
from streamlit_float import *
from st_pages import get_pages, get_script_run_ctx 
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.add_vertical_space import add_vertical_space
from utils.cookie_manager import CookieManager


pages = get_pages("")

class Reformat():

    ctx = get_script_run_ctx()
    set_streamlit_page_config_once()
    
    def __init__(self, ):

        st.session_state["current_page"] = "template"
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
        if not self.userId:
            st.switch_page("pages/streamlit_user.py")
        self._init_display()

    def _init_display(self, ):

        user_menu(self.userId, page="template")
        progress_bar(1)
        self.display_resume_templates()


    def display_resume_templates(self, ):
        
        paths = ["./backend/resume_templates/functional/functional0.docx","./backend/resume_templates/functional/functional1.docx","./backend/resume_templates/chronological/chronological0.docx", "./backend/resume_templates/chronological/chronological1.docx"]
        # if "image_paths" not in st.session_state:
        st.session_state["formatted_docx_paths"] = []
        st.session_state["formatted_pdf_paths"] = []
        st.session_state["image_paths"] = []
        for idx, path in enumerate(paths):
            filename = str(uuid.uuid4())
            output_dir = st.session_state["users_download_path"]
            docx_path = os.path.join(output_dir, filename+".docx")
            reformat_resume(path, st.session_state["profile"], docx_path)
            st.session_state["formatted_docx_paths"].append(docx_path)
            img_paths, pdf_path = convert_docx_to_img(docx_path, output_dir, idx)
            st.session_state["formatted_pdf_paths"].append(pdf_path)
            st.session_state["image_paths"].append(img_paths)
            
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            previews = [paths[0] for paths in st.session_state["image_paths"]]
            selected_idx=image_select("Select a template", images=previews, return_value="index")
            st.markdown(general_button, unsafe_allow_html=True)    
            # st.markdown(binary_file_downloader_html(formatted_pdf_paths[selected_idx], "Download as PDF"), unsafe_allow_html=True)
            # st.markdown(binary_file_downloader_html(formatted_docx_paths[selected_idx], "Download as DOCX"), unsafe_allow_html=True)
        with c2:
            st.image(st.session_state["image_paths"][selected_idx])
        with c3:
            float_container=st.container()
            with float_container:
                add_vertical_space(30)
                with stylable_container(
                    key="custom_template_container",
                        css_styles=  
                    """   button {
                                    background-color: #4682B4;
                                    color: white;
                                }"""
                    ):
                    if st.button("Chose this template", key="resume_template_button"):
                        st.session_state["selected_docx_resume"] = st.session_state["formatted_docx_paths"][selected_idx]
                        st.session_state["selected_pdf_resume"] = st.session_state["formatted_pdf_paths"][selected_idx]
                        print("user picked template")
                        st.switch_page("pages/streamlit_download.py")
            float_parent()





if __name__ == '__main__':

    reformat=Reformat()
    

