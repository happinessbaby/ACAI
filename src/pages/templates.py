from backend.upgrade_resume import reformat_resume
# import uuid
import os
from utils.basic_utils import list_files, convert_doc_to_pdf, convert_docx_to_img
from css.streamlit_css import new_upload_button, primary_button3
from streamlit_image_select import image_select
from streamlit_utils import progress_bar, set_streamlit_page_config_once, user_menu
from streamlit_float import *
# from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
# from st_pages import get_script_run_ctx 
from streamlit_extras.add_vertical_space import add_vertical_space
from utils.cookie_manager import retrieve_cookie, init_cookies
from multiprocessing import Pool
# from datetime import datetime
from pathlib import Path
import streamlit_antd_components as sac
from utils.lancedb_utils import retrieve_dict_from_table
# from streamlit_pdf_viewer import pdf_viewer
from streamlit_extras.stylable_container import stylable_container
from typing import List
import streamlit as st


set_streamlit_page_config_once()
float_init()
STORAGE = os.environ["STORAGE"]
if STORAGE=="CLOUD":
    template_path = os.environ["S3_RESUME_TEMPLATE_PATH"]
elif STORAGE=="LOCAL":
    template_path = os.environ["RESUME_TEMPLATE_PATH"]
# lance_users_table_current = os.environ["LANCE_USERS_TABLE_TAILORED"]
# pages = get_pages("")
# NOTE: GOINT WITH OPTION 2 FOR NOW 
# option=2
# menu_placeholder=st.empty()
# progressbar_placeholder=st.empty()
# template_placeholder = st.empty()


