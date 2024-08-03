from backend.upgrade_resume import reformat_resume
import uuid
import os
from utils.basic_utils import binary_file_downloader_html, convert_docx_to_img, list_files
from css.streamlit_css import general_button
from streamlit_image_select import image_select
from streamlit_utils import progress_bar, set_streamlit_page_config_once, user_menu
from streamlit_float import *
from st_pages import get_pages, get_script_run_ctx 
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.add_vertical_space import add_vertical_space
from utils.cookie_manager import CookieManager
from multiprocessing import Pool
import streamlit as st

set_streamlit_page_config_once()
float_init()
STORAGE = os.environ["STORAGE"]
if STORAGE=="CLOUD":
    template_path = os.environ["S3_RESUME_TEMPLATE_PATH"]
elif STORAGE=="LOCAL":
    template_path = os.environ["RESUME_TEMPLATE_PATH"]

# pages = get_pages("")

class Reformat():

    ctx = get_script_run_ctx()
    
    def __init__(self, ):

        st.session_state["current_page"] = "template"
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
        if not self.userId:
            st.switch_page("pages/user.py")
        self._init_display()

    def _init_display(self, ):

        user_menu(self.userId, page="template")
        progress_bar(1)
        self.display_resume_templates()


    def display_resume_templates(self, ):
        
    
        template_paths = list_files(template_path, ext=".docx")
      
        with Pool() as pool:
            st.session_state["formatted_docx_paths"] = pool.map(reformat_resume, template_paths)
        with Pool() as pool:
            result  = pool.map(convert_docx_to_img, st.session_state["formatted_docx_paths"])
        st.session_state["image_paths"], st.session_state["formatted_pdf_paths"] = zip(*result)
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            previews = [images[0] for images in st.session_state["image_paths"] if images is not None]
            print(previews)
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
                                    background-color: #FF6347;
                                    color: white;
                                }"""
                    ):
                    if st.button("Choose this template", key="resume_template_button"):
                        st.session_state["selected_docx_resume"] = st.session_state["formatted_docx_paths"][selected_idx]
                        st.session_state["selected_pdf_resume"] = st.session_state["formatted_pdf_paths"][selected_idx]
                        st.switch_page("pages/downloads.py")
            float_parent()





if __name__ == '__main__':

    reformat=Reformat()
    
