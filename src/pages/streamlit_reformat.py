from backend.upgrade_resume import reformat_resume
import uuid
import streamlit as st
import os
from utils.basic_utils import binary_file_downloader_html, convert_docx_to_img
from css.streamlit_css import general_button
from streamlit_image_select import image_select
from backend.upgrade_resume import tailor_resume
from pages.streamlit_utils import progress_bar


def display_resume_templates():
    
    progress_bar()
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
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        print("image paths", image_paths)
        previews = [paths[0] for paths in image_paths]
        selected_idx=image_select("Select a template", images=previews, return_value="index")
        st.markdown(general_button, unsafe_allow_html=True)    
        # st.markdown(binary_file_downloader_html(formatted_pdf_paths[selected_idx], "Download as PDF"), unsafe_allow_html=True)
        # st.markdown(binary_file_downloader_html(formatted_docx_paths[selected_idx], "Download as DOCX"), unsafe_allow_html=True)
    with c2:
        st.image(image_paths[selected_idx])
        if st.button("Chose this template", key="resume_template_button"):
            print("user picked template")
    with c3:
        st.subheader("Step 3")
        st.write("Have a job posting you want to tailor to?")
        st.markdown(general_button, unsafe_allow_html=True )
        st.markdown('<span class="general-button"></span>', unsafe_allow_html=True)
        tailor = st.button("Tailor to a job posting ✨", key="resume_tailor_button")
        if tailor:
            tailor_resume()
    # with c3:
    #     st.subheader("Last step! Let AI Evaluate it for one final check!")
    #     if st.button("Evaluate my resume", key="resume_evaluation_button",):
    #         print("evaluating")
    #     if st.button("skip, take me to the download links", type="primary"):
    #         st.markdown(binary_file_downloader_html(formatted_pdf_paths[selected_idx], "Download as PDF"), unsafe_allow_html=True)
    #         st.markdown(binary_file_downloader_html(formatted_docx_paths[selected_idx], "Download as DOCX"), unsafe_allow_html=True)



display_resume_templates()
