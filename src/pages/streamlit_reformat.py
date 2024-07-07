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
from utils.common_utils import process_uploads, process_links, process_inputs


def display_resume_templates():
    
    progress_bar()
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
            # st.subheader("Step 2")
            # st.write("Have a job posting you want to tailor to?")
            # st.markdown(general_button, unsafe_allow_html=True )
            # st.markdown('<span class="general-button"></span>', unsafe_allow_html=True)
            # tailor = st.button("Tailor to a job posting ✨", key="resume_tailor_button")
            # if tailor:
            #     job_posting = st.radio(f" ", 
            #                     key="job_posting_radio", options=["job description", "job posting link"], 
            #                     index = 1 if "job_description"  not in st.session_state else 0
            #                     )
            #     if job_posting=="job posting link":
            #         job_posting_link = st.text_input(label="Job posting link",
            #                                         key="job_posting", 
            #                                         on_change=self.form_callback,
            #                                             # disabled=st.session_state.job_posting_disabled
            #                                         )
            #     elif job_posting=="job description":
            #         job_description = st.text_area("Job description", 
            #                                     key="job_descriptionx", 
            #                                     value=st.session_state.job_description if "job_description" in st.session_state else "",
            #                                         on_change=self.form_callback, 
            #                                         #  disabled=st.session_state.job_description_disabled
            #                                         )
                
            #     tailor_resume()
            float_parent()
    # with c3:
    #     st.subheader("Last step! Let AI Evaluate it for one final check!")
    #     if st.button("Evaluate my resume", key="resume_evaluation_button",):
    #         print("evaluating")
    #     if st.button("skip, take me to the download links", type="primary"):
    #         st.markdown(binary_file_downloader_html(formatted_pdf_paths[selected_idx], "Download as PDF"), unsafe_allow_html=True)
    #         st.markdown(binary_file_downloader_html(formatted_docx_paths[selected_idx], "Download as DOCX"), unsafe_allow_html=True)

def process(self, uploads, upload_type) -> None:

        """Processes user uploads including converting all format to txt, checking content safety, content type, and content topics. 

        Args:
            
            uploads: files or links saved when user uploads on Streamlit
            
            upload_type: "files" or "links"
    
        """

        if upload_type=="resume":
            result = process_uploads(uploads, st.session_state.save_path, st.session_state.sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="resume":
                    st.session_state["resume_path"]= end_path
                    # st.session_state["resume_dict"] = retrieve_or_create_resume_info(resume_path=end_path, )
                else:
                    # st.session_state.resume_checkmark=":red[*]"
                    st.info("Please upload your resume here")
            else:
                st.info("Please upload your resume here")
        elif upload_type=="job_posting":
            result = process_links(uploads, st.session_state.save_path, st.session_state.sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="job posting":
                    st.session_state["job_posting_path"]=end_path
                else:
                    # st.session_state.job_posting_checkmark=":red[*]"
                    st.info("Please upload your job posting link here")
            else:
                st.info("That didn't work. Please try pasting the content in job description instead.")
        elif upload_type=="job_description":
            result = process_inputs(uploads, match_topic="job posting or job description")
            if result is not None:
                st.session_state["job_description"] = uploads  
            else:
                st.info("Please share a job description here")


display_resume_templates()
