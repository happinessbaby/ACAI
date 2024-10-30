from streamlit_extras.add_vertical_space import add_vertical_space
import os
# from google.oauth2 import id_token
from google.auth.transport import requests
from utils.cookie_manager import retrieve_cookie, authenticate, delete_cookie, add_user, check_user, change_password, save_cookies, init_cookies
import time
from datetime import datetime
from utils.lancedb_utils import retrieve_dict_from_table, delete_user_from_table, save_user_changes, convert_pydantic_schema_to_arrow, delete_job_from_table, save_job_posting_changes
from utils.common_utils import  process_uploads, create_resume_info, process_links, process_inputs, create_job_posting_info, grammar_checker, suggest_skills, research_skills
from utils.basic_utils import mk_dirs, send_recovery_email, change_hex_color
from typing import Any, List
from backend.upgrade_resume import reformat_resume, match_resume_job
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from utils.pydantic_schema import ResumeUsers, GeneralEvaluation, JobTrackingUsers
from streamlit_utils import user_menu, progress_bar, set_streamlit_page_config_once, hide_streamlit_icons,length_chart, comparison_chart, language_radar, readability_indicator, automatic_download, Progress, percentage_comparison
from css.streamlit_css import primary_button3, google_button, primary_button2, primary_button, linkedin_button, included_skills_button, suggested_skills_button, new_upload_button
from backend.upgrade_resume import tailor_resume, evaluate_resume
# from backend.generate_cover_letter import generate_basic_cover_letter
# from streamlit_float import *
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
# from st_pages import get_script_run_ctx 
from streamlit_extras.stylable_container import stylable_container
from authlib.integrations.requests_client import OAuth2Session
from annotated_text import annotated_text
from st_draggable_list import DraggableList
from streamlit_extras.grid import grid
import streamlit_antd_components as sac
from streamlit_tags import st_tags
import requests
# from apscheduler.schedulers.background import BackgroundScheduler
# from threading import Thread
# from utils.async_utils import thread_with_trace, asyncio_run
import re
import queue
from multiprocessing import Pool
# import streamlit_antd_components as sac
#NOTE: below import is necessary for nested column fix, do not delete
import streamlit_nested_layout 
import streamlit as st


set_streamlit_page_config_once()
hide_streamlit_icons()

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

STORAGE = os.environ['STORAGE']
if STORAGE=="CLOUD":
    login_file = os.environ["S3_LOGIN_FILE_PATH"]
    db_path=os.environ["S3_LANCEDB_PATH"]
    base_uri = os.environ["CLOUD_BASE_URI"]
    template_path = os.environ["S3_RESUME_TEMPLATE_PATH"]
elif STORAGE=="LOCAL":
    login_file = os.environ["LOGIN_FILE_PATH"]
    db_path=os.environ["LANCEDB_PATH"]
    base_uri = os.environ["BASE_URI"]
    template_path = os.environ["RESUME_TEMPLATE_PATH"]
client_secret_json = os.environ["CLIENT_SECRET_JSON"]
user_profile_file=os.environ["USER_PROFILE_FILE"]
linkedin_client_id = os.environ["LINKEDIN_CLIENT_ID"]
linkedin_client_secret =os.environ["LINKEDIN_CLIENT_SECRET"]
lance_eval_table = os.environ["LANCE_EVAL_TABLE"]
lance_users_table_default = os.environ["LANCE_USERS_TABLE"]
# lance_users_table_tailored = os.environ["LANCE_USERS_TABLE_TAILORED"]
lance_tracker_table = os.environ["LANCE_TRACKER_TABLE"]
other_cookie_key = os.environ["OTHER_COOKIE_KEY"]
user_cookie_key=os.environ["USER_COOKIE_KEY"]
menu_placeholder=st.empty()
profile_placeholder=st.empty()
_, c, _= st.columns([3, 1, 3])
with c:
    add_vertical_space(20)
    spinner_placeholder=st.empty()
_, c1, _ = st.columns([3, 2, 3])
with c1:
    signin_placeholder=st.empty()
    signup_placeholder=st.empty()
_, c2, _ = st.columns([1, 1, 1, ])
with c2:
    resume_placeholder=st.empty()

# initialize float feature/capability
# float_init()
# store = FeatureStore("./my_feature_repo/")


# st.markdown(
#     """
# <style>
#     [data-testid="collapsedControl"] {
#         display: none
#     }
# </style>
# """,
#     unsafe_allow_html=True,
# )
st.markdown("<style> ul {display: none;} </style>", unsafe_allow_html=True)
# pages = get_pages("")

#initialize evaluation fragment rerun timer 
#NOTE: fragment parameter seems to need to be set at topmost level
if "eval_rerun_timer" not in st.session_state:
    st.session_state["eval_rerun_timer"]=3


all_fields=["contact", "educations", "summary_objective", "included_skills", "projects", "qualifications", "certifications", "awards", "work_experience", "hobbies", "licenses"]
all_fields_icons = [":material/contacts:", ":material/school:", ":material/summarize:", ":material/widgets:", ":material/perm_media:", ":material/commit:", ":material/license:", ":material/workspace_premium:", ":material/work_history:", ":material/heart_plus:", ":material/license:"]
all_fields_labels=["Contact", "Education", "Summary Objective", "Skills", "Projects", "Professional Accomplishment", "Certifications", "Awards & Honors", "Work Experience", "Hobbies", "Licenses"]

