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
from utils.lancedb_utils import create_lancedb_table, add_to_lancedb_table, query_lancedb_table, retrieve_lancedb_table
from utils.common_utils import check_content, process_linkedin, create_profile_summary, process_uploads, create_resume_info
from utils.basic_utils import mk_dirs
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
from utils.streamlit_utils import nav_to, retrieve_user_profile_dict
from utils.pydantic_schema import ResumeUsers



# st.set_page_config(layout="wide")
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

STORAGE = os.environ['STORAGE']
bucket_name = os.environ["BUCKET_NAME"]
login_file = os.environ["LOGIN_FILE_PATH"]
db_path=os.environ["LANCEDB_PATH"]
user_profile_file=os.environ["USER_PROFILE_FILE"]
cookie_name = os.environ["COOKIE_NAME"]
cookie_key=os.environ["COOKIE_KEY"]
client_secret_json = os.environ["CLIENT_SECRET_JSON"]
lance_users_table = os.environ["LANCE_USERS_TABLE"]
# store = FeatureStore("./my_feature_repo/")

# st.set_page_config(initial_sidebar_state="collapsed")

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

class User():


    def __init__(self, user_mode=None):
        # NOTE: userId is retrieved from browser cookie
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
        if self.userId:
            st.session_state["user_mode"]="signedin" 
            if "user_profile_dict" not in st.session_state:
                if "user_profile_dict" not in st.session_state:
                    st.session_state["user_profile_dict"]=retrieve_user_profile_dict(self.userId)
        else:
            if "user_mode" not in st.session_state or (st.session_state["user_mode"]!="signup" and st.session_state["user_mode"]!="signedin"):  
                st.session_state["user_mode"]="signedout"
        if user_mode:
            st.session_state["user_mode"]=user_mode
        self._init_session_states()
        self._init_display()

    # @st.cache_data()
    def _init_session_states(_self, ):

        st.session_state["redirect_uri"]="http://localhost:8501/"
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
            paths=[
                os.path.join(st.session_state.user_save_path,),
                os.path.join(st.session_state.user_save_path, "uploads"),
                ]
            mk_dirs(paths, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)






    def _init_display(self):

        """ Initalizes user page according to user's sign in status"""
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
        # config = st.session_state["config"]
        
        # authenticator = stauth.Authenticate( config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'], config['preauthorized'] )
        if st.session_state.user_mode=="signup":
            print("signing up")
            self.sign_up()
        elif st.session_state.user_mode=="signedout":
            print("signed out")
            self.sign_in()
        elif st.session_state.user_mode=="signedin":
            print("signed in")
            nav_to(st.session_state.redirect_page if "redirect_page" in st.session_state else st.session_state.redirect_uri)
        elif st.session_state.user_mode=="display_profile":
            if "user_profile_dict" in st.session_state:
                self.display_profile()
            else:
                print("user profile does not exists yet")
                self.about_resume()

    
    

    def sign_out(self, ):

        # logout = st.session_state.authenticator.logout('Logout', 'sidebar')
        print('signing out')
        st.session_state.cm.delete_cookie()
        st.session_state["user_mode"]="signedout"
        st.rerun()



    def sign_in(self, ):


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
        st.markdown("""
        <style>.element-container:has(#button-after) + div button {
                cursor: pointer;
                transition: background-color .3s, box-shadow .3s;
                    
                padding: 12px 16px 12px 42px;
                border: none;
                border-radius: 3px;
                box-shadow: 0 -1px 0 rgba(0, 0, 0, .04), 0 1px 1px rgba(0, 0, 0, .25);
                
                color: #757575;
                font-size: 14px;
                font-weight: 500;
                font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,Cantarell,"Fira Sans","Droid Sans","Helvetica Neue",sans-serif;
                
                background-image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTgiIGhlaWdodD0iMTgiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGcgZmlsbD0ibm9uZSIgZmlsbC1ydWxlPSJldmVub2RkIj48cGF0aCBkPSJNMTcuNiA5LjJsLS4xLTEuOEg5djMuNGg0LjhDMTMuNiAxMiAxMyAxMyAxMiAxMy42djIuMmgzYTguOCA4LjggMCAwIDAgMi42LTYuNnoiIGZpbGw9IiM0Mjg1RjQiIGZpbGwtcnVsZT0ibm9uemVybyIvPjxwYXRoIGQ9Ik05IDE4YzIuNCAwIDQuNS0uOCA2LTIuMmwtMy0yLjJhNS40IDUuNCAwIDAgMS04LTIuOUgxVjEzYTkgOSAwIDAgMCA4IDV6IiBmaWxsPSIjMzRBODUzIiBmaWxsLXJ1bGU9Im5vbnplcm8iLz48cGF0aCBkPSJNNCAxMC43YTUuNCA1LjQgMCAwIDEgMC0zLjRWNUgxYTkgOSAwIDAgMCAwIDhsMy0yLjN6IiBmaWxsPSIjRkJCQzA1IiBmaWxsLXJ1bGU9Im5vbnplcm8iLz48cGF0aCBkPSJNOSAzLjZjMS4zIDAgMi41LjQgMy40IDEuM0wxNSAyLjNBOSA5IDAgMCAwIDEgNWwzIDIuNGE1LjQgNS40IDAgMCAxIDUtMy43eiIgZmlsbD0iI0VBNDMzNSIgZmlsbC1ydWxlPSJub256ZXJvIi8+PHBhdGggZD0iTTAgMGgxOHYxOEgweiIvPjwvZz48L3N2Zz4=);
                background-color: white;
                background-repeat: no-repeat;
                background-position: 12px 11px;
                }
                .element-container:has(#button-after) + div button:hover { 
                       box-shadow: 0 -1px 0 rgba(0, 0, 0, .04), 0 2px 4px rgba(0, 0, 0, .25);
                }
            </style>""", unsafe_allow_html=True)
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
            redirect_uri=st.session_state["redirect_uri"] if "redirect_page" not in st.session_state else st.session_state.redirect_page,
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
            st.markdown('<span id="button-after"></span>', unsafe_allow_html=True)
            if st.button("Sign in with Google"):
                authorization_url, state = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                )
                webbrowser.open_new_tab(authorization_url)

    def sign_up(self,):

        print("inside signing up")
        authenticator = st.session_state.authenticator
        username= authenticator.register_user("Create an account", "main", preauthorization=False)
        if username:
            name = authenticator.credentials["usernames"][username]["name"]
            password = authenticator.credentials["usernames"][username]["password"]
            email = authenticator.credentials["usernames"][username]["email"]
            if self.save_password( username, name, password, email):
                if STORAGE=="LOCAL":
                    user_path = os.path.join(os.environ["USER_PATH"], email)
                elif STORAGE=="CLOUD":
                    user_path = os.path.join(os.environ["USER_PATH"], email)
                mk_dirs([user_path], storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
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
        st.button(label="submit", on_click=self.form_callback, args=("resume", ), disabled=st.session_state.resume_disabled)
        st.button(label='skip', type="primary", on_click=self.display_profile)

    def about_future(self):

        st.text_area("Where do you see yourself in 5 years?")

    def about_skills(self):

        st.text_area("What are your skills and talent?")


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



    # def form_callback1(self):

    #     st.session_state["init_user1"]=True

                
    # def form_callback2(self):

    #     summary = create_profile_summary(self.userId)
    #     print("profile summary",  summary)
    #     st.session_state["users"][self.userId]["summary"] = summary
    #      # Save the updated user profiles back to the JSON file
    #     with open(user_profile_file, 'w') as file:
    #         json.dump(st.session_state["users"], file, indent=2)
    #     data = [{"text": summary,"id":self.userId, "job_title":st.session_state.job, "job_url":"", "type":"user"}]
    #     print(data)
    #     add_to_lancedb_table(self.userId, data)
    #     st.session_state["init_user2"]=True

    def form_callback(self, type):
        """"""
        if type=="resume":
            resume_dict = create_resume_info(st.session_state.user_resume_path,)
            user_dict = {}
            user_dict.update(resume_dict["sections"])
            user_dict.update(resume_dict["contact"])
            user_dict.update(resume_dict["education"])
            user_dict.update({"resume_content":resume_dict["resume_content"]})
            user_dict.update({"resume_path": st.session_state.user_resume_path})
            user_dict.update({"user_id": self.userId})
            # table = create_lancedb_table(lance_users_table, ResumeUsers)
            #NOTE: the data added has to be a LIST!
            add_to_lancedb_table(lance_users_table, [user_dict], ResumeUsers)
            print("Successfully aded user to lancedb table")



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
        if input_type=="birthday":
            st.session_state.birthday = input_value.strftime('%Y-%m-%d')
            #TODO: get age instead
        if input_type=="certification":
            st.session_state.certification = input_value.split(",")
        if input_type=="study":
            st.session_state.study = input_value.split(",")
        if input_type=="job":
            st.session_state.job=str(input_value.split(","))
        if input_type=="location_input":
            st.session_state.location_input=input_value.split(",")
        elif input_type=="transferable_skills":
            st.session_state.transferable_skills=input_value.split(",")





    def display_profile(self,):

        """Loads from user file and displays profile"""
        profile=st.session_state["user_profile_dict"]
        updated_dict = {}
        with st.expander(label="Bio"):
            try:
                value = profile["name"][0]
            except Exception as e:
                print(e)
                value = ""
            if st.text_input("name", value=value, key="profile_name",  args=(profile, )):
                updated_dict.update({"name":st.session_state.profile_name})
            try:
                value = profile["email"][0]
            except Exception as e:
                print(e)
                value = ""
            if st.text_input("email", value=value, key="profile_email",  args=(profile, )):
                updated_dict.update({"email":st.session_state.profile_email})
        save_changes = st.button("Save", key="profile_save_buttonn",)
        if save_changes:
            print("saving changes")
            self.update_personal_info(updated_dict)
 
            
  
    def update_personal_info(self, updated_dict):

        """ updates user profile"""

        try:
            users_table = retrieve_lancedb_table(lance_users_table)
            user_id = self.userId
            users_table.update(where=f"user_id = '{self.userId}'", values=updated_dict)
            print("Successfully updated user profile")
        except Exception as e:
            raise e

        # update user information to vectorstore
        # vectorstore=create_vectorstore("elasticsearch", index_name=self.userId)
        # record_manager=create_record_manager(self.userId)
        # update_index(docs, record_manager, vectorstore)
    




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
        





if __name__ == '__main__':
    if "force_user_mode" in st.session_state:
        if st.session_state.force_user_mode == "signout":
            user = User("signout")
        elif st.session_state.force_user_mode == "display_profile":
            user=User("display_profile")
    else:
        user=User()
    

