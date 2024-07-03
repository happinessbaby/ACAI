from backend.upgrade_resume import reformat_resume
import uuid
import streamlit as st
import os
from utils.basic_utils import binary_file_downloader_html, convert_docx_to_img
from css.streamlit_css import general_button
from streamlit_image_select import image_select


def display_resume_templates():
    
    paths = ["./backend/resume_templates/functional/functional0.docx","./backend/resume_templates/functional/functional1.docx","./backend/resume_templates/chronological/chronological0.docx", "./backend/resume_templates/chronological/chronological1.docx"]
    formatted_docx_paths = []
    formatted_pdf_paths = []
    image_paths = []
    for idx, path in enumerate(paths):
        filename = str(uuid.uuid4())
        output_dir = st.session_state["users_download_path"]
        docx_path = os.path.join(output_dir, filename+".docx")
        reformat_resume(path, st.session_state["user_profile_dict"], docx_path)
        formatted_docx_paths.append(docx_path)
        img_paths, pdf_path = convert_docx_to_img(docx_path, output_dir, idx)
        formatted_pdf_paths.append(pdf_path)
        image_paths.append(img_paths)
    c1, c2 = st.columns([1, 3])
    with c1:
        print("image paths", image_paths)
        previews = [paths[0] for paths in image_paths]
        selected_idx=image_select("Select a template", images=previews, return_value="index")
        st.markdown(general_button, unsafe_allow_html=True)    
        st.markdown(binary_file_downloader_html(formatted_pdf_paths[selected_idx], "Download as PDF"), unsafe_allow_html=True)
        st.markdown(binary_file_downloader_html(formatted_docx_paths[selected_idx], "Download as DOCX"), unsafe_allow_html=True)
    with c2:
        st.image(image_paths[selected_idx])

display_resume_templates()
