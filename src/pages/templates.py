from backend.upgrade_resume import reformat_resume
import uuid
import os
from utils.basic_utils import binary_file_downloader_html, convert_docx_to_img, list_files, mk_dirs, convert_doc_to_pdf
from css.streamlit_css import general_button
# from streamlit_image_select import image_select
from streamlit_utils import progress_bar, set_streamlit_page_config_once, user_menu
from streamlit_float import *
from st_pages import get_pages, get_script_run_ctx 
from streamlit_extras.add_vertical_space import add_vertical_space
from utils.cookie_manager import CookieManager
from multiprocessing import Pool
from datetime import datetime
import streamlit_antd_components as sac
from utils.lancedb_utils import retrieve_dict_from_table
from streamlit_pdf_viewer import pdf_viewer
import streamlit as st

set_streamlit_page_config_once()
float_init()
STORAGE = os.environ["STORAGE"]
if STORAGE=="CLOUD":
    template_path = os.environ["S3_RESUME_TEMPLATE_PATH"]
elif STORAGE=="LOCAL":
    template_path = os.environ["RESUME_TEMPLATE_PATH"]
lance_users_table = os.environ["LANCE_USERS_TABLE"]
# pages = get_pages("")
# NOTE: TESTING OUT OPTION 2 FOR NOW 
option = 2