class Reformat():

    # ctx = get_script_run_ctx()
    
    def __init__(self, ):
        
        # if "init_cookies" not in st.session_state:
        init_cookies() 
        self._init_session_states()
        self._init_display()


    def _init_session_states(_self, ):

        st.session_state["current_page"] = "template"
        if "userId" not in st.session_state:
            st.session_state["userId"] = retrieve_cookie()
            if not st.session_state["userId"]:
                st.switch_page("pages/user.py")
        if "profile" not in st.session_state:
            # st.session_state["profile"]= retrieve_dict_from_table(st.session_state.userId, lance_users_table_current)
            st.switch_page('pages/user.py')
        if "selected_fields" not in st.session_state:
            # if "additional_fields" in st.session_state:
            st.session_state["selected_fields"]=[value[0] for key, value in st.session_state.fields_dict.items() if key not in st.session_state["additional_fields"]]
            st.session_state["resume_fields_dict"] = {field:idx for idx, field in enumerate(st.session_state["selected_fields"])}
            print(st.session_state.selected_fields)
        # if "user_save_path" not in st.session_state:
        #     if STORAGE=="CLOUD":
        #         st.session_state["user_save_path"] = os.path.join(os.environ["S3_USER_PATH"], st.session_state.userId, "profile")
        #     elif STORAGE=="LOCAL":
        #         st.session_state["user_save_path"] = os.path.join(os.environ["USER_PATH"], st.session_state.userId, "profile")
            # Get the current time
            # now = datetime.now()
            # # Format the time as "year-month-day-hour-second"
            # formatted_time = now.strftime("%Y-%m-%d-%H-%M")
            # st.session_state["users_upload_path"] = os.path.join(st.session_state.user_save_path, "uploads", formatted_time)
            # st.session_state["users_download_path"] =  os.path.join(st.session_state.user_save_path, "downloads", formatted_time)
            # paths=[st.session_state["users_download_path"]]
            # mk_dirs(paths,)


    def _init_display(self, ):

        # st.markdown(general_button, unsafe_allow_html=True)   
        # st.markdown(primary_button, unsafe_allow_html=True )
    # with menu_placeholder.container():
        user_menu(st.session_state.userId, page="template")
    # with progressbar_placeholder.container():
        progress_bar(1)
        # if self.reformat_templates():
        if "spinner_container" not in st.session_state:
            _, c, _= st.columns([3, 1, 3])
            with c:
                add_vertical_space(10)
                st.session_state["spinner_placeholder"]=st.empty()        
        if "template_container" not in st.session_state:
            st.session_state["template_placeholder"]=st.empty()
        if "formatted_pdf_paths" in st.session_state and ("update_template" not in st.session_state or not st.session_state["update_template"]):
            if "image_paths" in st.session_state and st.session_state["image_paths"]:
                with st.session_state.template_placeholder.container():
                    self.display_resume_templates()
            else:
                with st.session_state.spinner_placeholder.container():
                    st.subheader("Sorry, that didn't work. Please try again.")
                    self.delete_session_states(["formatted_pdf_paths", "formatted_docx_paths"])
        else:
            st.session_state.template_placeholder.empty()
            self.reformat_templates()
            st.session_state["update_template"]=False
            st.rerun()

   

    def reformat_templates(self, ):

        # if  ("formatted_docx_paths" not in st.session_state or "formatted_pdf_paths" not in st.session_state) or ("fields_changed" in st.session_state and st.session_state["fields_changed"]) or ("update_template" in st.session_state and st.session_state["update_template"]):
        #     print("reformatting templates")
        try:
            template_paths = list_files(template_path, ext=".docx")
            # print(template_paths)
            with st.session_state.spinner_placeholder.container():
                with st.spinner("Updating templates..."):
                    with Pool() as pool:
                        st.session_state["formatted_docx_paths"] = pool.map(reformat_resume, template_paths)
                    if st.session_state["formatted_docx_paths"]:
                        print(st.session_state["formatted_docx_paths"])
                    # if option==1:s
                        with Pool() as pool:
                            result  = pool.map(convert_docx_to_img, st.session_state["formatted_docx_paths"])
                        st.session_state["image_paths"], st.session_state["formatted_pdf_paths"] = zip(*result)
                        st.session_state["image_paths"] = [sorted(paths) for paths in st.session_state["image_paths"] if paths]
                    else:
                        return False
                        # if option==2:
                            # with Pool() as pool:
                            #     st.session_state["formatted_pdf_paths"] = pool.map(convert_doc_to_pdf, st.session_state["formatted_docx_paths"])
            st.session_state.spinner_placeholder.empty()
            return True
        except Exception as e:
            print(e)
            return False



    @st.fragment()
    def display_resume_templates(self, ):
        
            add_vertical_space(2)
            fields_col, template_col, select_col = st.columns([1, 3, 1])
            with fields_col:
                self.fields_selection()  
            # if option==1: 
            with template_col:
                prev_col, preview_col, nxt_col = st.columns([1, 20, 1])
                if "start_idx" not in st.session_state:
                    st.session_state["start_idx"]=0
                previews = [images[0] for images in st.session_state["image_paths"]][st.session_state.start_idx:st.session_state.start_idx+3]
                st.session_state["previews_len"] = len(previews)
                # print(previews)
                with preview_col:    
                    c1, _, _= st.columns([1, 1, 1])
                    c2, _ = st.columns([2, 1])
                    if len(previews)==1:
                        with c1:
                            st.session_state["selected_idx"]=image_select("Select a template", images=previews, return_value="index", index = st.session_state.selected_idx if "selected_idx" in st.session_state else 0,)
                    elif len(previews)==2:
                        with c2:
                            st.session_state["selected_idx"]=image_select("Select a template", images=previews, return_value="index", index = st.session_state.selected_idx if "selected_idx" in st.session_state else 0,)
                    else:
                        st.session_state["selected_idx"]=image_select("Select a template", images=previews, return_value="index", index = st.session_state.selected_idx if "selected_idx" in st.session_state else 0,)    
                with prev_col:
                    add_vertical_space(5)
                    prev = st.button("🞀", key="prev_template_button", on_click=self.callback, args=("previous", ))
                with nxt_col:
                    add_vertical_space(5)
                    nxt = st.button("🞂", key="next_template_button", on_click=self.callback, args=("next", ))
                # st.image(st.session_state["image_paths"][selected_idx])
            # if option==2:
            # with template_col:
                # previews = [pdf for pdf in st.session_state["formatted_pdf_paths"] if pdf]
                # previews = st.session_state["image_paths"]
                # print(previews)
                # if "selected_idx" not in st.session_state:
                #     st.session_state["selected_idx"]=0
                with preview_col:
                    # with stylable_container(
                    #     key="container_with_border",
                    #     css_styles="""
                    #         {
                    #             border: 1px solid red;
                    #             border-radius: 0.5rem;
                    #             padding: calc(1em - 1px)
                    #         }
                    #         """,
                    # ):
                    st.image(st.session_state.image_paths[st.session_state.selected_idx])
                    # pdf_viewer(previews[st.session_state.selected_idx])
                    # self.display_pdf(previews[st.session_state.selected_idx])
                    st.session_state["selected_docx_resume"] = st.session_state["formatted_docx_paths"][st.session_state.selected_idx]
                    st.session_state["selected_pdf_resume"] = st.session_state["formatted_pdf_paths"][st.session_state.selected_idx]

                with select_col:
                    _, c = st.columns([0.5, 1])
                    with c:
                        float_container=st.container()
                        with float_container:
                            # add_vertical_space(10)
                            st.markdown(primary_button3, unsafe_allow_html=True)
                            st.markdown('<span class="primary-button3"></span>', unsafe_allow_html=True)
                            if st.button(label="Is this template for me?", key="template_learn_more_button", ):
                                self.learn_more_popup(st.session_state.selected_idx)
                            with stylable_container(
                                key="custom_button1_template",
                                    css_styles=  new_upload_button
                                ):
                                with st.popover("Download my resume"):
                                    c1, c2 = st.columns([1, 1])
                                    with c1:
                                        # st.session_state["selected_docx_resume"] = st.session_state["formatted_docx_paths"][st.session_state.selected_idx]
                                        with open(st.session_state["selected_docx_resume"], "rb") as f:
                                            st.download_button("Recommended: Download as Microsoft Word", f, mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                                    with c2:
                                        # st.session_state["selected_pdf_resume"] = st.session_state["formatted_pdf_paths"][st.session_state.selected_idx]
                                        with open(st.session_state["selected_pdf_resume"], "rb") as f:
                                            st.download_button("Download as PDF", f,  mime='application/pdf')

                                # if st.button("Download this template", key="resume_template_button"):
                                #     st.switch_page("pages/downloads.py")
                        float_parent()

    def callback(self, direction, ):
        if direction=="next":
            # if st.session_state["selected_idx"]!=st.session_state["previews_len"]-1:
            #   st.session_state["selected_idx"]+=1
            st.session_state["start_idx"] += 3
            if st.session_state.start_idx>=st.session_state.previews_len:
                st.session_state.start_idx-=3
        elif direction=="previous":
            # if st.session_state["selected_idx"]!=0:
            #     st.session_state["selected_idx"]-=1
            st.session_state["start_idx"] -= 3
            if st.session_state.start_idx<=0:
                st.session_state.start_idx=0


    @st.dialog(title=" ", )                
    def learn_more_popup(self, selected_idx):
        filename = st.session_state["formatted_docx_paths"][selected_idx]
        templatename = Path(filename).stem.split("_")
        template_type, template_num=templatename[0], templatename[1]
        design = "minimal" if int(template_num)<=5 else "more complicated"
        st.write(f'This is a {template_type} template with {design} design.')


    @st.fragment()
    def fields_selection(self, ):

        with st.container(border=True):
            st.write("Fields to include in the resume")
            items = []
            index = [idx for field, idx in st.session_state.resume_fields_dict.items() if field in st.session_state["selected_fields"]]
            for field, idx in st.session_state.resume_fields_dict.items():
                items.append(sac.ChipItem(label=field))
            selected_fields = sac.chip(
                # items=[
                #     sac.ChipItem(label='Contact'),
                #     sac.ChipItem(label='Education'),
                #     sac.ChipItem(label='Summary Objective'),
                #     sac.ChipItem(label='Work Experience'),
                #     sac.ChipItem(label='Skills'),
                #     sac.ChipItem(label='Professional Accomplishment'),
                #     sac.ChipItem(label='Projects'),
                #     sac.ChipItem(label='Certifications'),
                #     sac.ChipItem(label='Awards & Honors'),
                #     sac.ChipItem(label="Licenses"),
                #     sac.ChipItem(label="Hobbies"),
                # ],
                items=items,
                  label=' ',
                    index=index,
                      align='center', radius='md', multiple=True , variant="outline", color= "#47ff5a")
            _, c1 = st.columns([2, 1])
            with c1:
                if st.button("Confirm", key="fields_selection_button"):
                    if selected_fields!=st.session_state["selected_fields"]:
                        # st.session_state["fields_changed"]=True
                        st.session_state["selected_fields"]=selected_fields
                        if self.reformat_templates():
                             st.rerun()
                        # st.rerun()
                             
    def delete_session_states(self, names:List[str])->None:

        """ Helper function to clean up session state"""

        for name in names:
            try:
                del st.session_state[name]
            except Exception:
                pass

if __name__ == '__main__':

    reformat=Reformat()







