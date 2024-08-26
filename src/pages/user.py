from streamlit_extras.add_vertical_space import add_vertical_space
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities import RegisterError
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from utils.cookie_manager import CookieManager
import time
from datetime import datetime, timedelta, date
from utils.lancedb_utils import add_to_lancedb_table, retrieve_dict_from_table, delete_user_from_table, save_user_changes, convert_pydantic_schema_to_arrow

# from utils.lancedb_utils_async import add_to_lancedb_table, retrieve_dict_from_table, delete_user_from_table, save_user_changes, convert_pydantic_schema_to_arrow
from utils.common_utils import  create_profile_summary, process_uploads, create_resume_info, process_links, process_inputs, create_job_posting_info, grammar_checker
from utils.basic_utils import mk_dirs, send_recovery_email, write_file
from typing import Any, List
import uuid
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from utils.aws_manager import get_client
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import webbrowser
from utils.pydantic_schema import ResumeUsers, GeneralEvaluation, JobTrackingUsers
from streamlit_utils import nav_to, user_menu, progress_bar, set_streamlit_page_config_once, length_chart, comparison_chart, language_radar, readability_indicator, automatic_download
from css.streamlit_css import general_button, primary_button3, google_button, primary_button2, primary_button
from backend.upgrade_resume import tailor_resume, evaluate_resume,  readability_checker
from backend.generate_cover_letter import generate_basic_cover_letter
# from streamlit_float import *
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from st_pages import get_pages, get_script_run_ctx 
from streamlit_extras.stylable_container import stylable_container
from annotated_text import annotated_text
from st_draggable_list import DraggableList
from streamlit_extras.grid import grid
import requests
# from apscheduler.schedulers.background import BackgroundScheduler
from utils.async_utils import thread_with_trace, asyncio_run
import re
import queue
# import streamlit_antd_components as sac
#NOTE: below import is necessary for nested column fix, do not delete
import streamlit_nested_layout 
import streamlit as st


set_streamlit_page_config_once()

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

STORAGE = os.environ['STORAGE']
if STORAGE=="CLOUD":
    login_file = os.environ["S3_LOGIN_FILE_PATH"]
    db_path=os.environ["S3_LANCEDB_PATH"]
    client_secret_json = os.environ["CLOUD_CLIENT_SECRET_JSON"]
    base_uri = os.environ["PRODUCTION_BASE_URI"]
elif STORAGE=="LOCAL":
    login_file = os.environ["LOGIN_FILE_PATH"]
    db_path=os.environ["LANCEDB_PATH"]
    client_secret_json = os.environ["CLIENT_SECRET_JSON"]
    base_uri = os.environ["BASE_URI"]
user_profile_file=os.environ["USER_PROFILE_FILE"]
lance_eval_table = os.environ["LANCE_EVAL_TABLE"]
lance_users_table = os.environ["LANCE_USERS_TABLE"]
lance_tracker_table = os.environ["LANCE_TRACKER_TABLE"]
placeholder=st.empty()
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

