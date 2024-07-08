from backend.upgrade_resume import reformat_resume
import uuid
import streamlit as st
import os
from utils.basic_utils import binary_file_downloader_html, convert_docx_to_img
from css.streamlit_css import general_button
from streamlit_image_select import image_select
from backend.upgrade_resume import tailor_resume
from pages.streamlit_utils import progress_bar
from streamlit_float import *
from st_pages import get_pages, get_script_run_ctx 

pages = get_pages("")
ctx = get_script_run_ctx()

def display_resume_templates():
    
    current_page = get_current_page()
    progress_bar(current_page["page_name"])
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
        if st.button("Chose this template", key="resume_template_button"):
            st.session_state["user_resume"] = st.session_state["formatted_docx_paths"][selected_idx]
            print("user picked template")
    # with c3:
    #     float_container = st.container()
    #     with float_container:
    #         st.subheader("Step 3")
    #         st.write("Ready to convert your profile into a downloadable resume. Try it now!")
    #         st.markdown(general_button, unsafe_allow_html=True)    
    #         st.markdown('<span class="general-button"></span>', unsafe_allow_html=True)
    #         reformat= st.button("Convert to a new resume ✨", key="resume_format_button", )
    #         if reformat:
    #             save_user_changes()
    #             st.switch_page("pages/streamlit_reformat.py")




def get_current_page():
    try:
        current_page = pages[ctx.page_script_hash]
    except KeyError:
        current_page = [
            p for p in pages.values() if p["relative_page_hash"] == ctx.page_script_hash
        ][0]
    print("Current page:", current_page)
    return current_page


display_resume_templates()

