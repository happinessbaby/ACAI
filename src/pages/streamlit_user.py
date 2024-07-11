import streamlit as st
import extra_streamlit_components as stx
from interview_component import my_component
from streamlit_extras.add_vertical_space import add_vertical_space
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from utils.cookie_manager import CookieManager
import time
from datetime import datetime, timedelta, date
from utils.lancedb_utils import create_lancedb_table, add_to_lancedb_table, query_lancedb_table, retrieve_lancedb_table, retrieve_user_profile_dict, delete_user_from_table, save_user_changes, convert_pydantic_schema_to_arrow
from utils.common_utils import  process_linkedin, create_profile_summary, process_uploads, create_resume_info, process_links, process_inputs, retrieve_or_create_job_posting_info
from utils.basic_utils import mk_dirs, binary_file_downloader_html, convert_docx_to_img
from typing import Any, List
from pathlib import Path
import re
import uuid
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import json
from json.decoder import JSONDecodeError
from utils.aws_manager import get_client
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import webbrowser
from utils.pydantic_schema import ResumeUsers
from streamlit_image_select import image_select
from backend.upgrade_resume import reformat_resume
from pages.streamlit_utils import nav_to, user_menu, progress_bar
from css.streamlit_css import general_button, primary_button, google_button
import glob
from backend.upgrade_resume import tailor_resume, evaluate_resume
from streamlit_float import *
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import plotly.graph_objects as go
from st_pages import get_pages, get_script_run_ctx 

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

STORAGE = os.environ['STORAGE']
bucket_name = os.environ["BUCKET_NAME"]
login_file = os.environ["LOGIN_FILE_PATH"]
db_path=os.environ["LANCEDB_PATH"]
user_profile_file=os.environ["USER_PROFILE_FILE"]
client_secret_json = os.environ["CLIENT_SECRET_JSON"]
lance_users_table = os.environ["LANCE_USERS_TABLE"]
placeholder_about_resume=st.empty()
# initialize float feature/capability
float_init()
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
pages = get_pages("")
ctx = get_script_run_ctx()