class User():

    ctx = get_script_run_ctx()

    def __init__(self, ):


        # set current page for progress bar
        st.session_state["current_page"] = "profile"
        # NOTE: userId is retrieved from browser cookie
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId(max_retries=3, delay=1)
        time.sleep(3)
        self._init_session_states()
        self._init_display()

    # @st.cache_data()
    def _init_session_states(_self, ):


        # Open users login file
        if "authenticator" not in st.session_state:
            with open(login_file) as file:
                st.session_state["config"] = yaml.load(file, Loader=SafeLoader)
            st.session_state["authenticator"] = stauth.Authenticate( st.session_state.config['credentials'], st.session_state.config['cookie']['name'], st.session_state.config['cookie']['key'], st.session_state.config['cookie']['expiry_days'], st.session_state.config['preauthorized'] )
        # Open users profile file
        # with open(user_profile_file, 'r') as file:
        #     try:
        #         users = json.load(file)
        #         # Convert the single object into a list of objects if it's not already
        #         if not isinstance(users, list):
        #             users = [users]
        #         st.session_state["users"] = users
        #         st.session_state["users_dict"] = {user['userId']: user for user in st.session_state.users}
        #     except JSONDecodeError:
        #         raise 
            

        if _self.userId is not None:
            if "user_mode" not in st.session_state:
                st.session_state["user_mode"]="signedin"
            if "profile" not in st.session_state:
                st.session_state["profile"]= retrieve_dict_from_table(_self.userId, lance_users_table)
                # scheduler = BackgroundScheduler()
                # scheduler.add_job(_self.save_session_profile, 'interval', seconds=5, )
                # scheduler.start()
            if "evaluation" not in st.session_state:
                st.session_state["evaluation"] = retrieve_dict_from_table(_self.userId, lance_eval_table)
            if "tracker" not in st.session_state:
                st.session_state["tracker"] = retrieve_dict_from_table(_self.userId, lance_tracker_table)
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
                paths=[st.session_state["users_upload_path"], st.session_state["users_download_path"]]
                mk_dirs(paths,)
            if "freeze" not in st.session_state:
                st.session_state["freeze"]=False
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
            user_menu(self.userId, page="profile")
            # st.logo("./resources/logo_acareerai.png")
        if st.session_state.user_mode=="signup":
            print("signing up")
            self.sign_up()
        elif st.session_state.user_mode=="signedin":
            print("signed in")
            if "redirect_page" in st.session_state:
                st.switch_page(st.session_state.redirect_page)
            else:
                try:
                    if not st.session_state["profile"]:
                        print("user profile does not exists yet")
                        # ask user for their resumes
                        self.initialize_resume()
                    else:
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
            print("signed out")
            self.sign_in()
        elif st.session_state.user_mode=="signout":
            self.sign_out()
        # elif st.session_state.user_mode=="reset_password":
        #     self.reset_password()

          
    


    

    def sign_out(self, ):

        print('signing out')
        #NOTE: can't get authenticator logout to delete cookies so manually doing it with the cookie manager wrapper class
        # also needs to manually delete cookies for google login case
        st.session_state.cm.delete_cookie()
        try:
            # still needs the logout code since the authenticators need to be cleared
            st.session_state.authenticator.logout(location="unrendered")
            # self.google_signout()
        except Exception:
            pass
        st.session_state["user_mode"]="signedout"
        time.sleep(5)
        if "redirect_page" in st.session_state:
            st.switch_page(st.session_state.redirect_page)
        else:
            st.rerun()



    def sign_in(self, ):

        _, c1, _ = st.columns([1, 1, 1])
        with c1:
            with st.container(border=True):
                # st.markdown("<h1 style='text-align: center; color: #2d2e29;'>Welcome to ACAI</h1>", unsafe_allow_html=True)
                st.image("./resources/logo_acareerai.png")
                # self.google_signin()
                # add_vertical_space(1)
                # sac.divider(label='or',  align='center', color='gray')
                # st.divider()
                name, authentication_status, username = st.session_state.authenticator.login()
                placeholder_error = st.empty()
                signup_col, forgot_password_col, forgot_username_col = st.columns([4, 1, 1])
                with signup_col:
                    add_vertical_space(2)
                    sign_up = st.button(label="Sign up", key="signup",  type="primary")
                    if sign_up:
                        st.session_state["user_mode"]="signup"
                        st.rerun()
                with forgot_password_col:
                    st.markdown(primary_button3, unsafe_allow_html=True)
                    st.markdown('<span class="primary-button3"></span>', unsafe_allow_html=True)
                    if st.button(label="forgot my password", key="forgot_password", ):
                        self.recover_password_username_popup(type="password")
                with forgot_username_col:
                    st.markdown(primary_button3, unsafe_allow_html=True)
                    st.markdown('<span class="primary-button3"></span>', unsafe_allow_html=True)
                    if st.button(label="forgot my username", key="forgot_username",):
                        self.recover_password_username_popup(type="username")
                # print(name, authentication_status, username)
                if authentication_status:
                    # email = st.session_state.authenticator.credentials["usernames"][username]["email"]
                    st.session_state["user_mode"]="signedin"
                    time.sleep(5)
                    st.rerun()
                elif authentication_status==False:
                    placeholder_error.error('Username/password is incorrect')
            # if st.button("skip log in", ):
            #     self.userId="test"
            #     st.session_state["mode"]="signedin"

    @st.dialog(title=" ")
    def recover_password_username_popup(self, type):

        add_vertical_space(1)
        try:
            username, email = st.session_state.authenticator.forgot_username(fields={"Form name": "", "Email":"Please provide the email associated with your account"})
            if username:
                if send_recovery_email(email, type, username=username, ):
                    st.success('Please check your email')
            elif username== False:
                st.error('Email not found')
        except Exception as e:
            print(e)
            st.error("something went wrong, please try again.")


    def google_signin(self,):

        auth_code = st.query_params.get("code")
      
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
                # st.session_state["google_auth_code"] = auth_code
                # st.session_state["user_info"] = user_info
                st.session_state["credentials"] = credentials
                st.session_state.cm.set_cookie(user_info.get("email"), user_info.get("name"),)
                st.session_state["user_mode"]="signedin"
                time.sleep(5)
                st.rerun()
            except Exception as e:
                pass
        else:
            st.markdown(google_button, unsafe_allow_html=True)
            st.markdown('<span id="button-after"></span>', unsafe_allow_html=True)
            if st.button("Sign in with Google"):
                authorization_url, state = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                )
                # webbrowser.open_new_tab(authorization_url)
                st.query_params.redirect_uri=authorization_url
                st.query_params.state=state
                # st.experimental_set_query_params(redirect_uri=authorization_url, state=state)
                st.write(f'<meta http-equiv="refresh" content="0;url={authorization_url}">', unsafe_allow_html=True)

    def google_signout(self):
        if "credentials" in st.session_state:
            credentials = st.session_state["credentials"]
            revoke_token_url = "https://accounts.google.com/o/oauth2/revoke?token=" + credentials.token
            response = requests.get(revoke_token_url)
            if response.status_code == 200:
                print("Successfully signed out")
                # Clear session state
                del st.session_state["credentials"]
            else:
                print("Failed to revoke token")
        else:
            print("No user is signed in")

    def sign_up(self,):

        print("inside signing up")
        _, c, _ = st.columns([1, 1, 1])
        with c:
            try:
                authenticator = st.session_state.authenticator
                email, username, name= authenticator.register_user(pre_authorization=False)
                if email:
                    with open(login_file, 'w') as file:
                        yaml.dump(st.session_state.config, file, default_flow_style=False)
                    # if self.save_password( username, name, password, email):
                    st.session_state["user_mode"]="signedout"
                    st.success("User registered successfully. Redirecting...")
                    time.sleep(5)
                    st.rerun()
            except RegisterError as e:
                if e.message=="Password does not meet criteria":
                    st.warning("""Password must:
                    Contain at least one lowercase letter, at least one uppercase letter, at least one digit, at least one special character and between 8 and 20 characters in length""")
                else:
                    st.warning(e)

    def reset_password(self, token, username):
    
        _, c, _ = st.columns([1, 1, 1])
        with c:
            if self.verify_token(token):
                with st.form(key="password_reset_form"):
                # Display the password reset form
                    st.image("./resources/logo_acareerai.png")
                    st.subheader("Password Reset")
                    new_password = st.text_input("New Password", type="password", )
                    confirm_password = st.text_input("Confirm Password", type="password")               
                    if st.form_submit_button("Reset Password"):
                        if new_password == confirm_password:
                            # Update the user's password in the database
                            self.save_password(new_password, username)
                            st.success("Password has been reset successfully! Redirecting...")
                            time.sleep(5)
                            st.session_state["user_mode"]="signedout"
                            nav_to("/user")                              
                        else:
                            st.error("Passwords do not match.")
            else:
                st.error("Invalid or expired token.")
 
                

    def save_password(self, password, username, filename=login_file):

        try:
            with open(filename, 'r') as file:
                credentials = yaml.safe_load(file)
                # Add the new user's details to the dictionary
            # credentials['credentials']['usernames'][username] = {
            #     'email': email,
            #     'name': name,
            #     'password': password
            # }  
            credentials['credentials']['usernames'][username]['password']=password
            with open(filename, 'w') as file:
                yaml.dump(credentials, file)
            print("successfully saved password")
            # return True
        except Exception as e:
            raise e


    def verify_token(self, token):
        # Token verification logic
        # Check if token exists in the database and is not expired
        return True       


    
    def initialize_resume(self):

        _, c, _ = st.columns([1, 1, 1])
        with c:
            st.title("Let's get started with your resume")
            if "user_resume_path" in st.session_state:
                st.session_state.resume_disabled = False
            else:
                st.session_state.resume_disabled = True
            st.markdown("#")
            # c1, _, c2 = st.columns([5, 1, 3])
            resume = st.file_uploader(label="Upload your resume",
                            key="user_resume",
                                accept_multiple_files=False, 
                                on_change=self.form_callback, 
                                type=["pdf", "odt", "docx", "txt"],
                                help="This will become your default resume.")
            add_vertical_space(3)
            _, c1 = st.columns([5, 1])
            with c1:
                # st.markdown(general_button, unsafe_allow_html=True)
                # st.markdown('<span class="general-button"></span>', unsafe_allow_html=True)
                st.button(label="Submit", disabled=st.session_state.resume_disabled, on_click=self.initialize_resume_callback)
                if st.button(label="I'll do it later", type="primary", ):
                    # delete any old resume saved in session state
                    if "user_resume_path" in st.session_state:
                        del st.session_state["user_resume_path"]
                    self.create_empty_profile() 
                    st.rerun()

    def initialize_resume_callback(self, ):

        """Saves user resume to a lancedb table"""
        # create generated dict from resume
        resume_dict = create_resume_info(st.session_state.user_resume_path,)
        resume_dict.update({"resume_path":st.session_state.user_resume_path})
        resume_dict.update({"user_id": self.userId}) 
        # save resume dict into session's profile
        st.session_state["profile"] = resume_dict
        # save resume/profile into lancedb table
        save_user_changes(self.userId, resume_dict, ResumeUsers, lance_users_table)
        # delete any old profile instance
        try:
            del st.session_state["profile"]
        except Exception:
            pass
        print("Successfully added user to lancedb table")
                 
    def create_empty_profile(self):

        """ In case user did not upload a resume, this creates an empty profile and saves it as a lancedb table entry"""

        # filename = str(uuid.uuid4())
        # end_path =  os.path.join( st.session_state.user_save_path, "", "uploads", filename+'.txt')
        #creates an empty file
        # write_file(end_path, file_content="")
        st.session_state["profile"] = {"user_id": self.userId, "resume_path": "", "resume_content":"",
                   "contact": {"city":"", "email": "", "linkedin":"", "name":"", "phone":"", "state":"", "websites":"", }, 
                   "education": {"coursework":[], "degree":"", "gpa":"", "graduation_year":"", "institution":"", "study":""}, 
                   "pursuit_jobs":"", "summary_objective":"", "included_skills":[], "work_experience":[], "projects":[], 
                   "certifications":[], "suggested_skills":[], "qualifications":[], "awards":[], "licenses":[], "hobbies":[]}
        save_user_changes(self.userId, st.session_state.profile, ResumeUsers, lance_users_table) 
        # delete any old profile instance
        try:
            del st.session_state["profile"]
        except Exception:
            pass

    # def about_future(self):

    #     st.text_area("Where do you see yourself in 5 years?")




    # def about_career(self):

    #     c1, c2 = st.columns([1, 1])
    #     # components.html( """<div style="text-align: bottom"> Work Experience</div>""")
    #     with c1:
    #         st.text_input("Desired job title(s)", placeholder="please separate each with a comma", key="jobx", on_change=self.form_callback)
    #     with c2:
    #         st.select_slider("Level of experience",  options=["no experience", "entry level", "junior level", "mid level", "senior level"], key='job_levelx', on_change=self.form_callback)   
    #     c1, c2=st.columns([1, 1])
    #     with c1:
    #         min_pay = st.text_input("Minimum pay", key="min_payx", on_change=self.form_callback)
    #     with c2: 
    #         pay_type = st.selectbox("", ("hourly", "annually"), index=None, placeholder="Select pay type...", key="pay_typex", on_change=self.form_callback)
    #     job_unsure=st.checkbox("Not sure about the job")
    #     if job_unsure:
    #         st.multiselect("What industries interest you?", ["Healthcare", "Computer & Technology", "Advertising & Marketing", "Aerospace", "Agriculture", "Education", "Energy", "Entertainment", "Fashion", "Finance & Economic", "Food & Beverage", "Hospitality", "Manufacturing", "Media & News", "Mining", "Pharmaceutical", "Telecommunication", " Transportation" ], key="industryx", on_change=self.form_callback)
    #     career_switch = st.checkbox("Career switch", key="career_switchx", on_change=self.form_callback)
    #     if career_switch:
    #         st.text_area("Transferable skills", placeholder="Please separate each transferable skill with a comma", key="transferable_skillsx", on_change=self.form_callback)
    #     location = st.checkbox("Location is important to me")
    #     # location = st.radio("Is location important to you?", [ "no, I can relocate","I only want to work remotely", "I want to work near where I currently live", "I have a specific place in mind"], key="locationx", on_change=self.form_callback)
    #     if location:
    #         location_input = st.radio("", ["I want remote work", "work near where I currently live", "I have a specific place in mind"])
    #         if location_input=="I want remote work":
    #             st.session_state.location_input = "remote"
    #         if location_input == "I have a specific place in mind":
    #             st.text_input("Location", "e.g., the west coast, NYC, or a state", key="location_inputx", on_change=self.form_callback)
    #         if location_input == "work near where I currently live":
    #             if st.checkbox("Share my location"):
    #                 loc = get_geolocation()
    #                 if loc:
    #                     address = self.get_address(loc["coords"]["latitude"], loc["coords"]["longitude"])
    #                     st.session_state["location_input"] = address





    



    # def test_clear(self):
        
    #     vectorstore = retrieve_vectorstore("elasticsearch", index_name=self.userId)
    #     record_manager=create_record_manager(self.userId)
    #     print(f"record manager keys: {record_manager.list_keys()}")
    #     clear_index(record_manager, vectorstore)
    #     print(f"record manager keys: {record_manager.list_keys()}")

    # def get_address(self, latitude, longitude):

    #     """Retrieves the address of user's current location """

    #     geolocator = Nominatim(user_agent="nearest_city_finder")
    #     try:
    #         location = geolocator.reverse((latitude, longitude), exactly_one=True)
    #         print(location.address)
    #         return location.address
    #     except GeocoderTimedOut:
    #         # Retry after a short delay
    #         return self.get_address(latitude, longitude)
        
    def form_callback(self,):


        # try:
        #     st.session_state["self_description"] = st.session_state.self_descriptionx
        #     st.session_state["users"][self.userId]["self_description"] = st.session_state.self_description
        # except AttributeError:
        #     pass
        # try:
        #     st.session_state["career_goals"] = st.session_state.career_goalsx
        #     st.session_state["users"][self.userId]["career_goals"] = st.session_state.career_goals
        # except AttributeError:
        #     pass
        # try:
        #     st.session_state["job_level"] = st.session_state.job_levelx
        #     st.session_state["users"][self.userId]["job_level"] = st.session_state.job_level
        # except AttributeError:
        #     pass
        # try:
        #     st.session_state["min_pay"] = st.session_state.min_payx
        #     st.session_state["users"][self.userId]["mininum_pay"] = st.session_state.min_pay
        # except AttributeError:
        #     pass
        # try:
        #     st.session_state["pay_type"] = st.session_state.pay_typex
        #     st.session_state["users"][self.userId]["pay_type"] = st.session_state.pay_type
        # except AttributeError:
        #     pass
        
        # try:
        #     st.session_state["career_switch"] = st.session_state.career_switchx
        #     st.session_state["users"][self.userId]["career_switch"] = st.session_state.career_switch
        # except AttributeError:
        #     pass
        # try:
        #     transferable_skills = st.session_state.transferable_skillsx
        #     self.process("transferable_skills", transferable_skills)
        #     st.session_state["users"][self.userId]["transferable_skills"] = st.session_state.transferable_skills
        # except AttributeError:
        #     pass
        # try:
        #     location_input = st.session_state.location_inputx
        #     self.process("location_input", location_input)
        #     st.session_state["users"][self.userId]["location_input"] = st.session_state.location_input
        # except AttributeError:
        #     pass
        try:
            # delete old instance of user_resume_path
            try:
                del st.session_state["user_resume_path"]
            except Exception:
                pass
            resume = st.session_state.user_resume
            if resume:
                self.process([resume], "resume", )
        except AttributeError:
            pass
        try:
            try:
                del st.session_state["job_posting_path"]
                del st.session_state["job_description"]
                # del st.session_state["preselection"]
            except Exception:
                pass
            posting = st.session_state.job_postingx
            if posting:
                self.process(posting, "job_posting",)
        except AttributeError:
            pass
        # try:
        #     try:
        #         del st.session_state["job_posting_path"]
        #     except Exception:
        #         pass
        #     posting_link = st.session_state.posting_link
        #     if posting_link:
        #         self.process(posting_link, "job_posting",)
        # except AttributeError:
        #     pass
        # try:
        #     try:
        #         del st.session_state["job_description"]
        #     except Exception:
        #         pass
        #     job_descr = st.session_state.job_descriptionx
        #     if job_descr:
        #         self.process(job_descr, "job_description",)
        # except AttributeError:
        #     pass



    def process(self, input_value: Any, input_type:str, ):

        """ Processes and checks user inputs and uploads"""

        if input_type=="resume":
            result = process_uploads(input_value, st.session_state.users_upload_path, )
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="resume":
                    st.session_state["user_resume_path"]= end_path
                else:
                    st.info("Please upload your resume")
            else:
                st.info("That didn't work, please try again.")         
        elif input_type=="job_posting":
            result = process_links(input_value, st.session_state.users_upload_path, )
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="job posting":
                    st.session_state["job_posting_path"]=end_path
                    st.session_state["posting_link"]=input_value
                else:
                    st.info("Please upload a job posting link")
            else:
                result = process_inputs(input_value, match_topic="job posting or job description")
                if result is not None:
                    st.session_state["job_description"] = input_value
                else:
                    st.info("That didn't work. Please try pasting the content of job description")
        # elif input_type=="job_description":
        #     result = process_inputs(input_value, match_topic="job posting or job description")
        #     if result is not None:
        #         st.session_state["job_description"] = input_value
        #     else:
        #         st.info("Please share a job descriptions")

        # if input_type=="location_input":
        #     st.session_state.location_input=input_value.split(",")
        # elif input_type=="transferable_skills":
        #     st.session_state.transferable_skills=input_value.split(",")
    @st.dialog("drag to rearrange")
    def rearrange_skills_popup(self, ):
        data=[]
        idx=0
        for skill in self.skills_set:
            data.append({"id":skill, "order":idx, "name":skill})
            idx+=1
        slist = DraggableList(data, key="skills_rearrange_draggable")
        if slist:
            print(slist)
            st.session_state["profile"]["included_skills"]=[skill["name"] for skill in slist]
            st.session_state["profile_changed"]=True


    @st.fragment()
    def display_skills(self, ):

        """ Interactive display of skills section of the profile"""

        def get_display():
            c1, c2=st.columns([1, 1])
            with c1:
                with st.container(border=True):
                    c3, c4 = st.columns([3, 1])
                    with c3:
                        st.write("Your skills")
                    with c4:
                        with stylable_container(
                            key="custon_rearrange_skills_button",
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
                            if st.button("rearrange", key="rearrange_skills_button", ):
                                self.rearrange_skills_popup()

                    with stylable_container(key="custom_skills_button",
                    # border-radius: 20px;
                    # background-color: #4682B4;
                            css_styles=["""button {
                                color: black;
                                background: none;
                                border: none;
                                font-size: 8px;
                                padding: 0;
                                cursor: pointer;
                            }""",
                            ],
                    ):
                        my_grid=grid([1, 1, 1])
                        for idx, skill in enumerate(self.skills_set):
                            x = my_grid.button(skill+" :red[x]", key=f"remove_skill_{idx}", on_click=skills_callback, args=(idx, skill, ))
            with c2:
                st.write("Suggested skills to include")
                for idx, skill in enumerate(self.generated_skills_set):
                    y = st.button(skill +" :green[+]", key=f"add_skill_{idx}", on_click=skills_callback, args=(idx, skill, ))
                st.text_input("Add a skill", key="add_skill_custom", on_change=skills_callback, args=("", "", ))
            
        def skills_callback(idx, skill):
            try:
                new_skill = st.session_state.add_skill_custom
                if new_skill:
                    # Add only unique items that are not already in the ordered set
                    if new_skill not in self.skills_set:
                        self.skills_set.append(new_skill)
                        st.session_state["profile"]["included_skills"]=self.skills_set
                        st.session_state["profile_changed"]=True
                        st.session_state.add_skill_custom=''
            except Exception:
                    pass
            try:
                name = f"add_skill_{idx}"
                add_skill = st.session_state[name]
                if add_skill:
                    if add_skill not in self.skills_set:
                        self.skills_set.append(add_skill)
                        st.session_state["profile"]["included_skills"]=self.skills_set
                    self.generated_skills_set.remove(skill)
                    st.session_state["profile"]["suggested_skills"]=[i for i in st.session_state["profile"]["suggested_skills"] if not (i["skill"] == skill)]
                    st.session_state["profile_changed"]=True
            except Exception:
                pass
            try:
                name = f"remove_skill_{idx}"
                remove_skill = st.session_state[name]
                if remove_skill:
                    # print('remove skill', skill)
                    self.skills_set.remove(skill)
                    st.session_state["profile"]["included_skills"]=self.skills_set
                    st.session_state["profile_changed"]=True
            except Exception:
                pass

        return get_display



    @st.fragment()
    def display_field_details(self, field_name, x, field_detail, type):

        """ Interactive display of specific details such as bullet points in each field"""

        def get_display():
            
            if x!=-1:
                field_list = st.session_state["profile"][field_name][x][field_detail]
            else:
                field_list = st.session_state["profile"][field_name][field_detail]
            for idx, value in enumerate(field_list):
                add_detail(value, idx,)
            if type=="bullet_points":
                y, _, _ = st.columns([1, 20, 1])
                with y: 
                    st.button("**:green[+]**", key=f"add_{field_name}_{field_detail}_{x}", on_click=add_new_entry, help="add a description", use_container_width=True)
            if x!=-1 and len(field_list)>0:
                details = ". ".join(st.session_state["profile"][field_name][x][field_detail])
                # print("BBBBB", details)
                self.display_field_analysis(type, field_name, details=details, idx=x)

        def delete_entry(placeholder, idx):
            if type=="bullet_points":
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
            if type=="bullet_points":
                if x!=-1:
                    st.session_state["profile"][field_name][x][field_detail].append("")
                else:
                    st.session_state["profile"][field_name][field_detail].append("")

        def add_detail(value, idx,):
            
            placeholder = st.empty()
            if type=="bullet_points":
                with placeholder.container():
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
                   

        def callback(idx, ):
            
            try:
                new_entry = st.session_state[f"descr_{field_name}_{x}_{field_detail}_{idx}"]
                if x!=-1:
                    st.session_state["profile"][field_name][x][field_detail][idx] = new_entry
                else:
                    st.session_state["profile"][field_name][field_detail][idx] = new_entry
                st.session_state["profile_changed"]=True
            except Exception as e:
                pass
            st.session_state["profile_changed"]=True

        return get_display


    @st.fragment()   
    def display_field_content(self, name):

        """Interactive display of content of each profile/resume field """
        #TODO: FUTURE USING DRAGGABLE CONTAINERS TO ALLOW REORDER CONTENT https://discuss.streamlit.io/t/draggable-streamlit-containers/72484?u=yueqi_peng
        def get_display():

            for idx, value in enumerate(st.session_state["profile"][name]):
                add_container(idx, value)
            st.button("**:green[+]**", key=f"add_{name}_button", on_click=add_new_entry, use_container_width=True)
                  
        def add_new_entry():
            # adds new empty entry to profile dict
            if name=="certifications" or name=="licenses":
                st.session_state["profile"][name].append({"description":[],"issue_date":"", "issue_organization":"", "title":""})
            elif name=="work_experience":
                st.session_state["profile"][name].append({"company":"","description":[],"end_date":"","job_title":"","location":"","start_date":""})
            elif name=="awards" or name=="qualifications":
                st.session_state["profile"][name].append({"description":[],"title":""})
            elif name=="projects":
                st.session_state["profile"][name].append({"company":"","description":[],"end_date":"","link":"","location":"","start_date":"", "title":""})
        
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
                    st.button("**:red[-]**", type="primary", key=f"{name}_delete_{idx}", on_click=delete_container, args=(placeholder, idx) )
                if name=="awards" or name=="qualifications":
                    title = value["title"]
                    # description = value["description"]
                    st.text_input("Title", value=title, key=f"{name}_title_{idx}", on_change=callback, args=(idx, ), placeholder="Title", label_visibility="collapsed")
                    # st.write("Description")
                    get_display= self.display_field_details(name, idx, "description", "bullet_points")
                    get_display()
                elif name=="certifications" or name=="licenses":
                    title = value["title"]
                    organization = value["issue_organization"]
                    date = value["issue_date"]
                    # description = value["description"]
                    st.text_input("Title", value=title, key=f"{name}_title_{idx}", on_change=callback, args=(idx, ), placeholder="Title", label_visibility="collapsed")
                    st.text_input("Issue organization", value=organization, key=f"{name}_org_{idx}", on_change=callback, args=(idx, ), placeholder="Issue organization", label_visibility="collapsed")
                    st.text_input("Issue date", value=date, key=f"{name}_date_{idx}", on_change=callback, args=(idx, ), placeholder="Issue date", label_visibility="collapsed")
                    # st.write("Description")
                    get_display= self.display_field_details(name, idx, "description", "bullet_points")
                    get_display()
                elif name=="work_experience":
                    job_title = value["job_title"]
                    company = value["company"]
                    start_date = value["start_date"]
                    end_date = value["end_date"]
                    location = value["location"]
                    c1, c2, c3= st.columns([2, 1, 1])
                    with c1:
                        st.text_input("Job title", value = job_title, key=f"experience_title_{idx}", on_change=callback,args=(idx,),  placeholder="Job title", label_visibility="collapsed")
                        st.text_input("Company", value=company, key=f"experience_company_{idx}", on_change=callback,args=(idx,), placeholder="Company", label_visibility="collapsed"  )
                    with c2:
                        st.text_input("start date", value=start_date, key=f"experience_start_date_{idx}", on_change=callback,args=(idx,), placeholder="Start date", label_visibility="collapsed" )
                        st.text_input("Location", value=location, key=f"experience_location_{idx}", on_change=callback,  args=(idx,), placeholder="Location", label_visibility="collapsed" )
                    with c3:
                        st.text_input("End date", value=end_date, key=f"experience_end_date_{idx}", on_change=callback, args=(idx,), placeholder="End date", label_visibility="collapsed" )
                    # st.write("Description")
                    get_display= self.display_field_details("work_experience", idx, "description", "bullet_points")
                    get_display()
                elif name=="projects":
                    project_title = value["title"]
                    company = value["company"]
                    start_date = value["start_date"]
                    end_date = value["end_date"]
                    # descriptions = st.session_state["profile"][name][idx]["description"]
                    location = value["location"]
                    link =value["link"]
                    location=value["location"]
                    c1, c2, c3= st.columns([2, 1, 1])
                    with c1:
                        st.text_input("Project title", value = project_title, key=f"project_title_{idx}", on_change=callback,args=(idx,),  placeholder="Project title", label_visibility="collapsed")
                        st.text_input("Company", value=company, key=f"project_company_{idx}", on_change=callback,args=(idx,), placeholder="Company", label_visibility="collapsed"  )
                    with c2:
                        st.text_input("start date", value=start_date, key=f"project_start_date_{idx}", on_change=callback,args=(idx,), placeholder="Start date", label_visibility="collapsed" )
                        st.text_input("Location", value=location, key=f"project_location_{idx}", on_change=callback,  args=(idx,), placeholder="Location", label_visibility="collapsed" )
                    with c3:
                        st.text_input("End date", value=end_date, key=f"project_end_date_{idx}", on_change=callback, args=(idx,), placeholder="End date", label_visibility="collapsed" )
                        st.text_input("Link", value=link, key=f"project_link_{idx}", on_change=callback, args=(idx,), placeholder="Project link", label_visibility="collapsed" )
                    # st.write("Description")
                    get_display= self.display_field_details("projects", idx, "description", "bullet_points")
                    get_display()

        def callback(idx):
       
            try:
                title = st.session_state[f"{name}_title_{idx}"]
                st.session_state["profile"][name][idx]["title"]=title
            except Exception:
                pass
            try:
                date = st.session_state[f"{name}_date_{idx}"]
                st.session_state["profile"][name][idx]["issue_date"]=date
            except Exception:
                pass
            try:
                org = st.session_state[f"{name}_org_{idx}"]
                st.session_state["profile"][name][idx]["issue_organization"]=org
            except Exception:
                pass
            try:
                descr = st.session_state[f"{name}_descr_{idx}"]
                st.session_state["profile"][name][idx]["description"]=descr
            except Exception:
                pass
            try:
                title = st.session_state[f"experience_title_{idx}"]
                    # self.experience_list[idx]["job_title"] = title
                st.session_state["profile"]["work_experience"][idx]["job_title"] = title
            except Exception:
                pass
            try:
                company = st.session_state[f"company_{idx}"]
                st.session_state["profile"]["work_experience"][idx]["company"] = company
            except Exception:
                pass
            try:
                start_date = st.session_state[f"start_date_{idx}"]
                st.session_state["profile"]["work_experience"][idx]["start_date"] =start_date
            except Exception:
                pass
            try:
                end_date = st.session_state[f"end_date_{idx}"]
                st.session_state["profile"]["work_experience"][idx]["end_date"] = end_date
            except Exception:
                pass
            try:
                location = st.session_state[f"experience_location_{idx}"]
                st.session_state["profile"]["work_experience"][idx]["location"] = location
            except Exception:
                pass
            try:
                experience_description = st.session_state[f"experience_description_{idx}"]
                st.session_state["profile"]["work_experience"][idx]["description"] = experience_description
            except Exception:
                pass
            st.session_state["profile_changed"]=True
            
        return get_display

    @st.fragment()
    def display_field_analysis(self, type, field_name, details, idx=None):

        """ Displays the field-specific analysis UI """

        _, c0, c1, c2 = st.columns([5, 1, 1, 1])

        def display_tailor_options(popover_label="tailor"):
            st.markdown(primary_button2, unsafe_allow_html=True)
            st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
            with stylable_container(
                    key=button_key,
                    css_styles="""
                        button {
                            background: none;
                            border: none;
                            color: #2d2e29;
                            padding: 0;
                            cursor: pointer;
                            font-size: 12px; /* Adjust as needed */
                            text-decoration: none;
                        }
                        """,
                ):
                with st.popover(popover_label):
                    if "job_posting_dict" not in st.session_state:
                        upload = st.button("Please upload a job posting first", type="primary", key=button_key+"_upload")
                        if upload:
                            self.job_posting_popup(mode="resume")
                    else:
                        current = st.button("with the currrent job posting", key=button_key+"_current", type="primary")
                        new = st.button("with a new job posting", key=button_key+"_new", type="primary")
                        if current:
                            self.tailor_callback(type, field_name, details, )
                            st.rerun()
                        if new:
                            self.job_posting_popup()
        with c1:
            if f"evaluated_{field_name}" in st.session_state:
                if idx:
                    popover_key=f"eval_{field_name}_popover_{idx}"
                else:
                    popover_key = f"eval_{field_name}_popover"
                with stylable_container(
                    key=popover_key,
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
                    with st.popover("evaluate"):
                            if idx:
                                button_key=f"eval_again_{field_name}_button_{idx}"
                            else:
                                button_key=f"eval_again_{field_name}_button"
                            if f"{field_name}_readability" in st.session_state:
                                fig = readability_indicator(st.session_state[f"{field_name}_readability"])
                                st.plotly_chart(fig)
                            evaluation = st.session_state[f"evaluated_{field_name}"]
                            st.write(evaluation)
                            st.markdown(primary_button2, unsafe_allow_html=True)
                            st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
                            st.button("evaluate again", key=button_key,  on_click=self.evaluation_callback, args=(field_name, details, ), )
            else:
                if idx:
                    button_key=f"eval_{field_name}_button_{idx}"
                else:
                    button_key=f"eval_{field_name}_button"
                st.markdown(primary_button2, unsafe_allow_html=True)
                st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
                evaluate = st.button("evaluate",  key=button_key, on_click=self.evaluation_callback, args=(field_name, details), )
        with c2:
            if f"tailored_{field_name}" in st.session_state:
                if idx:
                    popover_key=f"tailor_{field_name}_popover_{idx}"
                else:
                    popover_key = f"tailor_{field_name}_popover"
                with stylable_container(
                    key=popover_key,
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
                    with st.popover("tailor"):
                        if idx:
                            button_key=f"tailor_again_{field_name}_button_{idx}"
                        else:
                            button_key=f"tailor_again_{field_name}_button"
                        tailoring = st.session_state[f"tailored_{field_name}"]
                        if field_name=="summary_objective":
                            if tailoring!="please try again":
                                # split sentence into words and punctuations
                                text_list = re.findall(r"[\w']+|[.,!?;]", st.session_state["profile"]["summary_objective"])
                                replaced_words = [replacement["replaced_words"] for replacement in tailoring["replacements"]]
                                substitutions = [substitution["substitution"] for substitution in tailoring["replacements"]]
                                # replace replacements with annotation
                                for i in range(len(text_list)):
                                    for j in range(1, len(text_list)-i+1):
                                        substring = " ".join(text_list[i:i+j])
                                        if substring in replaced_words:
                                            idx = replaced_words.index(substring)
                                            text_list[i] = (substitutions[idx], substring)
                                            for x in range(i+1, i+j):
                                                text_list[x]=""
                                            break                 
                                text_list =  [text + " " if not isinstance(text, tuple) else text for text in text_list if text != ""]
                                print(text_list)
                                annotated_text(text_list)
                            else:
                                st.write(tailoring)
                        else:
                            st.write(tailoring)
                        st.markdown(primary_button2, unsafe_allow_html=True)
                        st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
                        display_tailor_options(popover_label="tailor again")
                        # st.button("tailor again", key=button_key, on_click=self.tailor_callback, args=(field_name, details, ), )
            else:
                if idx:
                    button_key=f"tailor_{field_name}_button_{idx}"
                else:
                    button_key=f"tailor_{field_name}_button"
                display_tailor_options(popover_label="tailor")
     
          

    @st.dialog("Job posting")   
    def job_posting_popup(self, mode="resume"):

        """ Opens a popup for adding a job posting """

        # disables the next button until user provides a job posting
        if "job_posting_path" in st.session_state or "job_description" in st.session_state:
            st.session_state["job_posting_disabled"]=False
        else:
            st.session_state["job_posting_disabled"]=True
        if mode=="cover_letter":
            st.warning("Please be aware that some organizations may not accept AI generated cover letters. Always research before you apply.")
        st.info("In case a job posting link does not work, please copy and paste the complete job posting content into the box below")
        # past_jobs = st.session_state["tracker"]
        # if past_jobs:
        #     options =[past_job["company"] + "-" + past_job["job"] for past_job in past_jobs]
        #     print(options)
        #     selection = st.selectbox(label="Select a past job", options = options, index=None, )
        #     if selection:
        #         st.session_state["job_posting_dict"] = past_jobs[past_jobs.index(selection)]
        #         st.session_state["preselection"] = True
        job_description = st.text_area("job posting link or job description", 
                                        key="job_postingx", 
                                        placeholder="Pleasae paste a job posting link or a job description here",
                                        on_change=self.form_callback, 
                                        label_visibility="collapsed",
                                            )
        # st.session_state["info_container"]=st.empty()
        if mode=="resume":
            freeze = st.radio("Would you like to freeze your profile before you start tailoring?", 
                    help = "This will make your tailoring changes a session copy so you can edit without losing the original profile",
                    options=["yes", "no"], 
                    horizontal=True,)
            if freeze:
                st.session_state["freeze"]=True
        if st.button("Next", key="job_posting_button", disabled=st.session_state.job_posting_disabled,):
            # if "preselection" not in st.session_state:
            self.initialize_job_posting_callback()
            # starts field tailoring if called to tailor a field
            # if mode=="cover_letter":
            #     download_path=asyncio_run(lambda: generate_basic_cover_letter(st.session_state["profile"], st.session_state["job_posting_dict"], st.session_state["users_download_path"], ))
            #     if download_path:
            #         st.session_state["job_posting_dict"].update({"cover_letter_path": download_path})
            #         save_user_changes(self.userId, st.session_state["job_posting_dict"], JobTrackingUsers, lance_tracker_table)
            #         with open(download_path, "rb") as file:
            #             file_content = file.read()
            #         st.download_button(
            #             label="Download your cover letter",
            #             data=file_content,
            #             file_name="cover_letter.docx",  # Specify the default name for the downloaded file
            #             mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    # )
            # starts cover letter generation if called to generate cover letter
                # automatic_download(download_path)
            # elif mode=="resume" and "tailoring_field" in st.session_state:
                # tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"], st.session_state["tailoring_field"])
                # tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"],st.session_state["tailoring_field"], st.session_state["tailoring_details"] if "tailoring_details" in st.session_state else None)
            st.rerun()

    def initialize_job_posting_callback(self, ):

        st.session_state["job_posting_dict"] = create_job_posting_info(
                    st.session_state.job_posting_path if "job_posting_path" in st.session_state else "",
                    st.session_state.job_description if "job_description" in st.session_state else "",  
                )
        # st.session_state["job_posting_dict"].update({"posting_path":st.session_state["job_posting_path"] if "job_posting_path" in st.session_state else ""})
        st.session_state["job_posting_dict"].update({"link": st.session_state["posting_link"] if "posting_link" in st.session_state else ""})
        st.session_state["job_posting_dict"].update({"user_id": self.userId})
        st.session_state["job_posting_dict"].update({"resume_path": ""})
        st.session_state["job_posting_dict"].update({"cover_letter_path": ""})
        st.session_state["job_posting_dict"].update({"status": ""})
        st.session_state["job_posting_dict"].update({"time":datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        save_user_changes(self.userId, st.session_state["job_posting_dict"], JobTrackingUsers, lance_tracker_table)


    
    def tailor_callback(self, type=None, field_name=None, field_details=None):
      
        if "job_posting_dict" in st.session_state and field_name:
            # starts specific field tailoring
            tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"], type, field_name, field_details,)
        else:

            # initialize a job posting popup 
            if field_name:
                st.session_state["tailoring_field"]=field_name
            if field_details:
                st.session_state["tailoring_details"]=field_details
            self.job_posting_popup()
            
   


    def evaluation_callback(self, field_name=None, details=None,):

        if field_name:
            # starts specific evaluation of a field
            evaluate_resume(resume_dict=st.session_state["profile"], type=field_name, details=details )
        else:
            # start general evaluation if there's no saved evaluation 
            if "init_eval" not in st.session_state and st.session_state["evaluation"] is None:
                # evaluate_resume(st.session_state["profile"], "general")
                self.eval_thread = thread_with_trace(target=evaluate_resume, args=(st.session_state["profile"], "general", ))
                add_script_run_ctx(self.eval_thread, self.ctx)
                self.eval_thread.start()   
                st.session_state["init_eval"]=True
         

    


    def display_profile(self,):

        """Displays interactive user profile UI"""

        # self.save_session_profile()
        eval_col, profile_col, fields_col = st.columns([1, 3, 1])   
        _, menu_col, _ = st.columns([3, 1, 3])   
        with fields_col:
             # save session profile periodically unless user freezes their profile
            freeze=st.toggle("Freeze my profile", value=st.session_state["freeze"], help="If you freeze your profile, your edits won't be permanently saved")
            if freeze:
                 pass
            else:
                self.save_session_profile()

        # general evaluation column
        with eval_col:
            float_container= st.container()
            with float_container:
                self.display_general_evaluation(float_container)
                self.evaluation_callback()
        # the main profile column
        with profile_col:
            c1, c2 = st.columns([1, 1])
            with c1:
                with st.expander(label="Contact", ):
                    name = st.session_state["profile"]["contact"]["name"]
                    if st.text_input("Name", value=name, key="profile_name", placeholder="Name", label_visibility="collapsed")!=name:
                        st.session_state["profile"]["contact"]["name"]=st.session_state.profile_name
                        st.session_state["profile_changed"] = True
                    email = st.session_state["profile"]["contact"]["email"]
                    if st.text_input("Email", value=email, key="profile_email", placeholder="Email", label_visibility="collapsed")!=email:
                        st.session_state["profile"]["contact"]["email"] = st.session_state.profile_email
                        st.session_state["profile_changed"] = True
                    phone = st.session_state["profile"]["contact"]["phone"]
                    if st.text_input("Phone", value=phone, key="profile_phone", placeholder="Phone", label_visibility="collapsed")!=phone:
                        st.session_state["profile"]["contact"]["phone"]=st.session_state.profile_phone
                        st.session_state["profile_changed"] = True
                    city = st.session_state["profile"]["contact"]["city"]
                    if st.text_input("City", value=city, key="profile_city", placeholder="City", label_visibility="collapsed")!=city:
                        st.session_state["profile"]["contact"]["city"]=st.session_state.profile_city
                        st.session_state["profile_changed"] = True
                    state = st.session_state["profile"]["contact"]["state"]
                    if st.text_input("State", value=state, key="profile_state", placeholder="State", label_visibility="collapsed")!=state:
                        st.session_state["profile"]["contact"]["state"]=st.session_state.profile_state
                        st.session_state["profile_changed"] = True
                    linkedin = st.session_state["profile"]["contact"]["linkedin"]
                    if st.text_input("Linkedin", value=linkedin, key="profile_linkedin", placeholder="Linkedin", label_visibility="collapsed")!=linkedin:
                        st.session_state["profile"]["contact"]["linkedin"]=st.session_state.profile_linkedin
                        st.session_state["profile_changed"] = True
                    website = st.session_state["profile"]["contact"]["websites"]
                    if st.text_input("Other websites", value=website, key="profile_websites", placeholder="Other websites, each separated by a comma", label_visibility="collapsed")!=website:
                        st.session_state["profile"]["contact"]["websites"]=st.session_state.profile_websites
                        st.session_state["profile_changed"] = True
            with c2:
                with st.expander(label="Education"):
                    degree = st.session_state["profile"]["education"]["degree"]
                    if st.text_input("Degree", value=degree, key="profile_degree", placeholder="Degree", label_visibility="collapsed")!=degree:
                        st.session_state["profile"]["education"]["degree"]=st.session_state.profile_degree
                        st.session_state["profile_changed"] = True
                    study = st.session_state["profile"]["education"]["study"]
                    if st.text_input("Area of study", value=study, key="profile_study", placeholder="Area of Study", label_visibility="collapsed")!=study:
                        st.session_state["profile"]["education"]["study"]=st.session_state.profile_study
                        st.session_state["profile_changed"] = True
                    grad_year = st.session_state["profile"]["education"]["graduation_year"]
                    if st.text_input("Graduation year", value=grad_year, key="profile_grad_year", placeholder="Graduation year", label_visibility="collapsed")!=grad_year:
                        st.session_state["profile"]["education"]["graduation_year"]=st.session_state.profile_grad_year
                        st.session_state["profile_changed"] = True
                    gpa = st.session_state["profile"]["education"]["gpa"]
                    if st.text_input("GPA", value=gpa, key="profile_gpa", placeholder="GPA", label_visibility="collapsed")!=gpa:
                        st.session_state["profile"]["education"]["gpa"]=st.session_state.profile_gpa
                        st.session_state["profile_changed"] = True
                    st.markdown("Course works")
                    display_detail=self.display_field_details("education", -1, "coursework", "bullet_points")
                    display_detail()
            with st.expander(label="Summary Objective",):
                pursuit_jobs = st.session_state["profile"]["pursuit_jobs"]
                if st.text_input("Pursuing titles", value=pursuit_jobs, key="profile_pursuit_jobs", placeholder="Job titles", label_visibility="collapsed", )!=pursuit_jobs:
                    st.session_state["profile"]["pursuit_jobs"] = st.session_state.profile_pursuit_jobs
                    st.session_state["profile_changed"] = True
                summary = st.session_state["profile"]["summary_objective"]
                if st.text_area("Summary", value=summary, key="profile_summary", placeholder="Your summary objective", label_visibility="collapsed")!=summary:
                    st.session_state["profile"]["summary_objective"] = st.session_state.profile_summary
                    st.session_state["profile_changed"] = True
                if st.session_state["profile"]["summary_objective"]:
                    self.display_field_analysis(type="text", field_name="summary_objective", details=st.session_state["profile"]["summary_objective"])
            with st.expander(label="Work Experience",):
                # if st.session_state["profile"]["work_experience"]:
                #     self.display_field_analysis("work_experience")
                get_display=self.display_field_content("work_experience")
                get_display()
            with st.expander(label="Skills",):
                # self.display_field_analysis("included_skills")
                suggested_skills = st.session_state["profile"]["suggested_skills"]
                self.skills_set= st.session_state["profile"]["included_skills"]
                self.generated_skills_set=set()
                for skill in suggested_skills:
                    self.generated_skills_set.add(skill["skill"])
                get_display=self.display_skills()
                get_display()
            # c1, c2 = st.columns([1, 1])
            # with c1:
            with st.expander(label="Professional Accomplihsment"):
                st.page_link("https://www.indeed.com/career-advice/resumes-cover-letters/listing-accomplishments-on-your-resume", 
                                label="learn more")
                get_display=self.display_field_content("qualifications")
                get_display()
            # with c2:
            with st.expander(label="Projects"):
                get_display=self.display_field_content("projects")
                get_display()
            # c1, c2=st.columns([1, 1])
            # with c1:
            with st.expander(label="Certifications", ):
                get_display=self.display_field_content("certifications")
                get_display()
        # with c2:
            with st.expander("Awards & Honors"):
                get_display=self.display_field_content("awards")
                get_display()
            # with c3:
            #     with st.expander("Licenses"):
            #         get_display=self.display_field_content("licenses")
            #         get_display()
            #TODO, allow custom fields with custom field details such as bullet points, dates, links, etc. 
            # placeholder = st.empty()
            # st.button("+ custom field", on_click=self.add_custom_field, args=(placeholder, ))
            st.divider()
        # the menu container
        with menu_col:
            with stylable_container(key="custom_button1_profile1",
                            # border-radius: 20px;
                            # background-color: #4682B4;
                        css_styles=["""button {
                            color: white;
                            background-color: #ff8247;
                        }""",
                        # """{
                        #     border: 1px solid rgba(49, 51, 63, 0.2);
                        #     border-radius: 0.5rem;
                        #     padding: calc(1em - 1px)
                        # }
                        # """
                        ],
                ):
                # st.button("Set as default", key="profile_save_button", on_click=save_user_changes, args=(st.session_state.profile, ResumeUsers, lance_users_table), use_container_width=True)
                if st.button("Upload a new resume", key="new_resume_button", use_container_width=True):
                    # NOTE:cannot be in callback because streamlit dialogs are not supported in callbacks
                    self.delete_profile_popup()
                # if st.button("Upload a new job posting", key="new_posting_button", use_container_width=True):
                #     self.job_posting_popup(mode="resume")
                # if st.button("Draft a cover letter", key="cover_letter_button", use_container_width=True):
                #     # NOTE:cannot be in callback because job_posting_popup is a dialog
                #     self.job_posting_popup(mode="cover_letter")
   

    
    @st.fragment(run_every=st.session_state["eval_rerun_timer"])
    def display_general_evaluation(self, container):

        """ Displays the general evaluation result of the profile """


        # NOTE: evaluation either comes from table or from backend function
        try:
            finished = st.session_state["evaluation"]["finished"]
            if finished and st.session_state["eval_rerun_timer"]:
                st.session_state["evaluation"].update({"user_id":self.userId})
                st.session_state["eval_rerun_timer"]=None
                save_user_changes(self.userId, st.session_state["evaluation"], GeneralEvaluation, lance_eval_table)
                st.rerun()      
        except Exception:
            finished=False

        if st.session_state["evaluation"]:

            with st.popover("My profile report ✨"):
                c1, c2=st.columns([1, 1])
                with c1:
                    st.write("**Length**")
                    try:
                        length=st.session_state["evaluation"]["word_count"]
                        # pages=st.session_state["evaluation"]["page_count"]
                        fig = length_chart(int(length))
                        st.plotly_chart(fig, 
                                        # use_container_width=True
                                        )
                    except Exception:
                        if finished is False:
                            st.write("Evaluating...")
                with c2:
                    st.write("**Formatting**")
                    try:
                        add_vertical_space(3)
                        ideal_type = st.session_state["evaluation"]["ideal_type"]
                        st.write("The ideal type for your resume is:")
                        if ideal_type=="chronological":
                            st.header(":green[Chronological]")
                        elif ideal_type=="functional":
                            st.header(":blue[Functional]")
                        # resume_type=st.session_state["evaluation"]["resume_type"]
                        # if ideal_type==resume_type:
                        #     st.subheader(":green[Good]")
                        #     st.write(f"The best type of resume for you is **{ideal_type}** and your resume is also **{resume_type}**")
                        # else:
                        #     st.subheader(":red[Mismatch]")
                        #     st.write(f"The best type of resume for you is **{ideal_type}** but your resume seems to be **{resume_type}**")
                        if not st.session_state["eval_rerun_timer"]:
                            add_vertical_space(1)
                            if st.button("Why the right type matters?", type="primary", key="resume_type_button"):
                                self.resume_type_popup()
                            # add_vertical_space(1)
                            # if st.button("Explore template options", key="resume_template_explore_button"):
                            #     self.explore_template_popup()
                    except Exception:
                        if finished is False:
                            st.write("Evaluating...")
                st.write("**Language**")
                try:
                    categories=["syntax", "diction", "tone", "coherence"]
                    language_data=[]
                    for category in categories:
                        language_data.append({category:st.session_state["evaluation"][category]})
                    fig = language_radar(language_data)
                    st.plotly_chart(fig)
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
                st.write("**Impression**")
                try:
                    impression = st.session_state["evaluation"]["impression"]
                    st.write(impression)
                except Exception:
                    if finished is False:
                        st.write("Evaluating...")
                st.markdown(primary_button2, unsafe_allow_html=True)
                st.markdown('<span class="primary-button2"></span>', unsafe_allow_html=True)
                if st.button("evaluate again", key=f"eval_button", ):
                    # if button_name=="evaluate again ✨":
                        # container.empty()
                        # delete previous evaluation states
                        try:
                            # remove evaluation from lance table and old evaluation from session
                            delete_user_from_table(self.userId, lance_eval_table)
                            del st.session_state["evaluation"]
                            del st.session_state["init_eval"]
                        except Exception:
                            pass
                        finally:
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
        st.image("./resources/functional_chronological_resume.png")
    
    # @st.dialog(" ", width="large")
    # def explore_template_popup(self, ):
    #     """"""
    #     type = sac.tabs([
    #         sac.TabsItem(label='functional',),
    #         sac.TabsItem(label='chronological',),
    #         sac.TabsItem(label='mixed', ),
    #     ], align='center', variant="outline")

    #     if type=="functional":
    #         st.image(["./resources/functional/functional0.png", "./resources/functional/functional1.png", "./resources/functional/functional2.png"])
    #     elif type=="chronological":
    #         st.image(["./resources/chronological/chronological0.png", "./resources/chronological/chronological1.png", "./resources/chronological/chronological2.png"])



    @st.fragment(run_every=5)
    def save_session_profile(self, ):
        if "profile_changed" in st.session_state and st.session_state["profile_changed"]:
            save_user_changes(self.userId, st.session_state.profile, ResumeUsers, lance_users_table)
            st.session_state["profile_changed"]=False


    @st.dialog("Warning")
    def delete_profile_popup(self):

        """ Opens a popup that warns user before uploading a new resume """

        add_vertical_space(2)
        st.warning("Your current profile will be re-populated. Are you sure?")
        add_vertical_space(2)
        c1, _, c2 = st.columns([1, 1, 1])
        with c2:
            if st.button("yes, I'll upload a new resume", type="primary", ):
                delete_user_from_table(self.userId, lance_users_table)
                delete_user_from_table(self.userId, lance_eval_table)
                 # delete session-specific copy of the profile and evaluation
                try:
                    del st.session_state["profile"]
                    del st.session_state["evaluation"]
                    del st.session_state["init_eval"]
                except Exception:
                    pass
                st.rerun()
    
      
    # def get_current_page(self, ):
    #     try:
    #         current_page = pages[ctx.page_script_hash]
    #     except KeyError:
    #         current_page = [
    #             p for p in pages.values() if p["relative_page_hash"] == ctx.page_script_hash
    #         ][0]
    #     print("Current page:", current_page)
    #     return current_page
                


if __name__ == '__main__':

        user=User()
    