class User():

    ctx = get_script_run_ctx()

    def __init__(self, ):
        # if "init_cookies" not in st.session_state:
        init_cookies()
        self._init_session_states()
        self._init_display()
        # self.reformat_templates()


    # @st.cache_data()
    def _init_session_states(_self, ):

        # set current page for progress bar
        st.session_state["current_page"] = "profile"
        # NOTE: userId is retrieved from browser cookie
        if "userId" not in st.session_state:
            st.session_state["userId"] = retrieve_cookie()
        if "logo_path" not in st.session_state:
            st.session_state["logo_path"]="./resources/logo-no-background.png"
        if st.session_state["userId"] is not None:
            _self.save_session_profile()
            if "user_mode" not in st.session_state:
                st.session_state["user_mode"]="signedin"
            if "profile" not in st.session_state:
                st.session_state["profile"]= retrieve_dict_from_table(st.session_state.userId, lance_users_table_default)
            if "profile_schema" not in st.session_state:
                st.session_state["profile_schema"] = convert_pydantic_schema_to_arrow(ResumeUsers)
            if "evaluation" not in st.session_state:
                st.session_state["evaluation"] = retrieve_dict_from_table(st.session_state.userId, lance_eval_table)
            if "evaluation_schema" not in st.session_state:
                st.session_state["evaluation_schema"] = convert_pydantic_schema_to_arrow(GeneralEvaluation)
            if "tracker" not in st.session_state:
                st.session_state["tracker"] = retrieve_dict_from_table(st.session_state.userId, lance_tracker_table)
                if st.session_state["tracker"]:
                    last_edit = sorted(st.session_state["tracker"],  key=lambda x: x["last_edit_time"], reverse=True)[0]["last_edit_time"]
                    print(last_edit)
                    st.session_state["current_idx"]=next((i for i, item in enumerate(st.session_state["tracker"]) if item.get("last_edit_time") == last_edit), -1)
                    print(st.session_state["current_idx"])
                    # NOTE: job_posting_dict is a session copy of the job posting on display
                    st.session_state["job_posting_dict"]=st.session_state["tracker"][st.session_state.current_idx]
                    st.session_state["tailor_color"] = st.session_state["job_posting_dict"]["color"]
            if "tracker_schema" not in st.session_state:
                st.session_state["tracker_schema"]=convert_pydantic_schema_to_arrow(JobTrackingUsers)
            # if "init_templates" not in st.session_state:
            #     scheduler = BackgroundScheduler()
            #     scheduler.start()
            #     scheduler.add_job(_self.reformat_templates, 'interval', seconds=10)
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
                paths=[st.session_state["users_upload_path"], st.session_state["users_download_path"]]
                mk_dirs(paths,)
            if "selection" not in st.session_state:
                st.session_state["selection"]="default"
                # st._config.set_option(f'theme.secondaryBackgroundColor' ,"#ffffff" )
                st._config.set_option(f'theme.textColor' ,"#2d2e29" ) 
                st._config.set_option(f'theme.primaryColor' ,"#ff9747" )
            if "fields_dict" not in st.session_state:
                zipped = zip(all_fields, all_fields_labels, all_fields_icons)
                st.session_state["fields_dict"] = {key: (val1, val2) for key, val1, val2 in zipped}
            if "additional_fields" not in st.session_state:
                st.session_state["additional_fields"]=[]
                if st.session_state["profile"]:
                    for field in all_fields:
                        if st.session_state["profile"][field] is None:
                            st.session_state.additional_fields.append(field)
            if "show" not in st.session_state:
                st.session_state["show"]=False
        else:
            if "user_mode" not in st.session_state:  
                st.session_state["user_mode"]="signedout"






    def _init_display(self):

        """ Initalizes user page according to user's sign in status"""
        st.markdown(primary_button, unsafe_allow_html=True )
        token = st.query_params.get("token")
        username = st.query_params.get("username")
        if token and username:
            st.session_state["user_mode"]="reset"
            self.reset_password(token, username)
        if st.session_state.user_mode!="signedout" and st.session_state.user_mode!="reset":
            with menu_placeholder.container():
                user_menu(st.session_state.userId, page="profile")
            # st.logo("./resources/logo_acareerai.png")
        if st.session_state.user_mode=="signup":
            with signup_placeholder.container():
                print("signing up")
                self.sign_up()
        elif st.session_state.user_mode=="signedin":
            st.query_params.clear()
            print("signed in")
            if "redirect_page" in st.session_state:
                st.switch_page(st.session_state.redirect_page)
            else:
                try:
                    if not st.session_state["profile"]:
                        with resume_placeholder.container():
                            print("user profile does not exists yet")
                            # ask user for their resumes
                            self.initialize_resume()
                    else:
                        with profile_placeholder.container():
                            #display the progress bar
                            progress_bar(0)
                            add_vertical_space(8)
                            # display the main profile
                            self.display_profile()
                except KeyError as e:
                    print(e)
                    # NOTE; sometimes retrieval of the user_profile_dict is slow so "if st.session_state["user_profile_dict"]" will raise an error
                    # rerun will allow time for "user_profile_dict" to get populated
                    st.rerun()
                    # if e.args[0] == "user_profile_dict":
                    #     # Handle the specific case where "user_profile_dict" is not present
                    #     print("user_profile_dict not found, rerunning...")
                    #     st.rerun()
                    # else:
                    #     # Re-raise the KeyError for any other missing key
                    #     raise
        elif st.session_state.user_mode=="signedout":
            with signin_placeholder.container(border=True):
                print("signing in")
                self.sign_in()
        elif st.session_state.user_mode=="signout":
            self.sign_out()
        # elif st.session_state.user_mode=="reset_password":
        #     self.reset_password()

          
    


    
    # @st.fragment()
    def sign_out(self, ):

        print('signing out')
        # also needs to manually delete cookies for google login case
        # st.session_state.cm.delete_cookie()
        delete_cookie()
        try:
            # still needs the logout code since the authenticators need to be cleared
            # st.session_state.authenticator.logout(location="unrendered")
            self.google_signout()
        except Exception:
            pass
        st.session_state["user_mode"]="signedout"
        st.session_state["userId"] = None
        # time.sleep(5)
        if "redirect_page" in st.session_state:
            st.switch_page(st.session_state.redirect_page)
        else:
            st.rerun()

    # @st.fragment()
    def sign_in(self, ):

        add_vertical_space(3)
        _, img_col, _ = st.columns([1, 4, 1])
        with img_col:
            st.image(st.session_state.logo_path)
        add_vertical_space(2)
        _, g_col= st.columns([1, 3])
        with g_col:
            self.google_signin()
            self.linkedin_signin()
        # add_vertical_space(1)
        # sac.divider(label='or',  align='center', color='gray')
        st.divider()
        st.subheader("Log in")
        with st.form(key="login_form", clear_on_submit=True, ):
            username=st.text_input("Email", )
            password=st.text_input("Password", type="password")
            signin = st.form_submit_button("login", )
                # name, authentication_status, username = st.session_state.authenticator.login()
                # if authentication_status:
                #     # email = st.session_state.authenticator.credentials["usernames"][username]["email"]
                #     st.session_state["user_mode"]="signedin"
                #     st.session_state["userId"] = username
                #     # time.sleep(5)
                #     st.rerun()
                # elif authentication_status==False:
                #     st.error('Username/password is incorrect')
                # placeholder_error = st.empty()
        _, signup_col, forgot_password_col= st.columns([5, 2, 2])
        with signup_col:
            add_vertical_space(2)
            signup = st.button(label="Sign up", key="signup",  type="primary")
        with forgot_password_col:
            st.markdown(primary_button3, unsafe_allow_html=True)
            st.markdown('<span class="primary-button3"></span>', unsafe_allow_html=True)
            forgot=st.button(label="recover password", key="forgot_password", )
        if signup:
            signin_placeholder.empty()
            st.session_state["user_mode"]="signup"
            st.rerun()
        if signin:
            username= authenticate(username, password)
            if username:
                signin_placeholder.empty()
                st.session_state["user_mode"]="signedin"
                st.session_state["userId"]=username
                print("signed in")
                st.rerun()
            else:
                st.error('Wrong username/password.')
        if forgot:
            self.recover_password_popup()


    @st.dialog(title=" ")
    def recover_password_popup(self):

        add_vertical_space(1)
        st.session_state['recover_disabled']=False
        # username, email = st.session_state.authenticator.forgot_username(fields={"Form name": "", "Email":"Please provide the email associated with your account"})
        email = st.text_input("Please provide the email associated with your account", key="recover_password_email", on_change=check_user)
        if not st.session_state.recover_password_email:
            st.session_state.recover_disabled=True
        if "recover_error_msg" in st.session_state: 
            if  st.session_state["recover_error_msg"]=="email not exists":
                st.error("Email does not exists")
                st.session_state.recover_disabled=True   
            elif st.session_state["recover_error_msg"]=="email invalid":
                st.error("Please provide a valid email")
                st.session_state.recover_disabled=True   
            del st.session_state["recover_error_msg"]
        submit = st.button("next", key="recover_password_submit_button", disabled=st.session_state.recover_disabled, )
        if submit:
            if "recover_password" in st.session_state:
                with st.spinner("Processing..."):
                    if send_recovery_email(st.session_state.recover_password_email, ):
                        st.success('Please check your email')
            else:
                st.error("something went wrong, please try again.")


    def google_signin(self,):

        auth_code = st.query_params.get("code")
        # auth_code = retrieve_cookie(cooke_key=google_cookie_key)
      
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            client_secret_json,
            scopes=["https://www.googleapis.com/auth/userinfo.email", "openid"],
            redirect_uri=st.session_state.redirect_page if "redirect_page" in st.session_state else base_uri+"/user",
            )
        if auth_code:
            try:
                flow.fetch_token(code=auth_code)
                credentials = flow.credentials
                user_info_service = build(
                    serviceName="oauth2",
                    version="v2",
                    credentials=credentials,
                )
                user_info = user_info_service.userinfo().get().execute()
                assert user_info.get("email"), "Email not found in infos"
                st.session_state["credentials"] = credentials
                # save_cookie(user_info.get("email"))
                # save_cookie(credentials.token, cookie_key=google_cookie_key)
                save_cookies({user_cookie_key:user_info.get("email"), other_cookie_key:credentials.token})
                st.session_state["user_mode"]="signedin"
                st.session_state["userId"]=user_info.get("email")
                st.rerun()
            except Exception as e:
                print(e)
                # clear the parameters including auth_code to allow user to access sign in button again
                st.query_params.clear()
                st.rerun()
        else:
            st.markdown(google_button, unsafe_allow_html=True)
            st.markdown('<span id="google-button-after"></span>', unsafe_allow_html=True)
            if st.button("Continue with Google"):
                authorization_url, state = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                )
                # webbrowser.open_new_tab(authorization_url)
                # st.query_params.redirect_uri=authorization_url
                # st.query_params.state=state
                # st.experimental_set_query_params(redirect_uri=authorization_url, state=state)
                st.write(f'<meta http-equiv="refresh" content="0;url={authorization_url}">', unsafe_allow_html=True)

    def google_signout(self):

        token = retrieve_cookie(cookie_key=other_cookie_key)
        if token:
        # if "credentials" in st.session_state:
            # credentials = st.session_state["credentials"]
            revoke_token_url = "https://accounts.google.com/o/oauth2/revoke?token=" + token
            response = requests.get(revoke_token_url)
            if response.status_code == 200:
                st.query_params.clear()
                print("Successfully signed out of Google")
                # Clear session state
                # del st.session_state["credentials"]
                delete_cookie(cookie_key=other_cookie_key)
            else:
                print("Failed to revoke token")
        else:
            print("No user is signed in")
    

    def linkedin_signin(self):

        redirect_uri = st.session_state.redirect_page if "redirect_page" in st.session_state else base_uri + "/user"
        auth_code = st.query_params.get("code")   
        linkedin = OAuth2Session(linkedin_client_id, linkedin_client_secret, redirect_uri=redirect_uri)     
        if auth_code:
            try:
                # Exchange authorization code for access token
                token = linkedin.fetch_token(
                    'https://www.linkedin.com/oauth/v2/accessToken',
                    code=auth_code,
                    client_secret=linkedin_client_secret
                )

                # Use the access token to fetch user profile information
                linkedin = OAuth2Session(linkedin_client_id, token=token)
                user_info = linkedin.get('https://api.linkedin.com/v2/me').json()
                email_info = linkedin.get('https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))').json()

                # assert email_info['elements'][0]['handle~']['emailAddress'], "Email not found in infos"

                # Save user credentials and info in session state
                st.session_state["credentials"] = token
                st.session_state["user_mode"] = "signedin"
                st.session_state["userId"] = email_info['elements'][0]['handle~']['emailAddress']

                # Save cookies for user email and token
                save_cookies({
                    user_cookie_key: email_info['elements'][0]['handle~']['emailAddress'],
                    other_cookie_key: token['access_token']
                })
                st.rerun()
            except Exception as e:
                print(e)
                # Clear the parameters including auth_code to allow user to access sign-in button again
                st.query_params.clear()
                st.rerun()
        else:
            # Show LinkedIn sign-in button
            st.markdown(linkedin_button, unsafe_allow_html=True)
            st.markdown('<span id="linkedin-button-after"></span>', unsafe_allow_html=True)
            if st.button("Continue with LinkedIn"):
                # Get LinkedIn authorization URL
                authorization_url, state = linkedin.create_authorization_url(
                    'https://www.linkedin.com/oauth/v2/authorization',
                    scope=["r_liteprofile", "r_emailaddress"]
                )
                # Redirect user to the LinkedIn authorization URL
                st.write(f'<meta http-equiv="refresh" content="0;url={authorization_url}">', unsafe_allow_html=True)

    # @st.fragment()
    def sign_up(self,):

        print("inside signing up")
        st.subheader("Register")
        with st.container(border=True):
            st.session_state["signup_disabled"]=False
            # with st.form("sign_up_form"):
            first_name=st.text_input("First name (optional)", key="signup_first_name", )
            last_name = st.text_input("Last name (optional)", key="signup_last_name")
            email = st.text_input("Email", key="signup_email", on_change=check_user)
            password=st.text_input("Password", type="password", key="signup_password", on_change=check_user, )
            confirm_password = st.text_input("Confirm password", type="password", key="signup_password_confirm", )
            if password and confirm_password and password!=confirm_password:
                st.error("Passwords don't match")
                st.session_state.signup_disabled=True
            if "signup_error_msg" in st.session_state:
                if st.session_state.signup_error_msg == "email exists":
                    st.error("Email already exists. Please log in.")
                elif st.session_state.signup_error_msg == "email invalid":
                    st.error("Please provide a valid email. ")
                elif st.session_state.signup_error_msg == "password length":
                    st.error("Password must be greater than 6 characters")
                del st.session_state["signup_error_msg"]
                st.session_state.signup_disabled=True
            if not st.session_state.signup_email or not st.session_state.signup_password or not st.session_state.signup_password_confirm:
                st.session_state.signup_disabled=True
            submit = st.button("sign up", key="signup_submit_button", disabled=st.session_state.signup_disabled)
        if submit:
            if add_user(email, password, first_name, last_name):
                st.session_state["user_mode"]="signedin"
                st.session_state["userId"] = email
                # st.success("User registered successfully. Redirecting...")
                signup_placeholder.empty()
                # time.sleep(5)
                st.rerun()
        # with c:
        #     try:
        #         authenticator = st.session_state.authenticator
        #         email, username, name= authenticator.register_user(pre_authorization=False)
        #         if email:
        #             with open(login_file, 'w') as file:
        #                 yaml.dump(st.session_state.config, file, default_flow_style=False)
        #             # if self.save_password( username, name, password, email):
        #             st.session_state["user_mode"]="signedin"
        #             st.session_state["userId"] = username
        #             st.success("User registered successfully. Redirecting...")
        #             # time.sleep(5)
        #             st.rerun()
        #     except RegisterError as e:
        #         if e.message=="Password does not meet criteria":
        #             st.warning("""Password must:
        #             Contain at least one lowercase letter, at least one uppercase letter, at least one digit, at least one special character and between 8 and 20 characters in length""")
        #         else:
        #             st.warning(e)
    # @st.fragment()
    def reset_password(self, token, username):
    
        _, c, _ = st.columns([3, 2, 3])
        with c:
            if self.verify_token(token):
                with st.form(key="password_reset_form"):
                # Display the password reset form
                    st.image("./resources/logo_acareerai.png")
                    # st.subheader("Password Reset")
                    new_password = st.text_input("New Password", type="password", )
                    confirm_password = st.text_input("Confirm Password", type="password")               
                    if st.form_submit_button("Reset Password"):
                        if new_password == confirm_password:
                            # Update the user's password in the database
                            # self.save_password(new_password, username)
                            change_password(username, new_password)
                            st.success("Password has been reset successfully! Redirecting...")
                            st.session_state["user_mode"]="signedin"
                            st.session_state["userId"] = username
                            time.sleep(1)
                            st.query_params.clear()
                            # nav_to("/user")  
                            st.switch_page("pages/user.py")                            
                        else:
                            st.error("Passwords do not match.")
            else:
                st.error("Invalid or expired token.")
 
                

    # def save_password(self, password, username, filename=login_file):

    #     try:
    #         with open(filename, 'r') as file:
    #             credentials = yaml.safe_load(file)
    #             # Add the new user's details to the dictionary
    #         # credentials['credentials']['usernames'][username] = {
    #         #     'email': email,
    #         #     'name': name,
    #         #     'password': password
    #         # }  
    #         credentials['credentials']['usernames'][username]['password']=password
    #         with open(filename, 'w') as file:
    #             yaml.dump(credentials, file)
    #         print("successfully saved password")
    #         # return True
    #     except Exception as e:
    #         raise e


    def verify_token(self, token):
        # Token verification logic
        # Check if token exists in the database and is not expired
        return True       


    
    def initialize_resume(self):
 
        st.title("Let's get started with your resume")
        if "user_resume_path" in st.session_state:
            st.session_state.resume_disabled = False
        else:
            st.session_state.resume_disabled = True
        st.markdown("#")
        resume = st.file_uploader(label="Upload your resume",
                        key="user_resume",
                            accept_multiple_files=False, 
                            # on_change=self.form_callback, 
                            type=["pdf", "odt", "docx", "txt"],
                            help="This will become your profile")
        _, c2 = st.columns([3, 1])
        with c2:
            add_vertical_space(2)
            skip= st.button(label="I'll do it later", type="primary", key="skip_resume_button" )
        if skip:
            menu_placeholder.empty()
            resume_placeholder.empty()
            with spinner_placeholder.container():
                with st.spinner("Loading your profile..."):
                    time.sleep(1)
                    self.create_empty_profile() 
                    st.rerun()
        if resume:
            menu_placeholder.empty()
            resume_placeholder.empty()
            with spinner_placeholder.container():
                with st.spinner("Processing..."):
                    # self.form_callback()
                    self.process(resume, "resume")
                if "user_resume_path" in st.session_state:
                    with st.spinner("Creating your profile..."):
                        self.initialize_resume_callback()
                        st.rerun()

    def initialize_resume_callback(self, ):

        """Saves user resume to a lancedb table"""
        # create generated dict from resume
        q = queue.Queue()
        t = threading.Thread(target=create_resume_info, args=(st.session_state.user_resume_path, q, ), daemon=True)
        t.start()
        t.join()
        resume_dict = q.get()
        resume_dict.update({"resume_path":st.session_state.user_resume_path})
        resume_dict.update({"user_id": st.session_state.userId}) 
        # save resume dict into session's profile
        st.session_state["profile"] = resume_dict
        for field in all_fields:
            if st.session_state["profile"][field] is None:
                st.session_state.additional_fields.append(field)
        # save resume/profile into lancedb table
        save_user_changes(st.session_state.userId, resume_dict, st.session_state["profile_schema"], lance_users_table_default)
        st.session_state["update_template"]=True
        st.session_state["profile_changed"]=True
        st.session_state["show"]=False
        # for field in st.session_state["additional_fields"]:
        #     self.delete_session_states([f"{field}_add_button"])
        self.delete_session_states(["user_resume_path"])
        print("Successfully added user to lancedb table")

                 
    def create_empty_profile(self):

        """ In case user did not upload a resume, this creates an empty profile and saves it as a lancedb table entry"""

        st.session_state["profile"] = {"user_id": st.session_state.userId, "resume_path": "", "resume_content":"",
                   "contact": {"city":"", "email": "", "links":[], "name":"", "phone":"", "state":"" }, 
                   "educations": None, 
                   "pursuit_jobs":"", "industry":"", "summary_objective":"", "included_skills":None, "work_experience":None, "projects":None, 
                   "certifications":None, "suggested_skills":None, "qualifications":None, "awards":None, "licenses":None, "hobbies":None}
        for field in all_fields:
            if st.session_state["profile"][field] is None:
                st.session_state.additional_fields.append(field)
        # save_user_changes(st.session_state.userId, st.session_state.profile, st.session_state["profile_schema"], lance_users_table_tailored)
        save_user_changes(st.session_state.userId, st.session_state.profile, st.session_state["profile_schema"], lance_users_table_default)
         # delete any old resume saved in session state
        self.delete_session_states(["user_resume_path"])
        st.session_state["show"]=False
        # for field in st.session_state["additional_fields"]:
        #     self.delete_session_states([f"{field}_add_button"])
        # prevent evaluation when profile is empty 
        st.session_state["init_eval"]=False
        st.session_state["profile_changed"]=True
        st.session_state["update_template"]=True




    def process(self, input_value: Any, input_type:str, ):

        """ Processes and checks user inputs and uploads"""

        if input_type=="resume":
            result = process_uploads(input_value, st.session_state.users_upload_path, )
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="resume":
                    st.session_state["user_resume_path"]= end_path
                else:
                    st.warning("Please upload your resume")
                    time.sleep(2)
                    st.rerun()
            else:
                st.warning("That didn't work, please try again.") 
                time.sleep(2)   
                st.rerun()  
        if input_type=="job_posting":
            st.session_state["posting_link"]=input_value.get("job_posting_link", "")
            description = input_value.get("job_posting_description", "")
            if st.session_state.posting_link:
                result = process_links(st.session_state.posting_link, st.session_state.users_upload_path, )
                if result is not None:
                    content_safe, content_type, content_topics, end_path = result
                    if content_safe and content_type=="job posting":
                        st.session_state["job_posting_path"]=end_path
            if description:
                result = process_inputs(description, )
                if result is not None:
                    topic, safe = result
                    if topic=="job description" and safe:
                        st.session_state["job_description"] = description
          
       
            

    @st.dialog("Rearrange")  
    def rearrange_skills_popup(self, ):
        add_vertical_space(2)
        data=[]
        idx=0
        for skill in self.skills_set:
            data.append({"id":skill, "order":idx, "name":skill})
            idx+=1
        slist = DraggableList(data, key="skills_rearrange_draggable")
        _, c = st.columns([3, 1])
        with c:
            if st.button("confirm", key="confirm_rearrange_skills_button"):
                st.session_state["profile"]["included_skills"]=[skill["name"] for skill in slist]
                st.session_state["profile_changed"]=True
                st.rerun()
        


    @st.fragment
    def display_skills(self, ):

        """ Interactive display of skills section of the profile"""

        @st.fragment
        def get_display():

            if st.session_state["profile"]["included_skills"] is None:
                st.session_state["profile"]["included_skills"]=[]
                st.session_state["profile_changed"]=True
            c1, c2=st.columns([2, 1])
            with c1:
                with st.container(border=True):
                    c3, c4 = st.columns([3, 1])
                    with c3:
                        st.write("**Your skills**")
                    with c4:
                        with stylable_container(
                            key="custom_rearrange_skills_button",
                            css_styles="""
                                button {
                                    background: none;
                                    border: none;
                                    color: #ff8247;
                                    padding: 0;
                                    cursor: pointer;
                                    font-size: 12px; 
                                    text-decoration: none;
                                }
                            """,
                        ):
                            if self.skills_set:
                                if st.button("Rearrange", key="rearrange_skills_button", ):
                                    self.rearrange_skills_popup()

                    # with stylable_container(key="custom_skills_button",
                    #         css_styles=included_skills_button,
                    # ):
                    # included_grid=grid([1, 1, 1])
                    # for idx, skill in enumerate(self.skills_set):
                        # x = included_grid.button(skill+" :red[x]", key=f"remove_skill_{idx}", on_click=skills_callback, args=(idx, skill, ), type="primary")
                    included_skills = st_tags(
                        label=' ',
                        text='Press enter to add more',
                        value=self.skills_set,
                        suggestions=self.generated_skills_set,
                        key='included_skills_tags')
                    # print(included_skills)
                    if included_skills!=self.skills_set:
                        st.session_state["profile"]["included_skills"]=included_skills
                        self.skills_set=included_skills
                        st.session_state["profile_changed"]=True
            with c2:
                c3, c4 = st.columns([3, 1])
                with c3:
                    st.write("**Suggested skills**")
                with c4:
                    with stylable_container(
                            key="custom_rearrange_skills_button",
                            css_styles="""
                                button {
                                    background: none;
                                    border: none;
                                    color: #ff8247;
                                    padding: 0;
                                    cursor: pointer;
                                    font-size: 12px; 
                                    text-decoration: none;
                                }
                            """,
                        ):
                        if st.button("Refresh", key="refresh_suggested_skills_button", ):
                            if st.session_state["selection"]=="default" or st.session_state["tracker"] is None:
                                print("AAAAAA", st.session_state["profile"]["resume_content"])
                                suggested_skills =list(set(suggest_skills(st.session_state["profile"]["resume_content"], job_posting=None)))
                            else:
                                suggested_skills = list(set(suggest_skills(st.session_state["profile"]["resume_content"], st.session_state["tracker"][st.session_state.current_idx]["content"])))
                            st.session_state["profile"]["suggested_skills"]=suggested_skills
                            st.session_state["profile_changed"]=True
                            self.generated_skills_set = [
                                    skill for skill in suggested_skills 
                                    if skill.casefold() not in {s.casefold() for s in self.skills_set}
                                ]
                            # st.rerun()
                # suggested_grid = grid([1, 1, 1])
                for skill in self.generated_skills_set:
                    st.write(skill)
                # with stylable_container(key="custom_skills_button2",
                #             css_styles=suggested_skills_button,
                #     ):
                    # for idx, skill in enumerate(self.generated_skills_set):
                        # y = suggested_grid.button(skill +" :green[+]", key=f"add_skill_{idx}", on_click=skills_callback, args=(idx, skill, ),  type="primary")
                    # st.text_input("Add a skill", key="add_skill_custom", placeholder="Add a skill", label_visibility="collapsed" ,on_change=skills_callback, args=("", "", ),)
                # sst.multiselect(" ", self.generated_skills_set, placeholder="Suggested skills...", on_change=skills_callback,)
        # def skills_callback():
        #     try:
        #         new_skill = st.session_state.add_skill_custom
        #         if new_skill:
        #             # Add only unique items that are not already in the ordered set
        #             if new_skill not in self.skills_set:
        #                 self.skills_set.append(new_skill)
        #                 st.session_state["profile"]["included_skills"]=self.skills_set
        #                 st.session_state["profile_changed"]=True
        #                 st.session_state.add_skill_custom=''
        #     except Exception:
        #             pass
        #     try:
        #         add_skill = st.session_state[f"add_skill_{skill}"]
        #         if add_skill:
        #             if skill not in self.skills_set:
        #                 self.skills_set.append(skill)
        #                 st.session_state["profile"]["included_skills"]=self.skills_set
        #                 st.session_state["profile_changed"]=True
        #             self.generated_skills_set.remove(skill)
        #             st.session_state["profile"]["suggested_skills"]=self.generated_skills_set
        #             # st.session_state["profile"]["suggested_skills"]=[i for i in st.session_state["profile"]["suggested_skills"] if not (i["skill"] == skill)]
        #     except Exception:
        #         pass
        #     try:
        #         remove_skill = st.session_state[f"remove_skill_{skill}"]
        #         if remove_skill:
        #             # print('remove skill', skill)
        #             self.skills_set.remove(skill)
        #             st.session_state["profile"]["included_skills"]=self.skills_set
        #             st.session_state["profile_changed"]=True
        #     except Exception:
        #         pass

        return get_display



    @st.fragment
    def display_field_details(self, field_name, x, field_detail, type):

        """ Interactive display of specific details such as bullet points in each field"""
        @st.fragment
        def get_display():
            
            if x!=-1:
                field_list = st.session_state["profile"][field_name][x][field_detail]
            else:
                field_list = st.session_state["profile"][field_name][field_detail]
            if field_list:
                for idx, value in enumerate(field_list):
                    add_detail(value, idx,)
            if type=="description":
                y, _, _ = st.columns([1, 20, 1])
                with y: 
                    st.button("**:green[+]**", key=f"add_{field_name}_{field_detail}_{x}", on_click=add_new_entry, help="add a description", use_container_width=True)
            elif type=="links":
                y, _, _ = st.columns([1, 20, 1])
                with y: 
                    st.button("**:green[+]**", key=f"add_{field_name}_{field_detail}_{x}", on_click=add_new_entry, help="add a link", use_container_width=True)


        def delete_entry(placeholder, idx):

            try:
                if x!=-1:
                    del st.session_state["profile"][field_name][x][field_detail][idx]
                else:
                    del st.session_state["profile"][field_name][field_detail][idx]
            except Exception:
                pass
            placeholder.empty()

        def move_entry(idx, movement, ):
            if movement=="up":
                if x!=-1:
                    current = st.session_state["profile"][field_name][x][field_detail][idx]
                    try:
                        prev =  st.session_state["profile"][field_name][x][field_detail][idx-1]
                        st.session_state["profile"][field_name][x][field_detail][idx-1] = current
                        st.session_state["profile"][field_name][x][field_detail][idx]=prev
                    except Exception:
                        pass
                else:
                    current = st.session_state["profile"][field_name][field_detail][idx]
                    try:
                        prev =  st.session_state["profile"][field_name][field_detail][idx-1]
                        st.session_state["profile"][field_name][field_detail][idx-1] = current
                        st.session_state["profile"][field_name][field_detail][idx]=prev
                    except Exception:
                        pass
            elif movement=="down":
                if x!=-1:
                    current = st.session_state["profile"][field_name][x][field_detail][idx]
                    try:
                        nxt =  st.session_state["profile"][field_name][x][field_detail][idx+1]
                        st.session_state["profile"][field_name][x][field_detail][idx+1] = current
                        st.session_state["profile"][field_name][x][field_detail][idx]=nxt
                    except Exception:
                        pass
                else:
                    current = st.session_state["profile"][field_name][field_detail][idx]
                    try:
                        nxt =  st.session_state["profile"][field_name][field_detail][idx+1]
                        st.session_state["profile"][field_name][field_detail][idx+1] = current
                        st.session_state["profile"][field_name][field_detail][idx]=nxt
                    except Exception:
                        pass
        
        def add_new_entry():
            # print("added new entry")
            if type=="description":
                if x!=-1:
                    st.session_state["profile"][field_name][x][field_detail].append("")
                else:
                    st.session_state["profile"][field_name][field_detail].append("")
            elif type=="links":
                if x!=-1:
                    st.session_state["profile"][field_name][x][field_detail].append({"display":"","url":""})
                else:
                    st.session_state["profile"][field_name][field_detail].append({"display":"","url":""})

        def add_detail(value, idx,):
            
            placeholder = st.empty()
            if type=="description":
                with placeholder.container():
                    try:
                        c1, c2, c3, c4, x_col = st.columns([1, 20, 1, 1, 1])
                        with c1:
                            st.write("•")
                        with c2: 
                            text = st.text_input(" " , value=value, key=f"descr_{field_name}_{x}_{field_detail}_{idx}", label_visibility="collapsed", on_change=callback, args=(idx, ), )
                        with c3:
                            st.button("**:blue[^]**", type="primary", key=f"up_{field_name}_{x}_{field_detail}_{idx}", on_click=move_entry, args=(idx, "up", ))
                        with c4:
                            st.button(":grey[⌄]", type="primary", key=f"down_{field_name}_{x}_{field_detail}_{idx}", on_click=move_entry, args=(idx, "down", ))
                        with x_col:
                            st.button("**:red[-]**", type="primary", key=f"delete_{field_name}_{x}_{field_detail}_{idx}", on_click=delete_entry, args=(placeholder, idx, ) )
                    except Exception:
                        pass
            elif type=="links":
                with placeholder.container(border=True):
                    try:
                        c1, c2 = st.columns([10, 1])
                        with c2:
                            st.button("**:red[x]**", type="primary", key=f"delete_{field_name}_{x}_{field_detail}_{idx}", on_click=delete_entry, args=(placeholder, idx, ) )
                        url = value["url"] if value["url"] else ""
                        display_name = value["display"] if value["display"] else ""
                        st.text_input("URL", value=url, key=f"{field_name}_{x}_url_{idx}", on_change=callback, args=(idx, ))
                        st.text_input("Display", help = "Display text of URL", value=display_name, key=f"{field_name}_{x}_display_{idx}",on_change=callback, args=(idx, ))
                    except Exception:
                        pass

                   

        def callback(idx, ):
            
            try:
                new_entry = st.session_state[f"descr_{field_name}_{x}_{field_detail}_{idx}"]
                if x!=-1:
                    st.session_state["profile"][field_name][x][field_detail][idx] = new_entry
                else:
                    st.session_state["profile"][field_name][field_detail][idx] = new_entry
            except Exception as e:
                pass
            try:
                url = st.session_state[f"{field_name}_{x}_url_{idx}"]
                if x!=-1:
                    st.session_state["profile"][field_name][x][field_detail][idx]["url"] = url
                else:
                    st.session_state["profile"][field_name][field_detail][idx]["url"] = url
            except Exception as e:
                pass
            try:
                display = st.session_state[f"{field_name}_{x}_display_{idx}"]
                if x!=-1:
                    st.session_state["profile"][field_name][x][field_detail][idx]["display"] = display
                else:
                    st.session_state["profile"][field_name][field_detail][idx]["display"] = display
            except Exception as e:
                pass
            st.session_state["profile_changed"]=True

        return get_display


    @st.fragment  
    def display_field_content(self, name):

        """Interactive display of content of each profile/resume field """
        #TODO: FUTURE USING DRAGGABLE CONTAINERS TO ALLOW REORDER CONTENT https://discuss.streamlit.io/t/draggable-streamlit-containers/72484?u=yueqi_peng
        @st.fragment
        def get_display():

            if st.session_state["profile"][name]:
                for idx, value in enumerate(st.session_state["profile"][name]):
                    add_container(idx, value)
            #NOTE: when first initiated, it'll be None, so add an empty entry to let user see the inputs. however, when user deletes all the entries, it'll become an empty list. 
                    #The below elif statement to check for None only is needed else the last entry cannot be deleted
            elif st.session_state["profile"][name] is None:
                st.session_state["profile"][name]=[]
                add_new_entry()
                add_container(0, st.session_state["profile"][name][0])
                st.session_state["profile_changed"]=True
            st.button("**:green[+]**", key=f"add_{name}_button", on_click=add_new_entry, use_container_width=True)
                  
        def add_new_entry():
            # adds new empty entry to profile dict
            if name=="certifications" or name=="licenses":
                st.session_state["profile"][name].append({"description":[],"issue_date":"", "issue_organization":"", "title":""})
            elif name=="work_experience":
                st.session_state["profile"][name].append({"company":"","description":[],"end_date":"","location":"","start_date":"","title":""})
            elif name=="awards" or name=="qualifications":
                st.session_state["profile"][name].append({"description":[],"title":""})
            elif name=="projects":
                st.session_state["profile"][name].append({"company":"","description":[],"end_date":"","links":[],"location":"","start_date":"", "title":""})
            elif name=="educations":
                st.session_state["profile"][name].append({"coursework":[], "degree":"",  "end_date":"", "gpa":"", "institution":"",  "start_date":"","study":""})
        
        
        
        def delete_container(placeholder, idx):

            #deletes field container
            # print("deleted", st.session_state["profile"][name][idx])
            try:
                del st.session_state["profile"][name][idx]
                placeholder.empty()
            except Exception:
                pass
        
        def move_entry(idx, movement, ):
            if movement=="up":
                current = st.session_state["profile"][name][idx]
                try:
                    prev =  st.session_state["profile"][name][idx-1]
                    st.session_state["profile"][name][idx-1] = current
                    st.session_state["profile"][name][idx]=prev
                except Exception:
                    pass
            elif movement=="down":
                current = st.session_state["profile"][name][idx]
                try:
                    nxt =  st.session_state["profile"][name][idx+1]
                    st.session_state["profile"][name][idx+1] = current
                    st.session_state["profile"][name][idx]=nxt
                except Exception:
                    pass


        def add_container(idx, value):
            
            # adds field container
            placeholder=st.empty()
            with placeholder.container(border=True):
                c1, up, down, x = st.columns([18, 1, 1, 1])
                # with c1:
                #     st.write(f"**{name} {idx}**")
                with up:
                    st.button("**:blue[^]**", type="primary", key=f"up_{name}_{idx}", on_click=move_entry, args=(idx, "up", ))
                with down: 
                    st.button(":grey[⌄]", type="primary", key=f"down_{name}_{idx}", on_click=move_entry, args=(idx, "down", ))
                with x:
                    st.button("**:red[x]**", type="primary", key=f"{name}_delete_{idx}", on_click=delete_container, args=(placeholder, idx) )
                if name=="awards" or name=="qualifications":
                    title = value["title"]
                    # description = value["description"]
                    st.text_input("Title", value=title, key=f"{name}_title_{idx}", on_change=callback, args=(idx, "title", ), placeholder="Title", label_visibility="collapsed")
                    # st.write("Description")
                    get_display= self.display_field_details(name, idx, "description", "description")
                    get_display()
                elif name=="certifications" or name=="licenses":
                    title = value["title"]
                    organization = value["issue_organization"]
                    date = value["issue_date"]
                    # description = value["description"]
                    st.text_input("Title", value=title, key=f"{name}_title_{idx}", on_change=callback, args=(idx, "title", ), placeholder="Title", label_visibility="collapsed")
                    c1, c2=st.columns([1, 1])
                    with c1:
                        st.text_input("Issue organization", value=organization, key=f"{name}_issue_organization_{idx}", on_change=callback, args=(idx, "issue_organization",), placeholder="Issue organization", label_visibility="collapsed")
                    with c2:
                        st.text_input("Issue date", value=date, key=f"{name}_issue_date_{idx}", on_change=callback, args=(idx, "issue_date, "), placeholder="Issue date", label_visibility="collapsed")
                    # st.write("Description")
                    get_display= self.display_field_details(name, idx, "description", "description")
                    get_display()
                elif name=="work_experience":
                    job_title = value["title"]
                    company = value["company"]
                    start_date = value["start_date"]
                    end_date = value["end_date"]
                    location = value["location"]
                    c1, c2, c3= st.columns([2, 1, 1])
                    with c1:
                        st.text_input("Job title", value = job_title, key=f"{name}_title_{idx}", on_change=callback,args=(idx, "title", ),  placeholder="Job title", label_visibility="collapsed")
                        st.text_input("Company", value=company, key=f"{name}_company_{idx}", on_change=callback,args=(idx, "company", ), placeholder="Company", label_visibility="collapsed"  )
                    with c2:
                        st.text_input("start date", value=start_date, key=f"{name}_start_date_{idx}", on_change=callback,args=(idx, "start_date", ), placeholder="Start date", label_visibility="collapsed" )
                        st.text_input("Location", value=location, key=f"{name}_location_{idx}", on_change=callback,  args=(idx, "location", ), placeholder="Location", label_visibility="collapsed" )
                    with c3:
                        st.text_input("End date", value=end_date, key=f"{name}_end_date_{idx}", on_change=callback, args=(idx, "end_date", ), placeholder="End date", label_visibility="collapsed" )
                    # st.write("Description")
                    get_display= self.display_field_details("work_experience", idx, "description", "description")
                    get_display()
                elif name=="projects":
                    project_title = value["title"]
                    company = value["company"]
                    start_date = value["start_date"]
                    end_date = value["end_date"]
                    # descriptions = st.session_state["profile"][name][idx]["description"]
                    location = value["location"]
                    # links =value["links"]
                    location=value["location"]
                    c1, c2, c3= st.columns([2, 1, 1])
                    with c1:
                        st.text_input("Project title", value = project_title, key=f"{name}_title_{idx}", on_change=callback,args=(idx, "title", ),  placeholder="Project title", label_visibility="collapsed")
                        st.text_input("Company", value=company, key=f"{name}_company_{idx}", on_change=callback,args=(idx, "company",), placeholder="Company", label_visibility="collapsed"  )
                    with c2:
                        st.text_input("start date", value=start_date, key=f"{name}_start_date_{idx}", on_change=callback,args=(idx, "start_date", ), placeholder="Start date", label_visibility="collapsed" )
                        st.text_input("Location", value=location, key=f"{name}_location_{idx}", on_change=callback,  args=(idx, "location", ), placeholder="Location", label_visibility="collapsed" )
                    with c3:
                        st.text_input("End date", value=end_date, key=f"{name}_end_date_{idx}", on_change=callback, args=(idx, "end_date", ), placeholder="End date", label_visibility="collapsed" )
                        # st.text_input("Link", value=link, key=f"{name}_link_{idx}", on_change=callback, args=(idx,), placeholder="Project link", label_visibility="collapsed" )
                        with stylable_container(
                            key= f"custom_project_popover",
                            css_styles=
                            f"""
                                button {{
                                    background: none;
                                    border: none;
                                    color: blue;
                                    padding: 0;
                                    cursor: pointer;
                                    font-size: 12px; 
                                    text-decoration: none;
                                }}
                                """,
                        ):
                            with st.popover("Project link",):
                                # url = link["url"] if link["url"] else ""
                                # display_name = link["name"] if link["name"] else ""
                                # st.text_input("url", value=url, key=f"profile_project_url_{idx}", placeholder="url", label_visibility="collapsed")
                                # st.text_input("display name", value=display_name, key=f"profile_project_name_{idx}", placeholder="display name", label_visibility="collapsed")
                                display_details = self.display_field_details("projects", idx, "links", "links") 
                                display_details()
                    # st.write("Description")
                    get_display= self.display_field_details("projects", idx, "description", "description")
                    get_display()
                elif name=="educations":
                    institution = value["institution"]
                    st.text_input("Institution", value=institution, key=f"{name}_institution_{idx}",on_change=callback,  args=(idx, "institution", ), placeholder="Institution", label_visibility="collapsed")
                    degree = value["degree"]
                    st.text_input("Degree", value=degree, key=f"{name}_degree_{idx}", placeholder=f"Degree",on_change=callback,  args=(idx, "degree", ), label_visibility="collapsed")
                    study = value["study"]
                    st.text_input("Area of study", value=study, key=f"{name}_study_{idx}", placeholder="Area of Study", on_change=callback,  args=(idx, "study", ),  label_visibility="collapsed")
                    start_date = value["start_date"]
                    st.text_input("Start date", value=start_date, key=f"{name}_start_date_{idx}", placeholder="Start date", label_visibility="collapsed", on_change=callback,  args=(idx, "start_date",), help="Do not include a date of graduation if it has been more than 10 years ago")
                    end_date = value["end_date"]
                    st.text_input("End date", value=end_date, key=f"{name}_end_date_{idx}", placeholder="End date", label_visibility="collapsed", on_change=callback,  args=(idx, "end_date",), help="Do not include a date of graduation if it has been more than 10 years ago")
                    gpa = value["gpa"]
                    st.text_input("GPA", value=gpa, key=f"{name}_gpa_{idx}", placeholder="GPA", label_visibility="collapsed", on_change=callback, args=(idx, "gpa"),  help="Only include your GPA if it's above 3.5")
                    st.markdown("Course works")
                    display_detail=self.display_field_details("educations", idx, "coursework", "description")
                    display_detail()


        def callback(idx, value):

            try:
                x = st.session_state[f"{name}_{value}_{idx}"]
                st.session_state["profile"][name][idx][value]= x
            except Exception:
                pass
            st.session_state["profile_changed"]=True
            
        return get_display

    # @st.fragment()
    def display_field_analysis(self, field_name, details):

        """ Displays the field-specific analysis UI including evaluation and tailoring """


        def join_with_punctuation(sublist):
            # Function to join words while avoiding extra spaces before punctuation
            result = ""
            for idx, word in enumerate(sublist):
                if not re.match(r'[^\w\s]', word):  # Check if word is not punctuation
                    # result += " "  # Add space only if the next word is not punctuation
                    result += f"{word} "
                else:
                    result = result.rstrip()  # Remove the trailing space before punctuation
                    result += f"{word} " # Append the punctuation without space
            return result.strip()

        def apply_changes():

            if field_name=="summary_objective":
                st.session_state["old_summary"]=st.session_state["profile"]["summary_objective"]
                st.session_state["profile"]["summary_objective"]="".join(st.session_state["new_summary"])
                st.session_state["profile_changed"]=True
            # elif type=="description":
            #     st.session_state[f"old_{field_name}_{idx}"] = st.session_state["profile"][field_name][idx]["description"]
            #     st.session_state["profile"][field_name][idx]["description"]=st.session_state[f"new_{field_name}_{idx}"]
            #     st.session_state["profile_changed"]=True



        def revert_changes():
            if field_name=="summary_objective":
                st.session_state["profile"]["summary_objective"]=st.session_state["old_summary"]
                st.session_state["profile_changed"]=True
            # elif type=="description":
            #     st.session_state["profile"][field_name][idx]["description"]=st.session_state[f"old_{field_name}_{idx}"]
            #     st.session_state["profile_changed"]=True

        def create_annotations(text_list, replaced_words, substitutions):

            # replace replacements with annotation
            for i in range(len(text_list)):
                for j in range(1, len(text_list)-i+1):
                    # substring = " ".join(text_list[i:i+j]).strip()
                    substring = join_with_punctuation(text_list[i:i+j])
                    if substring in replaced_words:
                        idx = replaced_words.index(substring)
                        text_list[i] = (substitutions[idx]+" ", substring)
                        for x in range(i+1, i+j):
                            text_list[x]=""
                        break                 
            return text_list


        _, c0, c1, c2 = st.columns([5, 1, 1, 1])
        with c1:
            # st.markdown(primary_button2, unsafe_allow_html=True)
            # st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
            # NOTE: Skills section doesn't have evaluate option
            if field_name!="included_skills":
                eval_container=st.empty()
                if f"evaluated_{field_name}" in st.session_state or f"readability_{field_name}" in st.session_state:
                    with stylable_container(
                        key= f"eval_{field_name}_popover",
                        css_styles="""
                            button {
                                background: none;
                                border: none;
                                color: #ff8247;
                                padding: 0;
                                cursor: pointer;
                                font-size: 12px; 
                                text-decoration: none;
                            }
                            """,
                    ):
                        with eval_container.popover("Evaluate"):
                            # if f"readability_{field_name}_{idx}" in st.session_state:
                            if st.session_state[f"readability_{field_name}"]:
                                fig = readability_indicator(st.session_state[f"readability_{field_name}"])
                                st.plotly_chart(fig, key=f"readability_{field_name}_plot")
                            if st.session_state[f"evaluated_{field_name}"]:
                                st.write(st.session_state[f"evaluated_{field_name}"])
                            if not st.session_state[f"readability_{field_name}"] and not st.session_state[f"evaluated_{field_name}"]:
                                st.write("please try again")
                            st.markdown(primary_button2, unsafe_allow_html=True)
                            st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
                            st.button("Evaluate again", key=f"eval_again_{field_name}_button",  on_click=self.evaluation_callback, args=(field_name, details, eval_container, ), )
                else:
                    evaluate = eval_container.button("Evaluate",  key=f"eval_{field_name}_button", on_click=self.evaluation_callback, args=(field_name, details, eval_container,), )
        with c2:
            # st.markdown(primary_button2, unsafe_allow_html=True)
            # st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
            tailor_container=st.empty()
            if f"tailored_{field_name}" in st.session_state:
                with stylable_container(
                    key=f"tailor_{field_name}_popover",
                    css_styles="""
                        button {
                            background: none;
                            border: none;
                            color: #ff8247;
                            padding: 0;
                            cursor: pointer;
                            font-size: 12px; 
                            text-decoration: none;
                        }
                        """,
                ):
                    with tailor_container.popover("Tailor"):
                        tailoring = st.session_state[f"tailored_{field_name}"]
                        try:
                            match_eval = tailoring["evaluation"]
                            match_perc = tailoring["percentage"]
                            fig = percentage_comparison(match_perc)
                            st.plotly_chart(fig, use_container_width=True, key="percentage_comparison_plot")
                            st.caption(match_eval)
                        except Exception as e:
                            pass
                        if field_name=="included_skills":
                            if tailoring!="please try again":
                                try:
                                    irrelevant_skills = ", ".join(tailoring.get("irrelevant_skills", ""))
                                    relevant_skills = ", ".join(tailoring.get("relevant_skills", ""))
                                    # transferable_skills= ", ".join(tailoring.get("transferable_skills", ""))
                                    st.write("Here are some tailoring suggestions")
                                    st.write(f"**Skills that can be ranked higher**: {relevant_skills}")
                                    st.write(f"**Skills that can be removed**: {irrelevant_skills}")
                                    # st.write(f"**Skills that can be added**: {transferable_skills}")
                                    st.write("Rearrange and edit your skills for maximum resume-job alignment")
                                except Exception as e:
                                    pass        
                            else:
                                st.write(tailoring)
                        elif field_name=="summary_objective":
                            if tailoring!="please try again":
                                try:
                                # split sentence into words and punctuations
                                    text_list = re.findall(r"[\w']+|[.,!?;]", st.session_state["profile"]["summary_objective"])
                                    replaced_words = [replacement["replaced_words"] for replacement in tailoring["replacements"]]
                                    substitutions = [substitution["substitution"] for substitution in tailoring["replacements"]]
                                    text_list = create_annotations(text_list, replaced_words, substitutions)   
                                    #TODO: for every word followed by a punctuation, there should be a space after the word  
                                    text_list =  [text + " " if not isinstance(text, tuple) and not re.match(r'[^\w\s]', text) else text for text in text_list if text != ""]
                                    st.session_state["new_summary"] = [text[0] if isinstance(text, tuple) else text for text in text_list if text !=""]
                                    # print(text_list)
                                    annotated_text(text_list)
                                    _, c = st.columns([3,1])
                                    with c:
                                        #NOTE: in the future can apply and revert one by one
                                        st.button("apply changes", on_click=apply_changes, key=f"tailor_{field_name}_button"+"_apply")  
                                        if "old_summary" in st.session_state: 
                                            st.button("     revert", on_click=revert_changes, key=f"tailor_{field_name}_button"+"_revert", type="primary")     
                                except Exception as e:
                                    pass
                                    # st.rerun()
                            else:
                                st.write(tailoring)
                        else:
                            # Remove special characters but keep punctuation and dashes
                            tailoring = re.sub(r'[^a-zA-Z0-9\s.,!?-]', '', tailoring)
                            st.write(tailoring)
                        # elif type=="description":
                        #     if tailoring!="please try again" and tailoring!="please add more bullet points first":
                        #         st.write(tailoring)
                        #         # st.write(tailoring["ranked"])
                        #         # if tailoring.get("ranked_list", ""):
                        #         #     st.write(tailoring["ranked_list"])
                        #         #     st.session_state[f"new_{field_name}_{idx}"]=tailoring["ranked_list"]
                        #         #     _, c = st.columns([3,1])
                        #         #     with c:
                        #         #         st.button("apply changes", on_click=apply_changes, key=f"tailor_{field_name}_button_{idx}"+"_apply")  
                        #         #         if f"old_{field_name}_{idx}" in st.session_state: 
                        #         #             st.button("revert", on_click=revert_changes, key=f"tailor_{field_name}_button_{idx}"+"_revert", type="primary")  
                        #     else:
                        #         st.write(tailoring)   
        
                        st.markdown(primary_button2, unsafe_allow_html=True)
                        st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
                        st.button("Tailor again", key=f"tailor_again_{field_name}_button", on_click=self.tailor_callback, args=(field_name, details, tailor_container,))
            else:
                if tailor_container.button("Tailor", key=f"tailor_{field_name}_button", disabled=True if st.session_state["selection"]=="default" else False):
                    if "job_posting_dict" not in st.session_state:
                        self.job_posting_popup(mode="resume", field_name=field_name, field_details=details, tailor_container=tailor_container)
                    else:
                        # if field_name==st.session_state["tailoring_field"] and idx==st.session_state[f"tailoring_field_idx"]:
                        self.tailor_callback(field_name,  details, tailor_container)
                        st.rerun()
                
    
          

    @st.dialog("Job posting")   
    def job_posting_popup(self, mode="resume", field_name="", field_details="", tailor_container=None):

        """ Opens a popup for adding a job posting """

        if mode=="cover_letter":
            st.warning("Please be aware that some organizations may not accept AI generated cover letters. Always research before you apply.")
        st.info("In case a job posting link does not work, please copy and paste the complete job posting content into the box below")
        job_posting_link = st.text_input("Link (required)", key="job_linkx", placeholder="Paste a posting link here", value=None,)
        job_posting_description = st.text_area("Description", 
                                        key="job_descriptionx", 
                                        placeholder="Paste a job description here (optional)",
                                        # on_change=self.form_callback, 
                                        value = None, 
                                        # label_visibility="collapsed",
                                     )
        st.session_state["job_link_disabled"]=False if st.session_state.job_linkx else True
        _, next_col=st.columns([5, 1])
        with next_col:
            submit= st.button("Next", key="job_posting_button", disabled=st.session_state.job_link_disabled)
        if submit:
            if mode=="resume":
                if job_posting_link or job_posting_description:
                    with st.spinner("Processing..."):
                        job_posting = {"job_posting_link": job_posting_link, "job_posting_description":job_posting_description}
                        self.process(job_posting, "job_posting")
                        if "job_description" in st.session_state or "job_posting_path" in st.session_state:
                            if self.initialize_job_posting_callback():
                                # st.session_state["tailoring_field"]=field_name
                                # st.session_state["tailoring_field_idx"]=field_idx
                                st.success("Successfully processed job posting")
                                for field_name in all_fields:
                                    self.delete_session_states([f"tailored_{field_name}", f"evaluated_{field_name}", f"readability_{field_name}"])
                                # st.session_state["init_match"]=match
                                if field_details and tailor_container:
                                    self.tailor_callback(field_name, field_details, tailor_container)
                                st.rerun()
                            else:
                                st.warning("That didin't work.")
                        else:
                            st.warning("That didn't work")
        # st.session_state["info_container"]=st.empty()
        # if st.button("Next", key="job_posting_button", disabled=st.session_state.job_posting_disabled,):
        #     # if "preselection" not in st.session_state:
        #     self.initialize_job_posting_callback()
        #     # starts field tailoring if called to tailor a field
        #     # if mode=="cover_letter":
        #     #     download_path=asyncio_run(lambda: generate_basic_cover_letter(st.session_state["profile"], st.session_state["job_posting_dict"], st.session_state["users_download_path"], ))
        #     #     if download_path:
        #     #         st.session_state["job_posting_dict"].update({"cover_letter_path": download_path})
        #     #         save_user_changes(st.session_state.userId, st.session_state["job_posting_dict"], JobTrackingUsers, lance_tracker_table)
        #     #         with open(download_path, "rb") as file:
        #     #             file_content = file.read()
        #     #         st.download_button(
        #     #             label="Download your cover letter",
        #     #             data=file_content,
        #     #             file_name="cover_letter.docx",  # Specify the default name for the downloaded file
        #     #             mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        #             # )
        #     # starts cover letter generation if called to generate cover letter
        #         # automatic_download(download_path)
        #     # elif mode=="resume" and "tailoring_field" in st.session_state:
        #         # tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"], st.session_state["tailoring_field"])
        #         # tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"],st.session_state["tailoring_field"], st.session_state["tailoring_details"] if "tailoring_details" in st.session_state else None)
        #     st.rerun()

    def initialize_job_posting_callback(self, ):

        try:
            q=queue.Queue()
            job_posting_path = st.session_state.job_posting_path if "job_posting_path" in st.session_state else ""
            job_description = st.session_state.job_description if "job_description" in st.session_state else "" 
            t = threading.Thread(target=create_job_posting_info, args=(job_posting_path, job_description, q, ), daemon=True)
            t.start()
            t.join()
            st.session_state["job_posting_dict"]=q.get()
            match = match_resume_job(st.session_state["profile"]["resume_content"], st.session_state["job_posting_dict"]["content"], " ")
            if match:
                match = match.dict()
                st.session_state["job_posting_dict"].update({"match":match["percentage"]})
            else:
                st.session_state["job_posting_dict"].update({"match":-1})
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            st.session_state["job_posting_dict"].update({"link": st.session_state["posting_link"] if "posting_link" in st.session_state else "", 
                                                         "user_id": st.session_state.userId, 
                                                         "color": "#ff9747", 
                                                         "cover_letter_path": "",
                                                           "applied": False, 
                                                           "time":now, 
                                                           "profile":st.session_state["profile"], 
                                                           "last_edit_time":now})
            save_job_posting_changes(st.session_state.userId, st.session_state["job_posting_dict"], st.session_state["tracker_schema"], lance_tracker_table,)
            st.session_state["tracker"] = retrieve_dict_from_table(st.session_state.userId, lance_tracker_table)
            st.session_state["current_idx"]= len(st.session_state["tracker"])-1
            st.session_state["job_posting_dict"]=st.session_state["tracker"][st.session_state.current_idx]
            st.session_state["tailor_color"] = "#ff9747"
            self.delete_session_states(["job_posting_path", "job_description"])
            return True
        except Exception as e:
            print(e)
            return False


    
    def tailor_callback(self, field_name=None, field_details=None, container=None):
      
        if "job_posting_dict" in st.session_state:
            if field_name:
                # starts specific field tailoring
                p=Progress()
                my_bar = container.progress(0, text=None)
                job_posting = st.session_state["job_posting_dict"]
                response_dict=tailor_resume(st.session_state["profile"], job_posting, field_name, field_details, p=p, loading_func=lambda progress: my_bar.progress(progress, text=f"Tailoring: {progress}%"))
                if response_dict:
                    print(f"successfully tailored {field_name}")
                    st.session_state[f"tailored_{field_name}"]=response_dict
                else:
                    print(f"failed to tailor {field_name}")
                    st.session_state[f"tailored_{field_name}"]="please try again"
                # Ensure the progress bar reaches 100% after the function is complete
                my_bar.progress(100, text="Tailoring Complete!")




    def evaluation_callback(self, field_name=None,  details=None, container=None):

        if field_name:
            # starts specific evaluation of a field
            p=Progress()
             # Create a progress bar
            my_bar = container.progress(0, text=None)
            readability_dict, evaluation = evaluate_resume(resume_dict=st.session_state["profile"], type=field_name, details=details, p=p, loading_func=lambda progress: my_bar.progress(progress, text=f"Evaluating: {progress}%"))
            if readability_dict:
                st.session_state[f"readability_{field_name}"]=readability_dict
            else:
                st.session_state[f"readability_{field_name}"]=None
            if evaluation:
                st.session_state[f"evaluated_{field_name}"]=evaluation
            else:
                st.session_state[f"evaluated_{field_name}"]=None
            # Ensure the progress bar reaches 100% after the function is complete
            my_bar.progress(100, text="Evaluation Complete!")
        else:
            # start general evaluation if there's no saved evaluation 
            if "init_eval" not in st.session_state and st.session_state["evaluation"] is None:
                self.eval_thread = threading.Thread(target=evaluate_resume, args=(st.session_state["profile"], "general", ), daemon=True)
                add_script_run_ctx(self.eval_thread, self.ctx)
                self.eval_thread.start()   
                st.session_state["init_eval"]=True
         
    

    @st.fragment
    def display_profile(self,):

        """Displays interactive user profile UI"""


        def add_field(field, placeholder,):

            label, icon = st.session_state.fields_dict[field]
            with placeholder.expander(label=label, icon=icon):
                _, del_col=st.columns([8, 1])
                with del_col:
                    st.button(":grey[Delete field]", type="primary", key=f"delete_{field}_button", on_click=self.delete_field_popup, args=(field, placeholder, ))
                if field=="contact":
                    if st.session_state["profile"]["contact"] is None:
                        st.session_state["profile"]["contact"]={}
                        st.session_state["profile"]["contact"].update({"city":"", "email": "", "links":[], "name":"", "phone":"", "state":"", })
                        st.session_state["profile_changed"]=True
                    c1, c2, c3=st.columns([1, 1, 1])
                    with c1:
                        name = st.session_state["profile"]["contact"]["name"]
                        if st.text_input("Name", value=name, key="profile_name", placeholder="Name", label_visibility="collapsed")!=name:
                            st.session_state["profile"]["contact"]["name"]=st.session_state.profile_name
                            st.session_state["profile_changed"] = True
                        city = st.session_state["profile"]["contact"]["city"]
                        if st.text_input("City", value=city, key="profile_city", placeholder="City", label_visibility="collapsed")!=city:
                            st.session_state["profile"]["contact"]["city"]=st.session_state.profile_city
                            st.session_state["profile_changed"] = True
                    with c2:
                        email = st.session_state["profile"]["contact"]["email"]
                        if st.text_input("Email", value=email, key="profile_email", placeholder="Email", label_visibility="collapsed")!=email:
                            st.session_state["profile"]["contact"]["email"] = st.session_state.profile_email
                            st.session_state["profile_changed"] = True
                        state = st.session_state["profile"]["contact"]["state"]
                        if st.text_input("State", value=state, key="profile_state", placeholder="State", label_visibility="collapsed")!=state:
                            st.session_state["profile"]["contact"]["state"]=st.session_state.profile_state
                            st.session_state["profile_changed"] = True
                    with c3:
                        phone = st.session_state["profile"]["contact"]["phone"]
                        if st.text_input("Phone", value=phone, key="profile_phone", placeholder="Phone", label_visibility="collapsed")!=phone:
                            st.session_state["profile"]["contact"]["phone"]=st.session_state.profile_phone
                            st.session_state["profile_changed"] = True
                    with stylable_container(
                        key= f"custom_websites_popover",
                        css_styles=
                        f"""
                            button {{
                                background: none;
                                border: none;
                                color: blue;
                                padding: 0;
                                cursor: pointer;
                                font-size: 12px; 
                                text-decoration: none;
                            }}
                            """,
                    ):
                        with st.popover("Personal links",):
                            display_detail=self.display_field_details("contact", -1, "links", "links")
                            display_detail()
                if field=="educations":
                    get_display=self.display_field_content(field)
                    get_display()
                elif field=="summary_objective":  
                    pursuit_jobs = st.session_state["profile"]["pursuit_jobs"]
                    if st.text_input("Pursuing titles", value=pursuit_jobs, key="profile_pursuit_jobs", placeholder="Job titles", label_visibility="collapsed", )!=pursuit_jobs:
                        st.session_state["profile"]["pursuit_jobs"] = st.session_state.profile_pursuit_jobs
                        st.session_state["profile_changed"] = True
                    summary = st.session_state["profile"]["summary_objective"]
                    if summary is None:
                        st.session_state["profile"]["summary_objective"]=" "
                        st.session_state["profile_changed"]=True
                    if st.text_area("Summary", value=summary, key="profile_summary", placeholder="Your summary objective", label_visibility="collapsed")!=summary:
                        # NOTE: this ensures that if text area is cleared, the value of profile summary is never None, else the field won't show up
                        st.session_state["profile"]["summary_objective"] = st.session_state.profile_summary if st.session_state.profile_summary else " "
                        st.session_state["profile_changed"] = True
                    if st.session_state["profile"]["summary_objective"].strip():
                        self.display_field_analysis(field_name="summary_objective", details=st.session_state["profile"]["summary_objective"])
                elif field=="included_skills":
                    suggested_skills = st.session_state["profile"]["suggested_skills"] if st.session_state["profile"]["suggested_skills"] else []
                    self.skills_set= st.session_state["profile"]["included_skills"] if st.session_state["profile"]["included_skills"] else []
                    self.generated_skills_set=  self.generated_skills_set = [
                                    skill for skill in suggested_skills 
                                    if skill.casefold() not in {s.casefold() for s in self.skills_set}
                                ]
                    get_display=self.display_skills()
                    get_display()
                    if st.session_state["profile"]["included_skills"]:
                        self.display_field_analysis(field_name="included_skills", details=st.session_state["profile"]["included_skills"])
                elif field=="work_experience" or field=="projects" or field=="certifications" or field=="awards" or field=="licenses" or field=="qualifications":
                    get_display=self.display_field_content(field)
                    get_display()
                    if st.session_state["profile"][field]:
                        self.display_field_analysis(field_name=field, details=st.session_state["profile"][field])
                elif field=="hobbies":
                    hobbies = st.session_state["profile"]["hobbies"]
                    if hobbies is None:
                        st.session_state["profile"]["hobbies"]={}
                        st.session_state["profile"]["hobbies"].update({"description":[]})
                        st.session_state["profile_changed"]=True
                    get_display=self.display_field_details(field, -1, "description", "description")
                    get_display()
                    # if st.session_state["profile"]["hobbies"] is not None:
                    #     hobbies = ", ".join(st.session_state["profile"]["hobbies"]) 
                    # else:
                    #     hobbies = ""
                    #     st.session_state["profile"]["hobbies"] = []
                    #     st.session_state["profile_changed"] = True
                    # if st.text_area("Hobbies", value=hobbies, key="profile_hobbies", placeholder="Your hobbies, separated by commas", label_visibility="collapsed")!=hobbies:
                    #     st.session_state["profile"]["hobbies"] = st.session_state.profile_hobbies.split(",") if st.session_state.profile_hobbies else []
                    #     st.session_state["profile_changed"] = True
        def job_applied_callback():
            applied = st.session_state["job_applied_toggle"]
            value = {"applied": applied}
            time = st.session_state["job_posting_dict"]["time"]
            st.session_state["job_posting_dict"].update(value)
            save_job_posting_changes(st.session_state.userId, value, st.session_state["tracker_schema"], lance_tracker_table, mode="update", time=time)
            st.session_state["tracker"] = retrieve_dict_from_table(st.session_state.userId, lance_tracker_table)
            if applied:
                print("APPLIED")
                #TODO: balloons not working properly
                # st.balloons()   
        def delete_job_callback():
            timestamp = st.session_state["tracker"][st.session_state.current_idx]["time"]
            delete_job_from_table(st.session_state.userId, timestamp, lance_tracker_table)
            st.session_state["tracker"] = retrieve_dict_from_table(st.session_state.userId, lance_tracker_table)
            if st.session_state["tracker"] is None or len(st.session_state["tracker"])==0:
                self.delete_session_states(["job_posting_dict", "color_picker", "job_applied_toggle"])
            else:
                st.session_state["current_idx"]-=1 if st.session_state.current_idx-1>=0 else 0
                st.session_state["job_posting_dict"]=st.session_state["tracker"][st.session_state.current_idx]            
        def show_hide():
            st.session_state.show = not st.session_state.show
          
        eval_col, profile_col, tailor_col = st.columns([1, 4, 2])   
        # self.save_session_profile()
        with tailor_col:
            selection=sac.segmented(
                   items=[
                        sac.SegmentedItem(label='Edit default'),
                        sac.SegmentedItem(label='Tailor mode'),
                    ], label=' ', align='center', index=1 if st.session_state["selection"]=="tailor" else 0, 
                    color = "#47ff5a",
                )
                      
            if selection=="Edit default" and st.session_state["selection"]!="default":
                # st._config.set_option(f'theme.secondaryBackgroundColor' ,"#5591f5" )
                # st._config.set_option(f'theme.primaryColor' ,"#ff8247" ) 
                st.session_state["selection"]="default"
                # st._config.set_option(f'theme.secondaryBackgroundColor' ,"#ffffff" )
                st._config.set_option(f'theme.textColor' ,"#2d2e29" )
                st._config.set_option(f'theme.primaryColor' ,"#ff9747" )
                st.session_state["profile"] = retrieve_dict_from_table(st.session_state.userId, lance_users_table_default)
                st.rerun()
            elif selection == "Tailor mode" and st.session_state["selection"]!="tailor":  
                 #st._config.set_option(f'theme.backgroundColor' ,"white" )
                # st._config.set_option(f'theme.base' ,"dark" )
                # st._config.set_option(f'theme.primaryColor' ,"#47ff5a" ) 
                if "tailor_color" in st.session_state:
                    # color=change_hex_color(st.session_state["tailor_color"], mode="lighten", percentage=0.5)
                    color = st.session_state["tailor_color"]
                else:
                    color="#ff9747"
                # st._config.set_option(f'theme.secondaryBackgroundColor', color ) 
                st._config.set_option(f'theme.textColor', color )
                st._config.set_option(f'theme.primaryColor' ,color)
                st.session_state["selection"]="tailor"
                if st.session_state["tracker"] is not None and len(st.session_state["tracker"]):
                    st.session_state["profile"] = st.session_state["tracker"][st.session_state.current_idx]["profile"]
                st.rerun()
            prev_col, job_col, nxt_col = st.columns([1, 10, 1])
            job_placeholder=st.empty()
            if st.session_state["selection"]=="tailor":
                with job_placeholder.container():
                    if "job_posting_dict" in st.session_state:
                        with prev_col:
                            add_vertical_space(15)
                            #NOTE: scrolling cannot be callback because need to set config
                            if st.session_state["current_idx"]>0 and len(st.session_state["tracker"])>1:
                                prev = st.button("🞀", key="prev_job_button", )
                                if prev:
                                    st.session_state["current_idx"]=st.session_state["current_idx"]-1
                                    st.session_state["job_posting_dict"] = st.session_state["tracker"][st.session_state.current_idx]
                                    st.session_state["tailor_color"]=st.session_state["job_posting_dict"]["color"]  
                                    # color=change_hex_color(st.session_state["tailor_color"], mode="lighten", percentage=0.5)                    
                                    # st._config.set_option(f'theme.secondaryBackgroundColor' , color)
                                    st._config.set_option(f'theme.textColor' ,st.session_state.tailor_color )
                                    st._config.set_option(f'theme.primaryColor' ,st.session_state.tailor_color) 
                                    st.session_state["profile"] = st.session_state["tracker"][st.session_state.current_idx]["profile"]
                                    st.rerun()
                        with nxt_col:
                            add_vertical_space(15)
                            if st.session_state["current_idx"]<len(st.session_state["tracker"])-1 and len(st.session_state["tracker"])>1:
                                nxt = st.button("🞂", key="next_job_button",)     
                                if nxt:
                                    st.session_state["current_idx"]=st.session_state["current_idx"]+1
                                    st.session_state["job_posting_dict"] = st.session_state["tracker"][st.session_state.current_idx]
                                    st.session_state["tailor_color"]=st.session_state["job_posting_dict"]["color"]
                                    # color=change_hex_color(st.session_state["tailor_color"], mode="lighten", percentage=0.5)
                                    # st._config.set_option(f'theme.secondaryBackgroundColor' , color) 
                                    st._config.set_option(f'theme.textColor' ,st.session_state.tailor_color )
                                    st._config.set_option(f'theme.primaryColor' ,st.session_state.tailor_color) 
                                    st.session_state["profile"] = st.session_state["tracker"][st.session_state.current_idx]["profile"]
                                    st.rerun()
                        with job_col:
                            # job_posting_container=st.empty()
                            # with job_posting_container.container(border=True): 
                            with stylable_container(
                                key="job_clip_note_container",
                            css_styles = """
                                    {
                                        border: 1px solid rgba(49, 51, 63, 0.2);
                                        border-radius: 0; /* Remove the rounded corners */
                                        padding: calc(1em + 1px);
                                        background: #FFFF88;
                                        width: 100%; /* Set the width to prevent text sticking out */
                                        overflow-wrap: break-word; /* Ensure long words break correctly */
                                        box-shadow: 4px 4px 10px rgba(0, 0, 0, 0.1); /* Add shadow around the outline */
                                    }
                                """,
                            ):
                                job_title = st.session_state["job_posting_dict"].get('job', "")
                                company = st.session_state["job_posting_dict"].get("company", "")
                                about = st.session_state["job_posting_dict"].get("about_job", "")
                                link = st.session_state["job_posting_dict"].get("link", "")
                                match = st.session_state["job_posting_dict"].get("match", "")
                                skills_keywords = st.session_state["job_posting_dict"].get("skills_keywords", "")
                                experience_keywords = st.session_state["job_posting_dict"].get("experience_keywords", "")
                                salary = st.session_state["job_posting_dict"].get("salary", "")
                                location = st.session_state["job_posting_dict"].get("location", "")
                                c1, c2, c3, c4=st.columns([4, 1, 1, 1])
                                with c1:
                                    st.write("📌 ")
                                    # title = f'<p style="font-family:Comic Sans MS, cursive; color:#2d2e29; font-size: 20px;"><b><i>Clipped Jobs</i></b></p>'
                                    # st.markdown(title, unsafe_allow_html=True)
                                with c3:
                                    if link:
                                        st.link_button("🔗", url=link)
                                with c2:
                                    change_color = st.color_picker("pick a color", value = st.session_state.tailor_color if "tailor_color" in st.session_state else "#ff9747", key="color_picker", label_visibility="collapsed")
                                    #NOTE: resetting config does not work in callback
                                    if change_color!=st.session_state["tailor_color"]:
                                        st.session_state["tailor_color"]= st.session_state.color_picker
                                        time=st.session_state["tracker"][st.session_state.current_idx]["time"]
                                        save_job_posting_changes(st.session_state.userId, {"color":st.session_state["tailor_color"]}, st.session_state["tracker_schema"], lance_tracker_table, mode="update", time=time)
                                        st.session_state["tracker"] = retrieve_dict_from_table(st.session_state.userId, lance_tracker_table)
                                        # color=change_hex_color(st.session_state["tailor_color"], mode="lighten", percentage=0.5)
                                        # st._config.set_option(f'theme.secondaryBackgroundColor' , color )
                                        st._config.set_option(f'theme.textColor' ,st.session_state.tailor_color )
                                        st._config.set_option(f'theme.primaryColor' ,st.session_state.tailor_color) 
                                        st.rerun()
                                with c4:
                                    st.button("X", key="delete_job_button", on_click=delete_job_callback)
                                if job_title:
                                    st.write(f"**Job**: {job_title}")
                                    # text = f'<p style="font-family:Segoe UI, sans-serif; color:#2d2e29; font-size: 16spx;">Job: {job_title}</p>'
                                    # st.markdown(text, unsafe_allow_html=True)
                                if company:
                                    st.write(f"**Company**: {company}")
                                    # text = f'<p style="font-family:Segoe UI, sans-serif; color:#2d2e29; font-size: 16spx;">Company: {company}</p>'
                                    # st.markdown(text, unsafe_allow_html=True)
                                if about:
                                    st.write(f"**Summary**: {about}")
                                    # text = f'<p style="font-family:Segoe UI, sans-serif; color:#2d2e29; font-size: 16spx;">Summary: {about}</p>'
                                    # st.markdown(text, unsafe_allow_html=True)
                                if salary:
                                    st.write(f"**Salary**: {salary}")
                                    # text = f'<p style="font-family:Segoe UI, sans-serif; color:#2d2e29; font-size: 16spx;">Salary: {salary}</p>'
                                    # st.markdown(text, unsafe_allow_html=True)
                                if location:
                                    st.write(f"**Location**: {location}")
                                    # text = f'<p style="font-family:Segoe UI, sans-serif; color:#2d2e29; font-size: 16spx;">Location: {location}</p>'
                                    # st.markdown(text, unsafe_allow_html=True)
                                if skills_keywords:
                                    # text = f'<p style="font-family:Segoe UI, sans-serif; color:#2d2e29; font-size: 16spx;">ATS skills keywords:</p>'
                                    # st.markdown(text, unsafe_allow_html=True)
                                    keywords = ", ".join(skills_keywords)
                                    # color = st.session_state["tailor_color"] if st.session_state["tailor_color"]!="#ffffff" else "#2d2e29"
                                    # color = change_hex_color(color, mode="darken")
                                    # keywords_display = f'<p style="font-family:Segoe UI, sans-serif; color:{color}; font-size: 16spx;">{keywords}</p>'
                                    # st.markdown(keywords_display, unsafe_allow_html=True)
                                    st.write(f"**ATS skills keywords**: {keywords}")
                                if experience_keywords:
                                    # text = f'<p style="font-family:Segoe UI, sans-serif; color:#2d2e29; font-size: 16spx;">ATS experience keywords:</p>'
                                    # st.markdown(text, unsafe_allow_html=True)
                                    keywords = ", ".join(experience_keywords)
                                    # color = st.session_state["tailor_color"] if st.session_state["tailor_color"]!="#ffffff" else "#2d2e29"
                                    # color = change_hex_color(color, mode="darken", percentage=0.5)
                                    # keywords_display = f'<p style="font-family:Segoe UI, sans-serif; color:{color}; font-size: 16spx;">{keywords}</p>'
                                    # st.markdown(keywords_display, unsafe_allow_html=True)
                                    st.write(f"**ATS experience keywords**: {keywords}")
                                if match:
                                    # text = f'<p style="font-family:Segoe UI, sans-serif; color:#2d2e29; font-size: 16spx;">Match:</p>'
                                    # st.markdown(text, unsafe_allow_html=True)
                                    if match<=50:
                                        st.write(f"**Match score**: :red[{match}%]")
                                    elif 50<match<70:
                                        st.write(f"**Match score**: :orange[{match}%]")
                                    else:
                                        st.write(f"**Match score**: : :green[{match}%]")
                                applied = st.toggle("**Applied**", key="job_applied_toggle", 
                                                    value=st.session_state["job_posting_dict"]["applied"], 
                                                    on_change=job_applied_callback)
                    _, job_upload_col, _=st.columns([1, 3, 1])
                    with job_upload_col:
                        with stylable_container(key="custom_button1_profile1",
                                        css_styles=new_upload_button
                                ):
                            if st.button("Upload a new job posting", key="new_job_posting_button", use_container_width=True):
                                self.job_posting_popup(mode="resume")
            else:
                job_placeholder.empty()

    
        # general evaluation column
        # with eval_col:
        #     if st.session_state["profile"]["resume_content"]!="":
        #         self.display_general_evaluation()
        #         self.evaluation_callback()
        # the main profile column
        with profile_col:
            # c1, c2 = st.columns([1, 1])
            # with c1:
            #     with st.expander(label="Contact", icon=":material/contacts:"):
            #         name = st.session_state["profile"]["contact"]["name"]
            #         if st.text_input("Name", value=name, key="profile_name", placeholder="Name", label_visibility="collapsed")!=name:
            #             st.session_state["profile"]["contact"]["name"]=st.session_state.profile_name
            #             st.session_state["profile_changed"] = True
            #         email = st.session_state["profile"]["contact"]["email"]
            #         if st.text_input("Email", value=email, key="profile_email", placeholder="Email", label_visibility="collapsed")!=email:
            #             st.session_state["profile"]["contact"]["email"] = st.session_state.profile_email
            #             st.session_state["profile_changed"] = True
            #         phone = st.session_state["profile"]["contact"]["phone"]
            #         if st.text_input("Phone", value=phone, key="profile_phone", placeholder="Phone", label_visibility="collapsed")!=phone:
            #             st.session_state["profile"]["contact"]["phone"]=st.session_state.profile_phone
            #             st.session_state["profile_changed"] = True
            #         city = st.session_state["profile"]["contact"]["city"]
            #         if st.text_input("City", value=city, key="profile_city", placeholder="City", label_visibility="collapsed")!=city:
            #             st.session_state["profile"]["contact"]["city"]=st.session_state.profile_city
            #             st.session_state["profile_changed"] = True
            #         state = st.session_state["profile"]["contact"]["state"]
            #         if st.text_input("State", value=state, key="profile_state", placeholder="State", label_visibility="collapsed")!=state:
            #             st.session_state["profile"]["contact"]["state"]=st.session_state.profile_state
            #             st.session_state["profile_changed"] = True
            #         # linkedin = st.session_state["profile"]["contact"]["linkedin"]
            #         # if st.text_input("Linkedin", value=linkedin, key="profile_linkedin", placeholder="Linkedin", label_visibility="collapsed")!=linkedin:
            #         #     st.session_state["profile"]["contact"]["linkedin"]=st.session_state.profile_linkedin
            #         #     st.session_state["profile_changed"] = True
            #         # linkedin = st.session_state["profile"]["contact"]["linkedin"]
            #         # color = st.session_state.tailor_color if "tailor_color" in st.session_state else "#2d2e29"
            #         with stylable_container(
            #             key= f"custom_websites_popover",
            #             css_styles=
            #             f"""
            #                 button {{
            #                     background: none;
            #                     border: none;
            #                     color: blue;
            #                     padding: 0;
            #                     cursor: pointer;
            #                     font-size: 12px; 
            #                     text-decoration: none;
            #                 }}
            #                 """,
            #         ):
            #             with st.popover("Personal links",):
            #                 display_detail=self.display_field_details("contact", -1, "links", "links")
            #                 display_detail()
                            # if linkedin:
                            #     with st.container(border=True):
                            #         url = linkedin["url"] if linkedin["url"] else ""
                            #         if st.text_input("url", value=url, key="profile_linkedin_url", placeholder="url", label_visibility="collapsed")!=url:
                            #             st.session_state["profile"]["contact"]["linkedin"]["url"]=st.session_state.profile_linkedin_url
                            #             st.session_state["profile_changed"] = True
                            #         name = linkedin["name"] if linkedin["name"] else ""
                            #         if st.text_input("display name", value=name, key="profile_linkedin_name", placeholder="display name", label_visibility="collapsed")!=name:
                            #             st.session_state["profile"]["contact"]["linkedin"]["name"]=st.session_state.profile_linkedin_name
                            #             st.session_state["profile_changed"] = True
                            

                    # websites = st.session_state["profile"]["contact"]["websites"]
                    # if st.text_input("Other websites", value=websites, key="profile_websites", placeholder="Other websites, separate each by a comma", label_visibility="collapsed")!=websites:
                    #     st.session_state["profile"]["contact"]["websites"]=st.session_state.profile_websites
                    #     st.session_state["profile_changed"] = True
            for field in st.session_state.fields_dict:
                if field not in st.session_state.additional_fields:
                    placeholder=st.empty()
                    add_field(field, placeholder)
            # if "summary_objective" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("summary_objective", placeholder)
            # if "work_experience" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("work_experience", placeholder)
            # if "included_skills" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("included_skills", placeholder)
            # if "qualifications" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("qualifications", placeholder)
            # if "projects" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("projects", placeholder)
            # if "certifications" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("certifications", placeholder)
            # if "awards" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("awards", placeholder)
            # if "licenses" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("licenses", placeholder)
            # if "hobbies" not in st.session_state["additional_fields"]:
            #     placeholder=st.empty()
            #     add_field("hobbies", placeholder)
            #TODO, allow custom fields with custom field details such as bullet points, dates, links, etc. 
            # placeholder=st.empty()
            if st.session_state["additional_fields"]:
                st.button("Add a field", key="add_field_button", use_container_width=True, on_click=show_hide, )
                #NOTE: below cannot be added to callback probably becauese it's adding buttons
                if st.session_state.show:
                    with st.container(border=True):
                        fields_grid = grid([1, 1, 1], vertical_align="center" )
                        for field in st.session_state["additional_fields"]:
                            label, icon = st.session_state.fields_dict[field]
                            # if f"{field}_add_button" not in st.session_state:
                            if fields_grid.button(label=label, key=f"{field}_add_button", icon=icon):
                                st.session_state["additional_fields"].remove(field)
                                st.rerun()
            st.divider()
        # the menu container
            _, menu_col, _ = st.columns([1, 1, 1])   
            with menu_col:
                upload_resume_placeholder=st.empty()
                if st.session_state["selection"]=="default":
                    with upload_resume_placeholder.container():
                        with stylable_container(key="custom_button1_profile1",
                                    css_styles=new_upload_button
                            ):
                            if st.button("Upload a new resume", key="new_resume_button", use_container_width=True):
                                # NOTE:cannot be in callback because streamlit dialogs are not supported in callbacks
                                self.delete_profile_popup()
                else:
                    upload_resume_placeholder.empty()



 


    @st.dialog("Warning")   
    def delete_field_popup(self, field, placeholder):
        add_vertical_space(2)
        name, icon = st.session_state.fields_dict[field]
        st.warning(f"You're about to delete the field **{name}** from your profile. Are you sure?")
        add_vertical_space(2)
        _, c = st.columns([5, 1])
        with c:
            if st.button("Confirm", type="primary"):
                st.session_state["additional_fields"].append(field)
                st.session_state["profile"][field]=None
                st.session_state["profile_changed"]=True
                placeholder.empty()
                st.rerun()


    
    @st.fragment(run_every=st.session_state["eval_rerun_timer"])
    def display_general_evaluation(self,):

        """ Displays the general evaluation result of the profile """


        # NOTE: evaluation either comes from table or from backend function
        try:
            finished = st.session_state["evaluation"]["finished"]
            if finished and st.session_state["eval_rerun_timer"]:
                st.session_state["evaluation"].update({"user_id":st.session_state.userId})
                st.session_state["eval_rerun_timer"]=None
                save_user_changes(st.session_state.userId, st.session_state["evaluation"], st.session_state["evaluation_schema"], lance_eval_table)
                st.rerun()      
        except Exception:
            finished=False

        if st.session_state["evaluation"]:
                with st.expander("Show my profile report", expanded=True):
                    # c1, c2=st.columns([1, 1])
                    # with c1:
                    st.divider()
                    st.write("**Length**")
                    try:
                        length=int(st.session_state["evaluation"]["word_count"])
                        # st.write("Your resume length is: ")
                        if length<300:
                            st.subheader(":red[too short]")
                        elif length>=300 and length<450:
                            st.subheader(":green[good]")
                        elif length>=450 and length<=600:
                            st.subheader(":green[great]")
                        elif length>600 and length<800:
                            st.subheader(":blue[good]")
                        else:
                            st.subheader(":red[too long]")
                        st.caption(f"A good resume length is between 475 and 600 words, yours is around {str(length)} words.")
                        # pages=st.session_state["evaluation"]["page_count"]
                        # fig = length_chart(int(length))
                        # st.plotly_chart(fig, 
                        #                 # use_container_width=True
                        #                 )
                    except Exception:
                        if finished is False:
                            st.write("Evaluating...")
                # with c2: 
                    st.divider()
                    st.write("**Formatting**")
                    try:
                        # add_vertical_space(1)
                        ideal_type = st.session_state["evaluation"]["ideal_type"]
                        st.write("The ideal type for your resume is:")
                        if ideal_type=="chronological":
                            st.subheader(":green[chronological]")
                        elif ideal_type=="functional":
                            st.subheader(":blue[functional]")
                        # resume_type=st.session_state["evaluation"]["resume_type"]
                        # if ideal_type==resume_type:
                        #     st.subheader(":green[Good]")
                        #     st.write(f"The best type of resume for you is **{ideal_type}** and your resume is also **{resume_type}**")
                        # else:
                        #     st.subheader(":red[Mismatch]")
                        #     st.write(f"The best type of resume for you is **{ideal_type}** but your resume seems to be **{resume_type}**")
                        if not st.session_state["eval_rerun_timer"]:
                            add_vertical_space(1)
                            if st.button("What are the different formats?", type="primary", key="resume_type_button"):
                                self.resume_type_popup()
                            # add_vertical_space(1)
                            # if st.button("Explore template options", key="resume_template_explore_button"):
                            #     self.explore_template_popup()
                    except Exception:
                        if finished is False:
                            st.write("Evaluating...")
                    st.divider()
                    st.write("**Language**")
                    try:
                        categories=["syntax", "tone", "readability"]
                        language_data=[]
                        for category in categories:
                            language_data.append({category:st.session_state["evaluation"][category]})
                        with st.container():
                            fig = language_radar(language_data)
                            st.plotly_chart(fig, use_container_width=True, key="language_radar_plot")
                            st.caption("Tone: keep a formal and respectful tone")
                            st.caption("Syntax: use power verbs and an active voice")
                            st.caption("Readability: vary your sentence lengths and word syllables")
                        # st.scatter_chart(df)
                    except Exception:
                        if finished is False:
                            st.write("Evaluating...")
                    # st.write("**How does your resume compare to others?**")
                    # try:
                    #     section_names = ["objective", "work_experience", "skillsets"]
                    #     comparison_data = []
                    #     for section in section_names:
                    #         comparison_data.append({section:st.session_state["evaluation"][section]})
                    #     fig = comparison_chart(comparison_data)
                    #     st.plotly_chart(fig)
                    # except Exception:
                    #     if finished is False:
                    #         st.write("Evaluating...")
                    # st.write("**Impression**")
                    # try:
                    #     impression = st.session_state["evaluation"]["impression"]
                    #     st.write(impression)
                    # except Exception:
                    #     if finished is False:
                    #         st.write("Evaluating...")
                    st.markdown(primary_button2, unsafe_allow_html=True)
                    st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
                    if st.button("Refresh", key=f"general_eval_refresh_button", ):    
                        delete_user_from_table(st.session_state.userId, lance_eval_table)
                        self.delete_session_states(["evaluation","init_eval"])
                        # reset evaluation rerun timer
                        st.session_state["eval_rerun_timer"]=3
                        st.rerun()
                        # elif button_name=="stop evaluation":s
                        #     try:
                        #         # kill the evaluation thread 
                        #         self.eval_thread.kill()
                        #         self.eval_thread.join()
                        #     except Exception as e:
                        #         print(e)
                        #         pass
                        #     finally:
                        #         # stop timer and finished evaluation
                        #         st.session_state["eval_rerun_timer"] = None
                        #         st.session_state["finished_eval"] = True
                        #         st.rerun()


    @st.dialog(" ")
    def resume_type_popup(self, ):
        add_vertical_space(4)
        st.image("./resources/functional_chronological_resume.png")



    @st.fragment(run_every=1)
    def save_session_profile(self,):

        """ Saves profile into lancedb table periodically if there's change """
        
        if "profile_changed" in st.session_state and st.session_state["profile_changed"]:
            if st.session_state["selection"]=="default": 
                print('Changed for default profile, saving user changes')
                save_user_changes(st.session_state.userId, st.session_state.profile, st.session_state["profile_schema"], lance_users_table_default, convert_content=True)
            # save_user_changes(st.session_state.userId, st.session_state.profile, st.session_state["profile_schema"], lance_users_table_tailored, convert_content=True)
            elif st.session_state["selection"]=="tailor" and st.session_state["tracker"] is not None and len(st.session_state["tracker"])>0:
                print("Saving tailoring profile")
                time=st.session_state["tracker"][st.session_state.current_idx]["time"]
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                st.session_state["tracker"][st.session_state.current_idx].update({"profile": st.session_state["profile"], "last_edit_time":now})
                save_job_posting_changes(st.session_state.userId, st.session_state["tracker"][st.session_state.current_idx], st.session_state["tracker_schema"], lance_tracker_table, mode="upsert", time=time)
            st.session_state["profile_changed"]=False
            st.session_state["update_template"]=True


    @st.dialog("Warning")
    def delete_profile_popup(self):

        """ Opens a popup that warns user before uploading a new resume """

        add_vertical_space(2)
        st.warning("You are about to delete your current profile. Are you sure?")
        add_vertical_space(2)
        c1, _, c2 = st.columns([1, 1, 1])
        with c2:
            if st.button("yes, I'll upload a new resume", type="primary", ):
                delete_user_from_table(st.session_state.userId, lance_users_table_default)
                # delete_user_from_table(st.session_state.userId, lance_users_table_tailored)
                delete_user_from_table(st.session_state.userId, lance_eval_table)
                 # delete session-specific copy of the profile and evaluation
                self.delete_session_states(["profile", "evaluation", "init_eval", "init_templates"])
                profile_placeholder.empty()
                st.rerun()
    
    def delete_session_states(self, names:List[str])->None:

        """ Helper function to clean up session state"""

        for name in names:
            try:
                del st.session_state[name]
            except Exception:
                pass
    # def get_current_page(self, ):
    #     try:
    #         current_page = pages[ctx.page_script_hash]
    #     except KeyError:
    #         current_page = [
    #             p for p in pages.values() if p["relative_page_hash"] == ctx.page_script_hash
    #         ][0]
    #     print("Current page:", current_page)
    #     return current_page

    #NOTE: this has to be here instead of templates.py because switching from templates makes run every seceonds stop
    # @st.fragment(run_every=30)
    # def reformat_templates(self, ):

    #     """ Runs the resume templates update every x seconds in the background. """

    #     if ("init_formatting" not in st.session_state) and (("formatted_docx_paths" not in st.session_state or "formatted_pdf_paths" not in st.session_state) or ("update_template" in st.session_state and st.session_state["update_template"])):
    #         print("REFORMATING")
    #         try:
    #             # prevents going through this loop while already formatting
    #             st.session_state["init_formatting"]=True
    #             template_paths = list_files(template_path, ext=".docx")
    #             with Pool() as pool:
    #                 st.session_state["formatted_docx_paths"] = pool.map(reformat_resume, template_paths)
    #                 # if st.session_state["current_page"] == "template":  # Define your stopping condition
    #                 #     pool.terminate()  # Stop all processes immediately
    #                 #     st.stop()  # Optionally stop Streamlit execution
    #             if st.session_state["formatted_docx_paths"]:
    #                     with Pool() as pool:
    #                         result  = pool.map(convert_docx_to_img, st.session_state["formatted_docx_paths"])
    #                         st.session_state["image_paths"], st.session_state["formatted_pdf_paths"] = zip(*result)
    #                         st.session_state["image_paths"] = [sorted(paths) for paths in st.session_state["image_paths"] if paths]
    #                 # with Pool() as pool:
    #                 #     st.session_state["formatted_pdf_paths"] = pool.map(convert_doc_to_pdf, st.session_state["formatted_docx_paths"])
    #                     # if st.session_state["current_page"] == "template":  # Define your stopping condition
    #                     #     pool.terminate()  # Stop all processes immediately
    #                     #     st.stop()  # Optionally stop Streamlit execution
    #             try:
    #                 st.session_state["update_template"]=False
    #                 self.delete_session_states(["init_formatting"])
    #             except Exception:
    #                 pass
    #         except Exception as e:
    #             st.session_state["update_template"]=False
    #             print(e)
    #     else:
    #         print("Skip reformatting templates")



if __name__ == '__main__':
    
    user=User()
    


