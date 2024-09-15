from backend.upgrade_resume import reformat_resume
import uuid
import os
from utils.basic_utils import binary_file_downloader_html, convert_docx_to_img, list_files, mk_dirs, convert_doc_to_pdf
from css.streamlit_css import general_button, primary_button
# from streamlit_image_select import image_select
from streamlit_utils import progress_bar, set_streamlit_page_config_once, user_menu
from streamlit_float import *
from st_pages import get_script_run_ctx 
from streamlit_extras.add_vertical_space import add_vertical_space
from utils.cookie_manager import retrieve_cookie
from multiprocessing import Pool
from datetime import datetime
from pathlib import Path
import streamlit_antd_components as sac
from utils.lancedb_utils import retrieve_dict_from_table
from streamlit_pdf_viewer import pdf_viewer
from streamlit_extras.stylable_container import stylable_container
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
float_init()
option=2
menu_placeholder=st.empty()
progressbar_placeholder=st.empty()
template_placeholder = st.empty()
_, c, _= st.columns([3, 1, 3])
with c:
    add_vertical_space(20)
    spinner_placeholder=st.empty()
# st.logo("./resources/logo_acareerai.png")

class Reformat():

    ctx = get_script_run_ctx()
    
    def __init__(self, ):

        # st.session_state["current_page"] = "template"
        # if "cm" not in st.session_state:
        #     st.session_state["cm"] = CookieManager()
        # st.session_state.userId = st.session_state.cm.retrieve_userId()
        # if not st.session_state.userId:
        #     st.switch_page("pages/user.py")      
        self._init_session_states()
        self._init_display()

    def _init_session_states(_self, ):

        st.session_state["current_page"] = "template"
        # if "cm" not in st.session_state:
        #     st.session_state["cm"] = CookieManager()
        # if "userId" not in st.session_state:
        if "userId" not in st.session_state:
            st.session_state["userId"] = retrieve_cookie()
            if not st.session_state["userId"]:
                st.switch_page("pages/user.py")
        if "profile" not in st.session_state:
                st.session_state["profile"]= retrieve_dict_from_table(st.session_state.userId, lance_users_table)
        if "selected_fields" not in st.session_state:
            st.session_state["selected_fields"]=["Contact", "Education", "Summary Objective", "Work Experience"]
        if "user_save_path" not in st.session_state:
            if STORAGE=="CLOUD":
                st.session_state["user_save_path"] = os.path.join(os.environ["S3_USER_PATH"], st.session_state.userId, "profile")
            elif STORAGE=="LOCAL":
                st.session_state["user_save_path"] = os.path.join(os.environ["USER_PATH"], st.session_state.userId, "profile")
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
        st.markdown(primary_button, unsafe_allow_html=True )
        with menu_placeholder.container():
            user_menu(st.session_state.userId, page="template")
        with progressbar_placeholder.container():
            progress_bar(1)
        if  ("formatted_docx_paths" not in st.session_state or "formatted_pdf_paths" not in st.session_state) or ("fields_changed" in st.session_state and st.session_state["fields_changed"]) or ("update_template" in st.session_state and st.session_state["update_template"]):
            if self.reformat_templates():
                with template_placeholder.container():
                    # print(st.session_state["selected_fields"])
                    self.display_resume_templates()
                    st.session_state["update_template"]=False
                    st.session_state["fields_changed"]=False
            else:
                st.rerun()
        else:
            with template_placeholder.container():
                self.display_resume_templates()
                st.session_state["update_template"]=False
                st.session_state["fields_changed"]=False


    def reformat_templates(self, ):

        try:
            template_paths = list_files(template_path, ext=".docx")
            # print(template_paths)
            with spinner_placeholder.container():
                with st.spinner("Updating templates..."):
                    with Pool() as pool:
                        st.session_state["formatted_docx_paths"] = pool.map(reformat_resume, template_paths)
                    if st.session_state["formatted_docx_paths"]:
                        # if option==1:
                        #     with Pool() as pool:
                        #         result  = pool.map(convert_docx_to_img, st.session_state["formatted_docx_paths"])
                        #     st.session_state["image_paths"], st.session_state["formatted_pdf_paths"] = zip(*result)
                        if option==2:
                            with Pool() as pool:
                                st.session_state["formatted_pdf_paths"] = pool.map(convert_doc_to_pdf, st.session_state["formatted_docx_paths"])
            spinner_placeholder.empty()
            return True
        except Exception as e:
            print(e)
            return False


    @st.fragment()
    def display_resume_templates(self, ):
        
        add_vertical_space(8)
        c1, template_col, select_col = st.columns([1, 3, 1])
        with c1:
            self.fields_selection()  
        # if option==1: 
        #     with c2:s
        #         previews = [images[0] for images in st.session_state["image_paths"] if images]
        #         print(previews)
        #         selected_idx=image_select("Select a template", images=previews, return_value="index")
        #         st.image(st.session_state["image_paths"][selected_idx])
        if option==2:
            with template_col:
                c1, c2, c3 = st.columns([1, 20, 1])
                previews = [pdf for pdf in st.session_state["formatted_pdf_paths"] if pdf]
                st.session_state["previews_len"] = len(previews)
                print(previews)
                if "selected_idx" not in st.session_state:
                    st.session_state["selected_idx"]=0
                with c1:
                    add_vertical_space(30)
                    prev = st.button("🞀", key="prev_template_button", on_click=self.callback, args=("previous", ))
                with c2:
                    with stylable_container(
                        key="container_with_border",
                        css_styles="""
                            {
                                border: 1px solid red;
                                border-radius: 0.5rem;
                                padding: calc(1em - 1px)
                            }
                            """,
                    ):
                        pdf_viewer(previews[st.session_state.selected_idx])
                        st.session_state["selected_docx_resume"] = st.session_state["formatted_docx_paths"][st.session_state.selected_idx]
                        st.session_state["selected_pdf_resume"] = st.session_state["formatted_pdf_paths"][st.session_state.selected_idx]
                with c3:
                    add_vertical_space(30)
                    nxt = st.button("🞂", key="next_template_button", on_click=self.callback, args=("next", ))
                    if nxt:
                        if st.session_state["selected_idx"]!=len(previews)-1:
                            st.session_state["selected_idx"]+=1
                            st.rerun()

            with select_col:
                _, c = st.columns([0.5, 1])
                with c:
                    float_container=st.container()
                    with float_container:
                        # add_vertical_space(10)
                        if st.button(label="Is this template for me?", key="template_learn_more_button", type="primary"):
                            self.learn_more_popup()
                        with stylable_container(
                            key="custom_button1_template",
                                css_styles=  
                            """   button {
                                            background-color: #ff8247;
                                            color: white;
                                        }"""
                            ):
                            with st.popover("Download my resume"):
                                c1, c2 = st.columns([1, 1])
                                with c1:
                                    # st.session_state["selected_docx_resume"] = st.session_state["formatted_docx_paths"][st.session_state.selected_idx]
                                    with open(st.session_state["selected_docx_resume"], "rb") as f:
                                        st.download_button("Download as DOC", f, mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                                with c2:
                                    # st.session_state["selected_pdf_resume"] = st.session_state["formatted_pdf_paths"][st.session_state.selected_idx]
                                    with open(st.session_state["selected_pdf_resume"], "rb") as f:
                                        st.download_button("Download as PDF", f,  mime='application/pdf')

                            # if st.button("Download this template", key="resume_template_button"):
                            #     st.switch_page("pages/downloads.py")
                    float_parent()

    def callback(self, direction, ):
        if direction=="next":
            if st.session_state["selected_idx"]!=st.session_state["previews_len"]-1:
                        st.session_state["selected_idx"]+=1
        elif direction=="previous":
            if st.session_state["selected_idx"]!=0:
                            st.session_state["selected_idx"]-=1
    @st.dialog(title=" ")                
    def learn_more_popup(self):
        filename = st.session_state["formatted_docx_paths"][st.session_state.selected_idx]
        templatename = Path(filename).stem.split("_")
        template_type, template_num=templatename[0], templatename[1]
        design = "minimal" if int(template_num)<=5 else "more complicated"
        st.write(f'This is a {template_type} template with {design} design.')


    @st.fragment()
    def fields_selection(self, ):

        if "resume_fields" not in st.session_state:
            st.session_state["resume_fields"] = ['Contact', 'Education', 'Summary Objective', 'Work Experience', 'Skills', 'Professional Accomplishment', 'Projects', 'Certifications', 'Awards & Honors']
        if "selected_fields" in st.session_state:
            index_selected = [idx for idx, val in enumerate(st.session_state["resume_fields"]) if val in st.session_state["selected_fields"]]
        else:
            index_selected = [0, 1, 2, 3]
        st.write("Fields to include in the resume")
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
    

