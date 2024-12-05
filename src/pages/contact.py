import json
from utils.cookie_manager import retrieve_cookie, init_cookies
from streamlit_utils import nav_to, user_menu, progress_bar, set_streamlit_page_config_once, bottom_info
# from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.buy_me_a_coffee import button
import streamlit as st

set_streamlit_page_config_once()

# STORAGE = os.environ["STORAGE"]
# if STORAGE=="CLOUD":
#     bucket_name = os.environ["BUCKET_NAME"]
#     s3_save_path = os.environ["S3_CHAT_PATH"]
#     session = boto3.Session(         
#                     aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"],
#                     aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"],
#                 )
#     s3 = session.client('s3')
#     s3_fs = s3fs.S3FileSystem(key=os.environ["AWS_SERVER_PUBLIC_KEY"], secret=os.environ["AWS_SERVER_SECRET_KEY"])
# else:
#     bucket_name=None
#     s3=None
# st.logo("./resources/logo_acareerai.png")

class Contact():


    def __init__(self):
        
        # st.session_state["current_page"] = "feedback"
        init_cookies()
        if "userId" not in st.session_state:
            st.session_state["userId"] = retrieve_cookie()
            # if not st.session_state["userId"]:
            #     st.switch_page("pages/user.py")
        # self._init_session_states()
        self._init_display()

    # def _init_session_states(_self, ):

    #     if "user_save_path" not in st.session_state:
    #         if STORAGE=="CLOUD":
    #             st.session_state["user_save_path"] = os.path.join(os.environ["S3_USER_PATH"], _self.userId, "profile")
    #         elif STORAGE=="LOCAL":
    #             st.session_state["user_save_path"] = os.path.join(os.environ["USER_PATH"], _self.userId, "profile")
    #         # Get the current time
    #         now = datetime.now()
    #         # Format the time as "year-month-day-hour-second"
    #         formatted_time = now.strftime("%Y-%m-%d-%H-%M")
    #         st.session_state["users_upload_path"] = os.path.join(st.session_state.user_save_path, "uploads", formatted_time)
    #         st.session_state["users_download_path"] =  os.path.join(st.session_state.user_save_path, "downloads", formatted_time)
    #         paths=[st.session_state["users_download_path"]]
    #         mk_dirs(paths,)

    def _init_display(self, ):

        user_menu(st.session_state.userId, page="contact")
        # progress_bar(2)
        add_vertical_space(10)
        # self.display_downloads()
        # add_vertical_space(5)
        # if "feedback" not in st.session_state: 
        _, c1, _ = st.columns([1, 1, 1])
        with c1: 
            with st.container(border=True):
                st.write("**Contact us**")
                st.write("contact@acareerai.com")
                st.write("**Support us**")
                button(username="Tebbles", floating=False, width=220)
        st.divider()
        bottom_info()


    # def display_downloads(self, ):

    #     _, download_col, _=st.columns([1, 1, 1])
    #     with download_col:
    #         if "selected_docx_resume" in st.session_state:
    #             c1, c2 = st.columns([1, 1])
    #             with c1:
    #                 # st.write("Download as Docx")
    #                 # st.write("⬇")
    #                 # with stylable_container(
    #                 #     key="custom_download_container",
    #                 #         css_styles="""{
    #                 #                 border: 3px solid rgba(49, 51, 63, 0.2);
    #                 #                 border-radius: 0.5rem;
    #                 #                 padding: calc(1em - 1px)
    #                 #             }
    #                 #     """
    #                 # ):
    #                 if STORAGE=="LOCAL":
    #                     with open(st.session_state["selected_docx_resume"], "rb") as f:
    #                         st.download_button("**Download as DOCX**", f, type="primary")
    #                     # st.markdown(binary_file_downloader_html(st.session_state["selected_docx_resume"], "Download as DOCX"), unsafe_allow_html=True)
    #                 elif STORAGE=="CLOUD":
    #                     #upload selected docx to s3
    #                     if "s3_docx_download_path" not in st.session_state:
    #                         filename=str(uuid.uuid4())
    #                         end_path = os.path.join(st.session_state["users_download_path"], filename+".docx")
    #                         if write_file(end_path, file_path=st.session_state["selected_docx_resume"]):
    #                             st.session_state["s3_docx_download_path"] = f"s3://{bucket_name}/{end_path}"
    #                     if s3_fs.exists(st.session_state.s3_docx_download_path):
    #                         with s3_fs.open(st.session_state.s3_docx_download_path, 'rb') as f:
    #                             binary_data = f.read()  # Read file content as binary data
    #                             st.download_button("click to download", binary_data,  type="primary", key="docx_download_button", mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    #                     else:
    #                         print("file does not exists in s3")
    #                         st.info("Something happened, please try again")
        
    #             with c2:
    #                 # st.write("Download as PDF")
    #                 # st.write("⬇")
    #                 # with stylable_container(
    #                 #     key="custom_download_container",
    #                 #     css_styles="""{
    #                 #                 border: 3px solid rgba(49, 51, 63, 0.2);
    #                 #                 border-radius: 0.5rem;
    #                 #                 padding: calc(1em - 1px)
    #                 #             }
    #                 #     """
    #                 # ):
    #                 if STORAGE=="LOCAL":
    #                     # st.markdown(binary_file_downloader_html(st.session_state["selected_pdf_resume"], "Download as PDF"), unsafe_allow_html=True)
    #                     with open(st.session_state["selected_pdf_resume"], "rb") as f:
    #                         st.download_button("**Download as PDF**", f, type="primary",)
    #                 elif STORAGE=="CLOUD":
    #                         #upload selected pdf to s3
    #                     if "s3_pdf_download_path" not in st.session_state:
    #                         filename=str(uuid.uuid4())
    #                         end_path = os.path.join(st.session_state["users_download_path"], filename+".pdf")
    #                         if write_file(end_path, file_path=st.session_state["selected_pdf_resume"]):
    #                             st.session_state["s3_pdf_download_path"] = f"s3://{bucket_name}/{end_path}"
    #                     if s3_fs.exists(st.session_state.s3_pdf_download_path):
    #                         with s3_fs.open(st.session_state.s3_pdf_download_path, 'rb') as f:
    #                             binary_data = f.read()  # Read file content as binary data
    #                             st.download_button("click to download", binary_data, type="primary",  key="pdf_download_button",  mime='application/pdf')
    #                     else:
    #                         st.info("Something happened, please try again")
    #         else:
    #             st.warning('Please go back and select a template',  icon="⚠️")


    # def leave_feedback(self, ):
    #     # _, c, _ = st.columns([2, 1, 2])
    #     # with c:
    #     with st.container(border=True):
    #         st.write("**Feedback**")
    #         st.write("Helpfulness")
    #         helpfulness = st.feedback(options="faces", key="helpfulness_rating",)
    #         st.write('Ease of use')
    #         use = st.feedback(options="faces", key="use_rating")
    #         st.write('Speed')
    #         speed = st.feedback(options="faces", key="speed_rating")
    #         st.write("How likely are you to continue using the resume builder?")
    #         likeliness=st.feedback(options="faces", key="continue_rating")
    #         # helpfulness = sac.rate(label='helpfulness', color="yellow", )
    #         # use= sac.rate(label='ease of use', color="yellow",)
    #         # speed = sac.rate(label='speed', color="yellow",)
    #         suggestions = st.text_area("Suggestions", )
    #         st.button("Submit", on_click=self.save_feedback, args = (helpfulness, use, speed, suggestions, likeliness))

    # def save_feedback(self, helpfulness, use, speed, suggestions, likeliness):
    #     # st.session_state["feedback"]=True
    #     feedback = {st.session_state.userId:{"helpfulness":helpfulness, "ease of use":use, "speed":speed, "suggestions":suggestions, "continue":likeliness}}
    #     with open("user_feedback.json", "w") as f:
    #         json.dump(feedback, f)
    #     st.success("Thank you for your feedback! We will use your feedback to continue improving our products.")

        

        



          

if __name__ == '__main__':

    contact=Contact()
    