class User():

    ctx = get_script_run_ctx()

    def __init__(self, user_mode=None):
        # NOTE: userId is retrieved from browser cookie
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
        if self.userId:
            if "user_mode" not in st.session_state:
                st.session_state["user_mode"]="signedin"
            # if "user_profile_dict" not in st.session_state: 
            st.session_state["user_profile_dict"]=retrieve_user_profile_dict(self.userId)
        else:
            if "user_mode" not in st.session_state:  
                st.session_state["user_mode"]="signedout"
        # if user_mode:
        #     st.session_state["user_mode"]=user_mode
        self._init_session_states()
        self._init_display()

    # @st.cache_data()
    def _init_session_states(_self, ):

        # st.session_state["profile_page"]="http://localhost:8501/streamlit_user"
        # Open users login file
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
    
        # st.session_state["sagemaker_client"]=_self.aws_session.client('sagemaker-featurestore-runtime')
        # st.session_state["lancedb_conn"]= lancedb.connect(db_path)
        if _self.userId is not None:
            if STORAGE=="CLOUD":
                st.session_state["s3_client"] = get_client('s3')
                st.session_state["bucket_name"] = bucket_name
                st.session_state["storage"] = "CLOUD"
                st.session_state["user_save_path"] = os.path.join(os.environ["S3_USER_PATH"], _self.userId, "profile")
            elif STORAGE=="LOCAL":
                st.session_state["s3_client"] = None
                st.session_state["bucket_name"] = None
                st.session_state["storage"] = "LOCAL"
                st.session_state["user_save_path"] = os.path.join(os.environ["USER_PATH"], _self.userId, "profile")
            # Get the current time
            now = datetime.now()
            # Format the time as "year-month-day-hour-second"
            formatted_time = now.strftime("%Y-%m-%d-%H-%M")
            st.session_state["users_upload_path"] = os.path.join(st.session_state.user_save_path, "uploads", formatted_time)
            st.session_state["users_download_path"] =  os.path.join(st.session_state.user_save_path, "downloads", formatted_time)
            paths=[st.session_state["users_upload_path"], st.session_state["users_download_path"]]
            mk_dirs(paths, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)






    def _init_display(self):

        """ Initalizes user page according to user's sign in status"""
        st.markdown(primary_button, unsafe_allow_html=True )
        if st.session_state.user_mode!="signedout":
            user_menu(self.userId, page="profile")
        if st.session_state.user_mode=="signup":
            print("signing up")
            self.sign_up()
        elif st.session_state.user_mode=="signedout":
            print("signed out")
            self.sign_in()
        elif st.session_state.user_mode=="signedin":
            print("signed in")
            st.session_state["user_mode"]="display_profile"
            if "redirect_page" in st.session_state:
                st.switch_page(st.session_state.redirect_page)
            else:
                st.rerun()
        elif st.session_state.user_mode=="signout":
            self.sign_out()
        elif st.session_state.user_mode=="display_profile":
            if  st.session_state["user_profile_dict"]:
                self.display_profile()
            else:
                print("user profile does not exists yet")
                self.about_resume()
          
    

    @st.experimental_dialog("Warning")
    def delete_profile_popup(self):
        add_vertical_space(2)
        st.warning("Your current profile will be lost. Are you sure?")
        add_vertical_space(2)
        c1, _, c2 = st.columns([1, 1, 1])
        with c2:
            if st.button("yes, I'll upload a new profile", type="primary"):
                delete_user_from_table(lance_users_table, self.userId)
                st.session_state["user_mode"]="display_profile"
                st.rerun()
        with c1:
            if st.button("go back"):
                st.session_state["user_mode"]="display_profile"
                st.rerun()


    

    def sign_out(self, ):

        print('signing out')
        st.session_state.cm.delete_cookie()
        st.session_state["user_mode"]="signedout"
        if "redirect_page" in st.session_state:
            st.switch_page(st.session_state.redirect_page)
        else:
            st.rerun()



    def sign_in(self, ):

        _, c1, _ = st.columns([1, 1, 1])
        with c1:
            st.header("Welcome back")
            name, authentication_status, username = st.session_state.authenticator.login('', 'main')
            placeholder_error = st.empty()

            st.markdown(
                """
                <style>
                button[kind="primary"] {
                    background: none!important;
                    border: none;
                    padding: 0!important;
                    color: black !important;
                    text-decoration: none;
                    cursor: pointer;
                    border: none !important;
                }
                button[kind="primary"]:hover {
                    text-decoration: none;
                    color: blue !important;
                }
                button[kind="primary"]:focus {
                    outline: none !important;
                    box-shadow: none !important;
                    color: blue !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns([5, 1, 1])
            with col2:
                # sign_up = st.button(label="sign up", key="signup", on_click=self.sign_up, args=[authenticator], type="primary")
                sign_up = st.button(label="sign up", key="signup",  type="primary")
                if sign_up:
                    st.session_state["user_mode"]="signup"
                    st.rerun()
            with col3:
                forgot_password = st.button(label="forgot my username/password", key="forgot", type="primary") 
            st.divider()
            self.google_signin()
            print(name, authentication_status, username)
            if authentication_status:
                email = st.session_state.authenticator.credentials["usernames"][username]["email"]
                print("setting cookie")
                st.session_state.cm.set_cookie(name, email, )
                st.session_state["user_mode"]="signedin"
                time.sleep(5)
                st.rerun()
                # webbrowser.open(st.session_state.redirect_page if "redirect_page" in st.session_state else st.session_state.redirect_url)
            elif authentication_status == False:
                placeholder_error.error('Username/password is incorrect')


    def google_signin(self,):

        auth_code = st.query_params.get("code")
      
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            client_secret_json,
            scopes=["https://www.googleapis.com/auth/userinfo.email", "openid"],
            redirect_uri=st.session_state.redirect_page,
            )
        if auth_code:
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
            st.write("Login Done")
            user_info_service = build(
                serviceName="oauth2",
                version="v2",
                credentials=credentials,
            )
            user_info = user_info_service.userinfo().get().execute()
            assert user_info.get("email"), "Email not found in infos"
            # st.session_state["google_auth_code"] = auth_code
            # st.session_state["user_info"] = user_info
            st.session_state.cm.set_cookie(user_info.get("email"), user_info.get("email"),)
            st.session_state["user_mode"]="signedin"
            time.sleep(5)
            st.rerun()
        else:
            st.markdown(google_button, unsafe_allow_html=True)
            st.markdown('<span id="button-after"></span>', unsafe_allow_html=True)
            if st.button("Sign in with Google"):
                authorization_url, state = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                )
                webbrowser.open_new_tab(authorization_url)

    def sign_up(self,):

        print("inside signing up")
        _, c, _ = st.columns([1, 1, 1])
        with c:
            authenticator = st.session_state.authenticator
            username= authenticator.register_user("Create an account", "main", preauthorization=False)
            if username:
                name = authenticator.credentials["usernames"][username]["name"]
                password = authenticator.credentials["usernames"][username]["password"]
                email = authenticator.credentials["usernames"][username]["email"]
                if self.save_password( username, name, password, email):
                    # if STORAGE=="LOCAL":
                    #     user_path = os.path.join(os.environ["USER_PATH"], email)
                    # elif STORAGE=="CLOUD":
                    #     user_path = os.path.join(os.environ["USER_PATH"], email)
                    # mk_dirs([user_path], storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                    st.session_state["user_mode"]="signedin"
                    st.success("User registered successfully")
                    st.session_state.cm.set_cookie(name, email,)
                    time.sleep(5)
                    st.rerun()
                else:
                    st.info("Failed to register user, please try again")
                    st.rerun()


                    



    # def about_user2(self):

    #     # with st.form(key="about_me2", clear_on_submit=False):
    #     if st.session_state.get("self_description", False):
    #     # and st.session_state.get("current_situation", False) and st.session_state.get("career_goals", False) :
    #         st.session_state.disabled=False
    #     else:
    #         st.session_state.disabled=True
    #     selected = stx.stepper_bar(steps=["Self Description", "Job Search", "Career Goals"])
    #     if selected==0 and st.session_state.value0=="":
    #         value0 = st.text_area(
    #         label="What can I know about you?", 
    #         placeholder="Tell me about yourself, for example, what are your best motivations and values? What's important to you in a job?", 
    #         key = "self_descriptionx", 
    #         on_change=self.field_check
    #         )
    #         st.session_state["value0"]=value0
    #     elif selected==0 and st.session_state.value0!="":
    #         value0=st.text_area(
    #         label="What can I know about you?", 
    #         value=st.session_state["value0"],
    #         key = "self_descriptionx", 
    #         on_change=self.field_check
    #         )
    #         st.session_state["value0"]=value0
    #     elif selected==1 and st.session_state.value1=="":
    #         value1=st.text_area(
    #         label="What are your skills?",
    #         placeholder = "Tell me about your skills and talent? What are you especially good at that you want to bring to a workplace?",
    #         key="skill_setx",
    #         on_change =self.field_check
    #         )
    #         st.session_state["value1"]=value1
    #     elif selected==1 and st.session_state.value1!="":
    #         value1=st.text_area(
    #         label="What are your skills?",
    #         value=st.session_state["value1"],
    #         key = "skill_setx",
    #         on_change=self.field_check
    #         )
    #         st.session_state["value1"]=value1
    #     elif selected==2 and st.session_state.value2=="":
    #         value2=st.text_area(
    #         label="What can I do for you?",
    #         placeholder = "Tell me about your career goals. Where do you see yourself in 1 year? What about 10 years? What do you want to achieve in life?",
    #         key="career_goalsx",
    #         on_change=self.field_check,
    #         )
    #         st.session_state["value2"]=value2
    #     elif selected==2 and st.session_state.value2!="":
    #         value2=st.text_area(
    #         label="What can I do for you?",
    #         value=st.session_state["value2"],
    #         key = "career_goalsx",
    #         on_change=self.field_check
    #         )
    #         st.session_state["value2"]=value2
        
    #     submitted = st.button("Submit", on_click=self.form_callback2, disabled=st.session_state.disabled)
    #     skip = st.button(label="skip", help="You can come back to this later, but remember, the more information you provide, the better your job search results", type="primary", on_click=self.form_callback2)
        # if submitted:
        #     st.session_state["init_user2"]=True

    
    def about_resume(self):

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
                                on_change=self.field_check, 
                                help="This will become your default resume.")
            add_vertical_space(3)
            _, c1 = st.columns([5, 1])
            with c1:
                # st.markdown(general_button, unsafe_allow_html=True)
                # st.markdown('<span class="general-button"></span>', unsafe_allow_html=True)
                if st.button(label="Submit", disabled=st.session_state.resume_disabled):
                    self.resume_form_callback()
                if st.button(label="I'll do it later", type="primary",):
                    self.display_profile()

    def about_future(self):

        st.text_area("Where do you see yourself in 5 years?")




    def about_bio(self):

        c1, c2 = st.columns(2)
        with c1:
            #TODO: check default value for user who wants to change their profile info
            st.text_input("Full name *", key="namex", 
                            value= st.session_state["users"][self.userId]["name"] if self.userId in st.session_state["users"] and "name" in st.session_state["users"][self.userId] else "", 
                            on_change=self.field_check)
        with c2:
            st.date_input("Date of Birth *", date.today(), min_value=date(1950, 1, 1), key="birthdayx", on_change=self.field_check)
        st.text_input("LinkedIn", key="linkedinx", on_change=self.field_check)


    def about_career(self):

        c1, c2 = st.columns([1, 1])
        # components.html( """<div style="text-align: bottom"> Work Experience</div>""")
        with c1:
            st.text_input("Desired job title(s)", placeholder="please separate each with a comma", key="jobx", on_change=self.field_check)
        with c2:
            st.select_slider("Level of experience",  options=["no experience", "entry level", "junior level", "mid level", "senior level"], key='job_levelx', on_change=self.field_check)   
        c1, c2=st.columns([1, 1])
        with c1:
            min_pay = st.text_input("Minimum pay", key="min_payx", on_change=self.field_check)
        with c2: 
            pay_type = st.selectbox("", ("hourly", "annually"), index=None, placeholder="Select pay type...", key="pay_typex", on_change=self.field_check)
        job_unsure=st.checkbox("Not sure about the job")
        if job_unsure:
            st.multiselect("What industries interest you?", ["Healthcare", "Computer & Technology", "Advertising & Marketing", "Aerospace", "Agriculture", "Education", "Energy", "Entertainment", "Fashion", "Finance & Economic", "Food & Beverage", "Hospitality", "Manufacturing", "Media & News", "Mining", "Pharmaceutical", "Telecommunication", " Transportation" ], key="industryx", on_change=self.field_check)
        career_switch = st.checkbox("Career switch", key="career_switchx", on_change=self.field_check)
        if career_switch:
            st.text_area("Transferable skills", placeholder="Please separate each transferable skill with a comma", key="transferable_skillsx", on_change=self.field_check)
        location = st.checkbox("Location is important to me")
        # location = st.radio("Is location important to you?", [ "no, I can relocate","I only want to work remotely", "I want to work near where I currently live", "I have a specific place in mind"], key="locationx", on_change=self.field_check)
        if location:
            location_input = st.radio("", ["I want remote work", "work near where I currently live", "I have a specific place in mind"])
            if location_input=="I want remote work":
                st.session_state.location_input = "remote"
            if location_input == "I have a specific place in mind":
                st.text_input("Location", "e.g., the west coast, NYC, or a state", key="location_inputx", on_change=self.field_check)
            if location_input == "work near where I currently live":
                if st.checkbox("Share my location"):
                    loc = get_geolocation()
                    if loc:
                        address = self.get_address(loc["coords"]["latitude"], loc["coords"]["longitude"])
                        st.session_state["location_input"] = address


    def about_education(self):

        c1, c2 = st.columns([1, 1])
            # st.text_input("School", key="schoolx")
        with c2:
            st.text_input("Year of Graduation (if applicable)", key="grad_yearx", on_change=self.field_check)
        with c1:
            degree = st.selectbox("Highest level of education *", index=None, options=("Did not graduate high school", "High school diploma", "Associate's degree", "Bachelor's degree", "Master's degree", "Professional degree"), key="degreex", placeholder = "Select your highest level of education", on_change=self.field_check)
        if degree=="Associate's degree" or degree=="Bachelor's degree" or degree=="Master's degree" or degree=="Professional degree":
            st.text_input("Area(s) of study", key="studyx", placeholder="please separate each with a comma", on_change=self.field_check)
        certification = st.checkbox("Other certifications")
        if certification:
            st.text_area("", key="certificationx", placeholder="Please write out the full name of each certification chronologically and separate them with a comma", on_change=self.field_check)



    def resume_form_callback(self, ):
        """"""
        resume_dict = create_resume_info(st.session_state.user_resume_path,)
        resume_dict.update({"resume_path":st.session_state.user_resume_path})
        resume_dict.update({"user_id": self.userId}) 
        #NOTE: the data added has to be a LIST!
        schema = convert_pydantic_schema_to_arrow(ResumeUsers)
        add_to_lancedb_table(lance_users_table, [resume_dict], schema)
        print("Successfully aded user to lancedb table")
        st.rerun()



    # def test_clear(self):
        
    #     vectorstore = retrieve_vectorstore("elasticsearch", index_name=self.userId)
    #     record_manager=create_record_manager(self.userId)
    #     print(f"record manager keys: {record_manager.list_keys()}")
    #     clear_index(record_manager, vectorstore)
    #     print(f"record manager keys: {record_manager.list_keys()}")

    def get_address(self, latitude, longitude):

        """Retrieves the address of user's current location """

        geolocator = Nominatim(user_agent="nearest_city_finder")
        try:
            location = geolocator.reverse((latitude, longitude), exactly_one=True)
            print(location.address)
            return location.address
        except GeocoderTimedOut:
            # Retry after a short delay
            return self.get_address(latitude, longitude)
        
    def field_check(self):

        # Hacky way to save input text for stepper bar for batch submission
        try:
            st.session_state["self_description"] = st.session_state.self_descriptionx
            st.session_state["users"][self.userId]["self_description"] = st.session_state.self_description
        except AttributeError:
            pass
        try:
            st.session_state["skill_set"] = st.session_state.skill_setx
            st.session_state["users"][self.userId]["skill_set"] = st.session_state.skill_set
        except AttributeError:
            pass
        try:
            st.session_state["career_goals"] = st.session_state.career_goalsx
            st.session_state["users"][self.userId]["career_goals"] = st.session_state.career_goals
        except AttributeError:
            pass
        try:
            st.session_state["name"] = st.session_state.namex
            st.session_state["users"][self.userId]["name"] = st.session_state.name
        except AttributeError:
            pass
        try:
            birthday = st.session_state.birthdayx
            self.process("birthday", birthday)
            st.session_state["users"][self.userId]["birthday"] = st.session_state.birthday
        except AttributeError:
            pass
        try:
            linkedin = st.session_state.linkedinx
            if linkedin:
                process_linkedin(st.session_state.linkedinx)
                st.session_state["users"][self.userId]["linkedin"] = st.session_state.linkedin
        except AttributeError:
            pass
        try:
            st.session_state["grad_year"] = st.session_state.grad_yearx
            st.session_state["users"][self.userId]["graduation_year"] = st.session_state.grad_year
        except AttributeError:
            pass
        try:
            st.session_state["degree"] = st.session_state.degreex
            st.session_state["users"][self.userId]["degree"] = st.session_state.degree
        except AttributeError:
            pass
        try:
            study = st.session_state.studyx
            self.process("study", study)
            st.session_state["users"][self.userId]["study"] = st.session_state.study
        except AttributeError:
            pass
        try:
            certification = st.session_state.certificationx 
            self.process("certification", certification)
            st.session_state["users"][self.userId]["certification"] = st.session_state.certification
        except AttributeError:
            pass
        try:
            job = st.session_state.jobx
            self.process("job", job)
            st.session_state["users"][self.userId]["job"] = st.session_state.job
        except AttributeError:
            pass
        try:
            st.session_state["job_level"] = st.session_state.job_levelx
            st.session_state["users"][self.userId]["job_level"] = st.session_state.job_level
        except AttributeError:
            pass
        try:
            st.session_state["min_pay"] = st.session_state.min_payx
            st.session_state["users"][self.userId]["mininum_pay"] = st.session_state.min_pay
        except AttributeError:
            pass
        try:
            st.session_state["pay_type"] = st.session_state.pay_typex
            st.session_state["users"][self.userId]["pay_type"] = st.session_state.pay_type
        except AttributeError:
            pass
        
        # try:
        #     st.session_state["career_switch"] = st.session_state.career_switchx
        #     st.session_state["users"][self.userId]["career_switch"] = st.session_state.career_switch
        # except AttributeError:
        #     pass
        try:
            transferable_skills = st.session_state.transferable_skillsx
            self.process("transferable_skills", transferable_skills)
            st.session_state["users"][self.userId]["transferable_skills"] = st.session_state.transferable_skills
        except AttributeError:
            pass
        try:
            st.session_state["industry"] = st.session_state.industryx
            st.session_state["users"][self.userId]["industry"] = st.session_state.industry
        except AttributeError:
            pass
        try:
            location_input = st.session_state.location_inputx
            self.process("location_input", location_input)
            st.session_state["users"][self.userId]["location_input"] = st.session_state.location_input
        except AttributeError:
            pass
        try:
            resume = st.session_state.user_resume
            if resume:
                self.process([resume], "resume")
        except AttributeError:
            pass


    def process(self, input_value: Any, input_type:str):
        if input_type=="resume":
            result = process_uploads(input_value, st.session_state.user_save_path, "")
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="resume":
                    st.session_state["user_resume_path"]= end_path
                else:
                    print("user didn't upload resume")
                    st.info("Please upload your resume here")
            else:
                print("upload didn't work")
                st.info("That didn't work, please try again.")
        elif input_type=="job_posting":
            result = process_links(input_value, st.session_state.save_path, st.session_state.sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="job posting":
                    st.session_state["job_posting_path"]=end_path
                else:
                    # st.session_state.job_posting_checkmark=":red[*]"
                    st.info("Please upload your job posting link here")
            else:
                st.info("That didn't work. Please try pasting the content in job description instead.")
        elif input_type=="job_description":
            result = process_inputs(input_value, match_topic="job posting or job description")
            if result is not None:
                st.session_state["job_description"] = input_value
            else:
                st.info("Please share a job description here")

        if input_type=="location_input":
            st.session_state.location_input=input_value.split(",")
        elif input_type=="transferable_skills":
            st.session_state.transferable_skills=input_value.split(",")



    @st.experimental_fragment()
    def update_skills(self, ):

        def get_display():
            c1, c2=st.columns([1, 1])
            with c1:
                with st.container(border=True):
                    st.write("Your skills")
                    for idx, skill in enumerate(self.skills_set):
                        x = st.button(skill+" :red[x]", key=f"remove_skill_{idx}", on_click=skills_callback, args=(idx, skill, ))
            with c2:
                st.write("Suggested skills to include")
                for idx, skill in enumerate(self.generated_skills_set):
                    y = st.button(skill +" :green[o]", key=f"add_skill_{idx}", on_click=skills_callback, args=(idx, skill, ))
            st.text_input("Add a skill not from the suggestion", key="add_skill_custom", on_change=skills_callback, args=("", "", ))
            
        def skills_callback(idx, skill):
            try:
                new_skill = st.session_state.add_skill_custom
                if new_skill:
                    self.skills_set.add(new_skill)
                    st.session_state["profile"]["included_skills"]=list(self.skills_set)
                    st.session_state.add_skill_custom=''
            except Exception:
                    pass
            try:
                name = f"add_skill_{idx}"
                add_skill = st.session_state[name]
                if add_skill:
                    # print('add skill', skill)
                    self.skills_set.add(skill)
                    st.session_state["profile"]["included_skills"]=list(self.skills_set)
                    self.generated_skills_set.remove(skill)
                    st.session_state["profile"]["suggested_skills"]=[i for i in st.session_state["profile"]["suggested_skills"] if not (i["skill"] == skill)]
            except Exception:
                pass
            try:
                name = f"remove_skill_{idx}"
                remove_skill = st.session_state[name]
                if remove_skill:
                    # print('remove skill', skill)
                    self.skills_set.remove(skill)
                    st.session_state["profile"]["included_skills"]=list(self.skills_set)
            except Exception:
                pass
        return get_display


    @st.experimental_fragment()
    def display_field_details(self, field_name, x, field_detail, type):

        def get_display():
            
            if x!=-1:
                field_list = st.session_state["profile"][field_name][x][field_detail]
            else:
                field_list = st.session_state["profile"][field_name][field_detail]
            for idx, value in enumerate(field_list):
                add_detail(value, idx,)
            if type=="bullet_points":
                c1, c2, y = st.columns([1, 20, 1])
                with y: 
                    st.button("**+**", key=f"add_{field_name}_{field_detail}_{x}", on_click=add_new_entry, help="add a bullet point description", use_container_width=True)

        def delete_entry(placeholder, idx):
            if type=="bullet_points":
                if x!=-1:
                    del st.session_state["profile"][field_name][x][field_detail][idx]
                else:
                    del st.session_state["profile"][field_name][field_detail][idx]
            placeholder.empty()

        def add_new_entry():
            print("added new entry")
            if type=="bullet_points":
                if x!=-1:
                    st.session_state["profile"][field_name][x][field_detail].append("")
                else:
                    st.session_state["profile"][field_name][field_detail].append("")

        def add_detail(value, idx,):
            
            placeholder = st.empty()
            if type=="bullet_points":
                with placeholder.container():
                    c1, c2, x_col = st.columns([1, 20, 1])
                    with c1:
                        st.write("•")
                    with c2: 
                        text = st.text_input(" " , value=value, key=f"descr_{field_name}_{x}_{field_detail}_{idx}", label_visibility="collapsed", on_change=callback, args=(idx, ), )
                    with x_col:
                        st.button("**x**", type="primary", key=f"delete_{field_name}_{x}_{field_detail}_{idx}", on_click=delete_entry, args=(placeholder, idx, ) )

        def callback(idx, ):
            
            try:
                new_entry = st.session_state[f"descr_{field_name}_{x}_{field_detail}_{idx}"]
                if new_entry:
                    if x!=-1:
                        st.session_state["profile"][field_name][x][field_detail][idx] = new_entry
                    else:
                        st.session_state["profile"][field_name][field_detail][idx] = new_entry
            except Exception as e:
                pass


        return get_display


    @st.experimental_fragment()   
    def display_field_content(self, name):

        """"""
        #TODO: FUTURE USING DRAGGABLE CONTAINERS TO ALLOW REORDER CONTENT https://discuss.streamlit.io/t/draggable-streamlit-containers/72484?u=yueqi_peng
        def get_display():
            for idx, value in enumerate(st.session_state["profile"][name]):
                add_container(idx, value)
            st.button("add", key=f"add_{name}_button", on_click=add_new_entry, use_container_width=True)
                  
        def add_new_entry():
            if name=="certifications" or name=="licenses":
                st.session_state["profile"][name].append({"description":[],"issue_date":"", "issue_organization":"", "title":""})
            elif name=="work_experience":
                st.session_state["profile"][name].append({"company":"","description":[],"end_date":"","job_title":"","location":"","start_date":""})
            elif name=="awards":
                st.session_state["profile"][name].append({"description":[],"title":""})
            elif name=="projects" or name=="qualifications":
                st.session_state["profile"][name].append({"description":[],"title":""})
            
        def delete_container(placeholder, idx):
            print("deleted", st.session_state["profile"][name][idx])
            del st.session_state["profile"][name][idx]
            placeholder.empty()


        def add_container(idx, value):

            placeholder=st.empty()
            with placeholder.container(border=True):
                c1, x = st.columns([18, 1])
                # with c1:
                #     st.write(f"**{name} {idx}**")
                with x:
                    st.button("**x**", type="primary", key=f"{name}_delete_{idx}", on_click=delete_container, args=(placeholder, idx) )
                if name=="awards" or name=="projects" or name=="qualifications":
                    title = value["title"]
                    # description = value["description"]
                    st.text_input("Title", value=title, key=f"{name}_title_{idx}", on_change=callback, args=(idx, ))
                    # st.text_input("Description", value=title, key=f"award_descr_{idx}", on_change=callback, args=(idx, ))
                    get_display= self.display_field_details(name, idx, "description", "bullet_points")
                    get_display()
                elif name=="certifications" or name=="licenses":
                    title = value["title"]
                    organization = value["issue_organization"]
                    date = value["issue_date"]
                    # description = value["description"]
                    st.text_input("Title", value=title, key=f"{name}_title_{idx}", on_change=callback, args=(idx, ))
                    st.text_input("Issue organization", value=organization, key=f"{name}_org_{idx}", on_change=callback, args=(idx, ))
                    st.text_input("Issue date", value=date, key=f"{name}_date_{idx}", on_change=callback, args=(idx, ))
                    # st.text_area("Description", value=description, key=f"{name}_descr_{idx}", on_change=callback, args=(idx,) )
                    get_display= self.display_field_details(name, idx, "description", "bullet_points")
                    get_display()
                elif name=="work_experience":
                    job_title = value["job_title"]
                    company = st.session_state["profile"][name][idx]["company"]
                    start_date = st.session_state["profile"][name][idx]["start_date"]
                    end_date = st.session_state["profile"][name][idx]["end_date"]
                    # descriptions = st.session_state["profile"][name][idx]["description"]
                    location = st.session_state["profile"][name][idx]["location"]
                    c1, c2, c3= st.columns([2, 1, 1])
                    with c1:
                        st.text_input("Job title", value = job_title, key=f"experience_title_{idx}", on_change=callback,args=(idx,)  )
                        st.text_input("Company", value=company, key=f"company_{idx}", on_change=callback,args=(idx,)  )
                    with c2:
                        st.text_input("start date", value=start_date, key=f"start_date_{idx}", on_change=callback,args=(idx,)  )
                        st.text_input("Location", value=location, key=f"experience_location_{idx}", on_change=callback,  args=(idx,) )
                    with c3:
                        st.text_input("End date", value=end_date, key=f"end_date_{idx}", on_change=callback, args=(idx,) )
                    # for x, descr in enumerate(descriptions):
                    #     # st.text_input("-", value=descr, key=f"experience_descr_{idx}_{x}", on_change=callback, )
                    #     # st.write("-" + descr)
                    get_display= self.display_field_details("work_experience", idx, "description", "bullet_points")
                    get_display()
                

        def callback(idx):
       
            # try:
            #     title = st.session_state[f"award_title_{idx}"]
            #     if title:
            #         st.session_state["profile"]["awards"][idx]["title"]=title
            # except Exception:
            #     pass
            # try:
            #     descr = st.session_state[f"award_descr_{idx}"]
            #     if descr:
            #         st.session_state["profile"]["awards"][idx]["description"]=descr
            # except Exception:
            #     pass
            try:
                title = st.session_state[f"{name}_title_{idx}"]
                if title:
                    st.session_state["profile"][name][idx]["title"]=title
            except Exception:
                pass
            try:
                date = st.session_state[f"{name}_date_{idx}"]
                if date:
                    st.session_state["profile"][name][idx]["issue_date"]=date
            except Exception:
                pass
            try:
                date = st.session_state[f"{name}_org_{idx}"]
                if date:
                    st.session_state["profile"][name][idx]["issue_date"]=date
            except Exception:
                pass
            try:
                descr = st.session_state[f"{name}_descr_{idx}"]
                if descr:
                    st.session_state["profile"][name][idx]["description"]=descr
            except Exception:
                pass
            try:
                title = st.session_state[f"experience_title_{idx}"]
                if title:
                    # self.experience_list[idx]["job_title"] = title
                    st.session_state["profile"]["work_experience"][idx]["job_title"] = title
            except Exception:
                pass
            try:
                company = st.session_state[f"company_{idx}"]
                if company:
                    # self.experience_list[idx]["company"] = company
                    st.session_state["profile"]["work_experience"][idx]["company"] = company
            except Exception:
                pass
            try:
                start_date = st.session_state[f"start_date_{idx}"]
                if start_date:
                    st.session_state["profile"]["work_experience"][idx]["start_date"] =start_date
            except Exception:
                pass
            try:
                end_date = st.session_state[f"end_date_{idx}"]
                if end_date:
                    st.session_state["profile"]["work_experience"][idx]["end_date"] = end_date
            except Exception:
                pass
            try:
                location = st.session_state[f"experience_location_{idx}"]
                if location:
                    st.session_state["profile"]["work_experience"][idx]["location"] = location
            except Exception:
                pass
            try:
                experience_description = st.session_state[f"experience_description_{idx}"]
                if experience_description:
                    # self.experience_list[idx]["description"] = experience_description
                    st.session_state["profile"]["work_experience"][idx]["description"] = experience_description
            except Exception:
                pass
            
        return get_display

    def display_field_eval_tailor(self, field_name):

        _, c1, c2 = st.columns([4, 1, 1])
        with c1:
            if f"evaluated_{field_name}" in st.session_state:
                with st.popover("Show evaluation"):
                    evaluation = st.session_state[f"evaluated_{field_name}"]
                    st.write(evaluation)
                    st.button("evaluate again ✨", key=f"eval_again_{field_name}_button", on_click=self.evaluation_callback, args=(field_name, ), )
            else:
                evaluate = st.button("evaluate ✨", key=f"eval_{field_name}_button", on_click=self.evaluation_callback, args=(field_name, ), )
        with c2:
            if f"tailored_{field_name}" in st.session_state:
                with st.popover("Show tailoring"):
                    tailoring = st.session_state[f"tailored_{field_name}"]
                    st.write(tailoring)
            else:
                tailor = st.button("tailor ✨",key=f"tailor_{field_name}_button", on_click=self.tailor_callback, args=(field_name, ))
          

    @st.experimental_dialog("Please provide a job posting")   
    def job_posting_popup(self, field_name):


        if "job_posting_path" in st.session_state or "job_description" in st.session_state:
            st.session_state["job_posting_disabled"]=False
        else:
            st.session_state["job_posting_disabled"]=True
        job_posting = st.radio(f" ", 
                                key="job_posting_radio", options=["job description", "job posting link"], 
                                index = 1 if "job_description"  not in st.session_state else 0
                                )
        if job_posting=="job posting link":
            job_posting_link = st.text_input(label="Job posting link",
                                            key="job_posting", 
                                            )
            if job_posting_link:
                self.process(job_posting_link, "job_posting")
        elif job_posting=="job descriptsion":
            job_description = st.text_area("Job description", 
                                        key="job_descriptionx", 
                                        value=st.session_state.job_description if "job_description" in st.session_state else "",
                                            )
            if job_description:
                self.process(job_description, "job_description")
        st.button("Next", disabled=st.session_state.job_posting_disabled, on_click=self.tailor_callback, args=(field_name, ),)

    
    def tailor_callback(self, field_name):
        if "job_posting_dict" in st.session_state:
            tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"], field_name)
        elif "job_posting_path" in st.session_state or "job_description" in st.session_state:
                st.session_state["job_posting_dict"] = retrieve_or_create_job_posting_info(
                st.session_state.job_posting_path if "job_posting_path" in st.session_state and st.session_state.job_posting_radio=="job posting link" else "",
                st.session_state.job_description if "job_description" in st.session_state and st.session_state.job_posting_radio=="job description" else "",  
            )
                self.tailor_callback(field_name)
        else:
            self.job_posting_popup(field_name)
            # st.session_state["tailor_dict"]=tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"])

    def evaluation_callback(self, field_name=None, redo=False):
        self.display_general_evaluation()
        if field_name:
            evaluate_resume(resume_dict=st.session_state["profile"], type=field_name,)
        else:
            if redo:
                del st.session_state["eval_dict"]
                del st.session_state["finished_eval"]
                del st.session_state["eval_button"]
            if "finished_eval" not in st.session_state:
                evaluate_resume(resume_dict=st.session_state["profile"], type="general")
            

    
    def display_profile(self,):

        """Loads from user file and displays profile"""
        # st.subheader("Your Profile")

        current_page = self.get_current_page()
        progress_bar(current_page["page_name"])
        # self.updated_dict = {}
        if "profile" not in st.session_state:
            st.session_state["profile"]=st.session_state["user_profile_dict"]
        eval_col, profile_col = st.columns([1, 2])
                
        with profile_col:
            c1, c2 = st.columns([1, 1])
            with c1:
                with st.expander(label="Contact", expanded=True ):
                    name = st.session_state["profile"]["contact"]["name"]
                    if st.text_input("Name", value=name, key="profile_name",)!=name:
                        st.session_state["profile"]["contact"]["name"]=st.session_state.profile_name
                    email = st.session_state["profile"]["contact"]["email"]
                    if st.text_input("Email", value=email, key="profile_email", )!=email:
                        value = st.session_state["profile"]["contact"]["email"] = st.session_state.profile_email
                    phone = st.session_state["profile"]["contact"]["phone"]
                    if st.text_input("Phone", value=phone, key="profile_phone", )!=phone:
                        st.session_state["profile"]["contact"]["phone"]=st.session_state.profile_phone
                    city = st.session_state["profile"]["contact"]["city"]
                    if st.text_input("City", value=city, key="profile_city", )!=city:
                        st.session_state["profile"]["contact"]["city"]=st.session_state.profile_city
                    state = st.session_state["profile"]["contact"]["state"]
                    if st.text_input("State", value=state, key="profile_state", )!=state:
                        st.session_state["profile"]["contact"]["state"]=st.session_state.profile_state
                    linkedin = st.session_state["profile"]["contact"]["linkedin"]
                    if st.text_input("Linkedin", value=linkedin, key="profile_linkedin", )!=linkedin:
                        st.session_state["profile"]["contact"]["linkedin"]=st.session_state.profile_linkedin
                    website = st.session_state["profile"]["contact"]["website"]
                    if st.text_input("Personal website", value=website, key="profile_website", )!=website:
                        st.session_state["profile"]["contact"]["website"]=st.session_state.profile_website
            with c2:
                with st.expander(label="Education", expanded=True):
                    degree = st.session_state["profile"]["education"]["degree"]
                    if st.text_input("Degree", value=degree, key="profile_degree", )!=degree:
                        # self.updated_dict.update({"degree":st.session_state.profile_degree})
                        st.session_state["profile"]["education"]["degree"]=st.session_state.profile_degree
                    study = st.session_state["profile"]["education"]["study"]
                    if st.text_input("Area of study", value=study, key="profile_study", )!=study:
                        # self.updated_dict.update({"degree":st.session_state.profile_study})
                        st.session_state["profile"]["education"]["study"]=st.session_state.profile_study
                    grad_year = st.session_state["profile"]["education"]["graduation_year"]
                    if st.text_input("Graduation year", value=grad_year, key="profile_grad_year", )!=grad_year:
                        # self.updated_dict.update({"graduation_year":st.session_state.profile_grad_year})
                        st.session_state["profile"]["education"]["graduation_year"]=st.session_state.profile_grad_year
                    gpa = st.session_state["profile"]["education"]["gpa"]
                    if st.text_input("GPA", value=gpa, key="profile_gpa", )!=gpa:
                        # self.updated_dict.update({"gpa":st.session_state.profile_gpa})
                        st.session_state["profile"]["education"]["gpa"]=st.session_state.profile_gpa
                    st.markdown("Course works")
                    display_detail=self.display_field_details("education", -1, "coursework", "bullet_points")
                    display_detail()
                    # #TODO list courseworks
            with st.expander(label="Summary/Objective",):
                self.display_field_eval_tailor("summary")
                summary = st.session_state["profile"]["summary_objective"]
                if st.text_area("Summary", value=summary, key="profile_summary", label_visibility="hidden")!=summary:
                    # self.updated_dict.update({"summary_objective_section":st.session_state.profile_summary})
                    st.session_state["profile"]["summary_objective"] = st.session_state.profile_summary
            with st.expander(label="Work experience",):
                self.display_field_eval_tailor("work_experience")
                get_display=self.display_field_content("work_experience")
                get_display()
            with st.expander(label="Skills",):
                self.display_field_eval_tailor("skills")
                included_skills = st.session_state["profile"]["included_skills"]
                suggested_skills = st.session_state["profile"]["suggested_skills"]
                self.skills_set= set(included_skills)
                self.generated_skills_set=set()
                # for skill in included_skills:
                #     self.skills_set.add(skill["skill"])
                for skill in suggested_skills:
                    self.generated_skills_set.add(skill["skill"])
                get_display=self.update_skills()
                get_display()
            c1, c2 = st.columns([1, 1])
            with c1:
                with st.expander(label="Professional Accomplihsment/Qualifications"):
                    st.page_link("https://www.indeed.com/career-advice/resumes-cover-letters/listing-accomplishments-on-your-resume", 
                                 label="learn more")
                    get_display=self.display_field_content("qualifications")
                    get_display()
            with c2:
                with st.expander(label="Projects"):
                    get_display=self.display_field_content("projects")
                    get_display()
            c1, c2, c3=st.columns([1, 1, 1])
            with c1:
                with st.expander(label="Certifications", ):
                    get_display=self.display_field_content("certifications")
                    get_display()
            with c2:
                with st.expander("Awards & Honors"):
                    get_display=self.display_field_content("awards")
                    get_display()
            with c3:
                with st.expander("Licenses"):
                    get_display=self.display_field_content("licenses")
                    get_display()
            #TODO, allow custom fields with custom field details such as bullet points, dates, links, etc. 
            # placeholder = st.empty()
            # st.button("Add Custom Field", on_click=self.add_custom_field, args=(placeholder, ))
            st.divider()
            c1, c2, c3 = st.columns([1, 1, 1])
            with c3:
                st.button("Set as default", key="profile_save_button", on_click=save_user_changes, args=(self.userId, ResumeUsers,))
                st.button("Upload a new resume", on_click=self.delete_profile_popup,  )
        with eval_col:
            # float_container= st.container()
            # with float_container:
                self.evaluation_callback()
                # float_parent()
                # if "finished_eval" not in st.session_state:
                #     self.display_evaluation()
                #     evaluate_resume(resume_dict=st.session_state["profile"], type="general")
                # else:
                #     self.display_evaluation()
        


    def get_dict(self, type):
        
        if type=="evaluation":
            try:
                eval_dict= st.session_state["eval_dict"]
            except Exception:
                eval_dict={}
            finally:
                return eval_dict
        elif type=="tailoring":
            try:
                tailor_dict = st.session_state["tailor_dict"]
            except Exception:
                tailor_dict={}
            finally:
                return tailor_dict

    
    @st.experimental_fragment(run_every=3)
    def display_general_evaluation(self, ):

            eval_dict= self.get_dict("evaluation")
            st.write("**Length**")
            try:
                length=eval_dict["word_count"]
                pages=eval_dict["page_number"]
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = length,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Your length"}))
                st.plotly_chart(fig, 
                                # use_container_width=True
                                )
                # st.write(f"Yours: {length} words & {pages}")
            except Exception:
                st.write("Evaluating...")
            st.write("**Type**")
            # st.button("explore template options", key="explore")
            try:
                ideal_type = eval_dict["ideal_type"]
                st.write(f"The ideal type for your resume: \n{ideal_type}")
                # my_type = eval_dict["type"]
                # st.write(f"Your resume type: \n {my_type}")
            except Exception:
                st.write("Evaluating...")
            st.write("**Comparison**")
            # st.write("How close does your resume compare to others of the same industry?")
            try:
                work_comparison = eval_dict["comparison"]["work_experience_section"]
                skills_comparison = eval_dict["comparison"]["skills_section"]
                summary_comparison = eval_dict["comparion"]["summary_objective"]
                st.write("work: "+ work_comparison)
                st.write("skills: " + skills_comparison)
                st.write("summary: " + summary_comparison)
                # {"work_experience":work_comparison, "skills":skills_comparison, "summary":summary_comparison}
                # st.scatter_chart()
            except Exception:
                st.write("Evaluating...")
            st.write("**Impression**")
            try:
                cohesiveness = eval_dict["cohesiveness"]
                st.write(cohesiveness)
                st.session_state["finished_eval"] = True
            except Exception:
                st.write("Evaluating...")
            again = st.button("evaluate again ✨", key=f"eval_button", on_click=self.evaluation_callback, args=(None, True, ))







    def save_password(self, username, name, password, email, filename=login_file):

        try:
            # hashed_password = hash_password(password)
            # print("hashed password", hashed_password)
            with open(filename, 'r') as file:
                credentials = yaml.safe_load(file)
                print(credentials)
                # Add the new user's details to the dictionary
            credentials['credentials']['usernames'][username] = {
                'email': email,
                'name': name,
                'password': password
            }  
            with open(filename, 'w') as file:
                yaml.dump(credentials, file)
            return True
        except Exception as e:
            return False
        
    def get_current_page(self, ):
        try:
            current_page = pages[ctx.page_script_hash]
        except KeyError:
            current_page = [
                p for p in pages.values() if p["relative_page_hash"] == ctx.page_script_hash
            ][0]
        print("Current page:", current_page)
        return current_page

        





if __name__ == '__main__':
    # if "force_user_mode" in st.session_state:
    #     if st.session_state.force_user_mode == "signout":
    #         user = User("signout")
    #     elif st.session_state.force_user_mode == "display_profile":
    #         user=User("display_profile")
    # else:
        user=User()
    