class Reformat():

    ctx = get_script_run_ctx()
    
    def __init__(self, ):

        st.session_state["current_page"] = "template"
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
        if not self.userId:
            st.switch_page("pages/user.py")
        else:
            if "profile" not in st.session_state:
                st.session_state["profile"]= retrieve_dict_from_table(self.userId, lance_users_table)
        self._init_session_states()
        self._init_display()

    def _init_session_states(_self, ):

        if "selected_fields" not in st.session_state:
            st.session_state["selected_fields"]=["Contact", "Education", "Summary Objective", "Work Experience"]
        if "user_save_path" not in st.session_state:
            if STORAGE=="CLOUD":
                st.session_state["user_save_path"] = os.path.join(os.environ["S3_USER_PATH"], _self.userId, "profile")
            elif STORAGE=="LOCAL":
                st.session_state["user_save_path"] = os.path.join(os.environ["USER_PATH"], _self.userId, "profile")
            # Get the current time
            now = datetime.now()
            # Format the time as "year-month-day-hour-second"
            formatted_time = now.strftime("%Y-%m-%d-%H-%M")
            st.session_state["users_upload_path"] = os.path.join(st.session_state.user_save_path, "uploads", formatted_time)
            st.session_state["users_download_path"] =  os.path.join(st.session_state.user_save_path, "downloads", formatted_time)
            paths=[st.session_state["users_download_path"]]
            mk_dirs(paths,)


    def _init_display(self, ):

        st.markdown(general_button, unsafe_allow_html=True)   
        user_menu(self.userId, page="template")
        progress_bar(1)
        add_vertical_space(8)
        if  ("formatted_docx_paths" not in st.session_state) or ("profile_changed" in st.session_state and st.session_state["profile_changed"]) or ("fields_changed" in st.session_state and st.session_state["fields_changed"]):
            print(st.session_state["selected_fields"])
            if self.reformat_templates():
                self.display_resume_templates()
            st.session_state["profile_changed"]=False
            st.session_state["fields_changed"]=False
        else:
            self.display_resume_templates()
            st.session_state["profile_changed"]=False
            st.session_state["fields_changed"]=False


    def reformat_templates(self, ):

        try:
            template_paths = list_files(template_path, ext=".docx")
            print(template_paths)
            with Pool() as pool:
                st.session_state["formatted_docx_paths"] = pool.map(reformat_resume, template_paths)
            # if option==1:
            #     with Pool() as pool:
            #         result  = pool.map(convert_docx_to_img, st.session_state["formatted_docx_paths"])
            #     st.session_state["image_paths"], st.session_state["formatted_pdf_paths"] = zip(*result)
            if option==2:
                with Pool() as pool:
                    st.session_state["formatted_pdf_paths"] = pool.map(convert_doc_to_pdf, st.session_state["formatted_docx_paths"])
            return True
        except Exception as e:
            print(e)
            return False


    @st.fragment()
    def display_resume_templates(self, ):
        
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            self.fields_selection()  
        # if option==1: 
        #     with c2:
        #         previews = [images[0] for images in st.session_state["image_paths"] if images]
        #         print(previews)
        #         selected_idx=image_select("Select a template", images=previews, return_value="index")
        #         st.image(st.session_state["image_paths"][selected_idx])
        if option==2:
            with c2:
                c1, c2, c3 = st.columns([1, 20, 1])
                previews = [pdf for pdf in st.session_state["formatted_pdf_paths"] if pdf]
                st.session_state["previews_len"] = len(previews)
                print(previews)
                if "selected_idx" not in st.session_state:
                    st.session_state["selected_idx"]=0
                with c1:
                    add_vertical_space(30)
                    prev = st.button("🞀", key="prev_template_button", on_click=self.callback, args=("previous", ))
                    # if prev:
                    #     if st.session_state["selected_idx"]!=0:
                    #         st.session_state["selected_idx"]-=1
                    #         st.rerun()
                with c2:
                    pdf_viewer(previews[st.session_state.selected_idx])
                    st.session_state["selected_docx_resume"] = st.session_state["formatted_docx_paths"][st.session_state.selected_idx]
                    st.session_state["selected_pdf_resume"] = st.session_state["formatted_pdf_paths"][st.session_state.selected_idx]
                with c3:
                    add_vertical_space(30)
                    nxt = st.button("🞂", key="next_template_button", on_click=self.callback, args=("next", ))
                    # if nxt:
                    #     if st.session_state["selected_idx"]!=len(previews)-1:
                    #         st.session_state["selected_idx"]+=1
                            # st.rerun()

           # with c3:
        #     float_container=st.container()
        #     with float_container:
        #         add_vertical_space(30)
        #         with stylable_container(
        #             key="custom_button1_template",
        #                 css_styles=  
        #             """   button {
        #                             background-color: #ff8247;
        #                             color: white;
        #                         }"""
        #             ):
        #             if st.button("Use this template", key="resume_template_button"):
        #                 st.session_state["selected_docx_resume"] = st.session_state["formatted_docx_paths"][selected_idx]
        #                 st.session_state["selected_pdf_resume"] = st.session_state["formatted_pdf_paths"][selected_idx]
        #                 st.switch_page("pages/downloads.py")
        #     float_parent()

    def callback(self, direction, ):
        if direction=="next":
            if st.session_state["selected_idx"]!=st.session_state["previews_len"]-1:
                        st.session_state["selected_idx"]+=1
        elif direction=="previous":
            if st.session_state["selected_idx"]!=0:
                            st.session_state["selected_idx"]-=1


    @st.fragment()
    def fields_selection(self, ):

        st.write("Fields to include in the resume")
        if "selected_fields" in st.session_state:
            index_selected = [idx for idx, val in enumerate(st.session_state["selected_fields"])]
        else:
            index_selected = [0, 1, 2, 3]
        selected_fields = sac.chip(items=[
                sac.ChipItem(label='Contact'),
                sac.ChipItem(label='Education'),
                sac.ChipItem(label='Summary Objective'),
                sac.ChipItem(label='Work Experience'),
                sac.ChipItem(label='Skills'),
                sac.ChipItem(label='Professional Accomplishment'),
                sac.ChipItem(label='Projects'),
                sac.ChipItem(label='Certifications'),
                sac.ChipItem(label='Awards & Honors'),
            ], label=' ', index=index_selected, align='center', radius='md', multiple=True , variant="light", color="#47ff5a")
        if selected_fields!=st.session_state["selected_fields"]:
            st.session_state["fields_changed"]=True
            st.session_state["selected_fields"]=selected_fields
            st.rerun()



if __name__ == '__main__':

    reformat=Reformat()
    

