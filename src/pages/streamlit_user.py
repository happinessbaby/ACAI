import streamlit as st
import extra_streamlit_components as stx
from my_component import my_component
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from langchain.prompts import PromptTemplate, StringPromptTemplate
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from cookie_manager import get_cookie, set_cookie, delete_cookie, get_all_cookies, decode_jwt, encode_jwt, get_cookie_manager
import time
from datetime import datetime, timedelta, date
from streamlit_modal import Modal
from utils.dynamodb_utils import save_user_info
from aws_manager import get_aws_session
from utils.dynamodb_utils import init_table, check_attribute_exists
from streamlit_plannerbot import Planner
import streamlit.components.v1 as components
from utils.lancedb_utils import create_lancedb_table, lancedb_table_exists, add_to_lancedb_table, query_lancedb_table
from utils.langchain_utils import create_record_manager, create_vectorstore, update_index, split_doc_file_size, clear_index, retrieve_vectorstore
from utils.common_utils import get_generated_responses, check_content, process_linkedin, process_resume, create_profile_summary
from utils.basic_utils import read_txt, delete_file, convert_to_txt
from typing import Any, List
from langchain.docstore.document import Document
from pathlib import Path
from feast import FeatureStore
import faiss
import re
import uuid
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import lancedb
import json
from json.decoder import JSONDecodeError

# st.set_page_config(layout="wide")
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

STORAGE = os.environ['STORAGE']
bucket_name = os.environ["BUCKET_NAME"]
login_file = os.environ["LOGIN_FILE_PATH"]
db_path=os.environ["LANCEDB_PATH"]
user_file=os.environ["USER_FILE"]
# store = FeatureStore("./my_feature_repo/")



class User():
    
    # cookie = get_cookie("userInfo")
    aws_session = get_aws_session()
    cookie_manager = get_cookie_manager()
    # st.write(get_all_cookies())

    def __init__(self):
        # NOTE: userId is retrieved from browser cookie
        self.cookie = get_cookie("userInfo", self.cookie_manager)
        time.sleep(2)
        if self.cookie:
            username = decode_jwt(self.cookie, "test").get('username')
            print("Cookie:", username)
            self.userId = username
            st.session_state["mode"]="signedin"
        else:
            if "mode" not in st.session_state or st.session_state["mode"]!="signup":  
                # self.userId = "tebs"
                st.session_state["mode"]="signedout"
            self.userId = None
        if "sessionId" not in st.session_state:
            st.session_state["sessionId"] = str(uuid.uuid4())
            print(f"Session: {st.session_state.sessionId}")
        self._init_session_states(self.userId, st.session_state.sessionId)
        self._init_user()

    @st.cache_data()
    def _init_session_states(_self, userId, sessionId):

        # if _self.cookie is None:
        #     st.session_state["mode"]="signedout"
        # else:
        #     st.session_state["mode"]="signedin"

        # st.session_state["welcome_modal"]=Modal("Welcome", key="register", max_width=500)
        with open(login_file) as file:
            config = yaml.load(file, Loader=SafeLoader)
        with open(user_file, 'r') as file:
            try:
                users = json.load(file)
            except JSONDecodeError:
                users = {}  # Icate( config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'], config['preauthorized'] )
        users[_self.userId]={}
        st.session_state["config"] = config
        st.session_state["users"] = users
        # st.session_state["sagemaker_client"]=_self.aws_session.client('sagemaker-featurestore-runtime')
        st.session_state["location_input"] = ""
        st.session_state["study"] = ""
        st.session_state["grad_year"] = ""
        st.session_state["certification"] = ""
        st.session_state["career_switch"] = False
        st.session_state["industry"] = ""
        st.session_state["self_description"]= ""
        st.session_state["skill_set"]=""
        st.session_state["career_goals"]=""
        st.session_state["lancedb_conn"]= lancedb.connect(db_path)
        if STORAGE=="CLOUD":
            st.session_state["s3_client"] = _self.aws_session.client('s3') 
            st.session_state["bucket_name"] = bucket_name
            st.session_state["storage"] = "CLOUD"
            st.session_state["user_path"] = os.environ["S3_USER_PATH"]
            try:
                # create "directories" in S3 bucket
                st.session_state.s3_client.put_object(Bucket=bucket_name,Body='', Key=os.path.join(st.session_state.user_path, _self.userId, "basic_info"))
                print("Successfully created directories in S3")
            except Exception as e:
                pass
        elif STORAGE=="LOCAL":
            st.session_state["s3_client"] = None
            st.session_state["bucket_name"] = None
            st.session_state["storage"] = "LOCAL"
            st.session_state["user_path"] = os.environ["USER_PATH"]
            try: 
                user_dir = os.path.join(st.session_state.user_path,  _self.userId, "basic_info")
                os.mkdir(user_dir)
            except Exception as e:
                pass
        st.session_state["value0"]=""
        st.session_state["value1"]=""
        st.session_state["value2"]=""





    def _init_user(self):

        """ Initalizes user page according to user's sign in status"""

        config = st.session_state["config"]
        authenticator = stauth.Authenticate( config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'], config['preauthorized'] )
        if st.session_state.mode=="signup":
            print("signing up")
            self.sign_up(authenticator)
        elif st.session_state.mode=="signedout":
            print("signed out")
            self.sign_in(authenticator)
        elif st.session_state.mode=="signedin":
            print("signed in")
            self.sign_out(authenticator)
            if lancedb_table_exists(st.session_state["lancedb_conn"], self.userId):
                print("user profile already exists")
            else:
                if "init_user1" not in st.session_state:
                    self.about_user1()
                if "init_user1" in st.session_state and st.session_state["init_user1"]==True and "init_user2" not in st.session_state:
                    self.about_user2()
            # with st.sidebar:
            #     update = st.button(label="update profile", key="update_profile", on_click=self.update_personal_info)
            # if "plannerbot" not in st.session_state:
            #     st.session_state["plannerbot"]=Planner(self.userId)
            # try:
            #     st.session_state.plannerbot._create_user_page()
            # except Exception as e:
            #     raise e
    

    def sign_out(self, authenticator):

        logout = authenticator.logout('Logout', 'sidebar')
        if logout:
            # Hacky way to log out of Google
                # print(get_all_cookies())
            print('signing out')
            _ = my_component("signout", key="signout")
            delete_cookie(get_cookie("userInfo"), key="deleteCookie", cookie_manager=self.cookie_manager)
            st.session_state["mode"]="signedout"
            st.rerun()



    def sign_in(self, authenticator):

        # modal = Modal("   ", key="sign_in_popup", max_width=500, close_button=False)
        # with modal.container():
            # st.button("X", on_click=self.close_modal, args=["signin_modal"])
        st.header("Welcome back")
        name, authentication_status, username = authenticator.login('', 'main')
        # print(name, authentication_status, username)
        if authentication_status:
            cookie = encode_jwt(name, username, "test")
            set_cookie("userInfo", cookie, key="setCookie", path="/", expire_at=datetime.now()+timedelta(days=1), cookie_manager=self.cookie_manager)
            st.session_state["mode"]="signedin"
            st.rerun()
            # time.sleep(3)
        # elif authentication_status == False:
        #     st.error('Username/password is incorrect')
        # elif authentication_status == None:
        #     st.warning('Please enter your username and password')
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
                st.session_state["mode"]="signup"
                st.rerun()
        with col3:
            forgot_password = st.button(label="forgot my username/password", key="forgot", type="primary") 
        # st.markdown("or")
        # user_info = my_component(name="signin", key="signin")
        # if user_info!=-1:
        #     user_info=user_info.split(",")
        #     name = user_info[0]
        #     email = user_info[1]
        #     token = user_info[2]
        #     cookie = encode_jwt(name, email, "test")
        #     print(f"user signed in through google: {user_info}")
        #     # NOTE: Google's token expires after 1 hour
        #     # set_cookie("userInfo", cookie, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
        #     set_cookie("userInfo", cookie, key="setCookie", path="/", expire_at=datetime.now()+timedelta(days=1))
        #     time.sleep(3)


    def sign_up(self, authenticator:stauth.Authenticate):

        print("inside signing up")
        username= authenticator.register_user("Create an account", "main", preauthorization=False)
        if username:
            name = authenticator.credentials["usernames"][username]["name"]
            password = authenticator.credentials["usernames"][username]["password"]
            email = authenticator.credentials["usernames"][username]["email"]
            if self.save_password( username, name, password, email):
                st.session_state["mode"]="signedin"
                st.success("User registered successfully")
                cookie = encode_jwt(name, username, "test")
                set_cookie("userInfo", cookie, key="setCookie", path="/", expire_at=datetime.now()+timedelta(days=1), cookie_manager=self.cookie_manager)
                st.rerun()
            else:
                st.info("Failed to register user, please try again")
                st.rerun()


    def about_user1(self):

        st.markdown("**To get started, please fill out the fields below**")
        if st.session_state.get("name", False) and st.session_state.get("birthday", False)  and st.session_state.get("degree", False) and ((st.session_state.get("job", False) and st.session_state.get("job_level", False)) or st.session_state.get("industry", False)):
            st.session_state.disabled1=False
        else:
            st.session_state.disabled1=True
        # st.markdown("**Basic Information**")
        with st.expander("**Basic information**", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                #TODO: check default value for user who wants to change their profile info
                st.text_input("Full name *", key="namex", 
                              value= st.session_state["users"][self.userId]["name"] if self.userId in st.session_state["users"] and "name" in st.session_state["users"][self.userId] else "", 
                              on_change=self.field_check)
            with c2:
                st.date_input("Date of Birth *", date.today(), min_value=date(1950, 1, 1), key="birthdayx", on_change=self.field_check)
            st.text_input("LinkedIn", key="linkedinx", on_change=self.field_check)
        with st.expander("**Education**"):
            c1, c2 = st.columns([1, 1])
                # st.text_input("School", key="schoolx")
            with c2:
                st.text_input("Year of Graduation (if applicable)", key="grad_yearx", on_change=self.field_check)
            with c1:
                degree = st.selectbox("Highest level of education *", options=("Did not graduate high school", "High school diploma", "Associate's degree", "Bachelor's degree", "Master's degree", "Professional degree"), key="degreex", placeholder = "Select your highest level of education", on_change=self.field_check)
            if degree=="Associate's degree" or degree=="Bachelor's degree" or degree=="Master's degree" or degree=="Professional degree":
                st.text_input("Area(s) of study", key="studyx", placeholder="please separate each with a comma", on_change=self.field_check)
            certification = st.checkbox("Other certifications")
            if certification:
                st.text_area("", key="certificationx", placeholder="Please write out the full name of each certification chronologically and separate them with a comma", on_change=self.field_check)
        # st.markdown("**Career**")
        with st.expander("**Career**"):
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
                pay_type = st.selectbox("", ("hourly", "annually"), placeholder="Select pay type...", key="pay_typex", on_change=self.field_check)
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
        st.file_uploader(label="**Resume**", key="resumex", on_change=self.field_check,)
        st.button(label="Next", on_click=self.form_callback1, disabled=st.session_state.disabled1)



    def about_user2(self):

        # with st.form(key="about_me2", clear_on_submit=False):
        if st.session_state.get("self_description", False):
        # and st.session_state.get("current_situation", False) and st.session_state.get("career_goals", False) :
            st.session_state.disabled=False
        else:
            st.session_state.disabled=True
        selected = stx.stepper_bar(steps=["Self Description", "Job Search", "Career Goals"])
        if selected==0 and st.session_state.value0=="":
            value0 = st.text_area(
            label="What can I know about you?", 
            placeholder="Tell me about yourself, for example, what are your best motivations and values? What's important to you in a job?", 
            key = "self_descriptionx", 
            on_change=self.field_check
            )
            st.session_state["value0"]=value0
        elif selected==0 and st.session_state.value0!="":
            value0=st.text_area(
            label="What can I know about you?", 
            value=st.session_state["value0"],
            key = "self_descriptionx", 
            on_change=self.field_check
            )
            st.session_state["value0"]=value0
        elif selected==1 and st.session_state.value1=="":
            value1=st.text_area(
            label="What are your skills?",
            placeholder = "Tell me about your skills and talent? What are you especially good at that you want to bring to a workplace?",
            key="skill_setx",
            on_change =self.field_check
            )
            st.session_state["value1"]=value1
        elif selected==1 and st.session_state.value1!="":
            value1=st.text_area(
            label="What are your skills?",
            value=st.session_state["value1"],
            key = "skill_setx",
            on_change=self.field_check
            )
            st.session_state["value1"]=value1
        elif selected==2 and st.session_state.value2=="":
            value2=st.text_area(
            label="What can I do for you?",
            placeholder = "Tell me about your career goals. Where do you see yourself in 1 year? What about 10 years? What do you want to achieve in life?",
            key="career_goalsx",
            on_change=self.field_check,
            )
            st.session_state["value2"]=value2
        elif selected==2 and st.session_state.value2!="":
            value2=st.text_area(
            label="What can I do for you?",
            value=st.session_state["value2"],
            key = "career_goalsx",
            on_change=self.field_check
            )
            st.session_state["value2"]=value2
        
        submitted = st.button("Submit", on_click=self.form_callback2, disabled=st.session_state.disabled)
        skip = st.button(label="skip", help="You can come back to this later, but remember, the more information you provide, the better your job search results", type="primary", on_click=self.form_callback2)
        # if submitted:
        #     st.session_state["init_user2"]=True



    def form_callback1(self):

        st.session_state["init_user1"]=True

                
    def form_callback2(self):

         # Save the updated user profiles back to the JSON file
        with open(user_file, 'w') as file:
            json.dump(st.session_state["users"], file, indent=2)
        summary = create_profile_summary(self.userId)
        data = [{"text": summary,"id":self.userId, "job_title":st.session_state.job,  "type":"user"}]
        add_to_lancedb_table(st.session_state["lancedb_conn"], self.userId, data)
        st.session_state["init_user2"]=True



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
            self.process_input("birthday", birthday)
            st.session_state["users"][self.userId]["birthday"] = st.session_state.birthday
        except AttributeError:
            pass
        try:
            st.session_state["linkedin"] = st.session_state.linkedinx
            process_linkedin(st.session_state.linkedin)
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
            self.process_input("study", study)
            st.session_state["users"][self.userId]["study"] = st.session_state.study
        except AttributeError:
            pass
        try:
            certification = st.session_state.certificationx 
            self.process_input("certification", certification)
            st.session_state["users"][self.userId]["certification"] = st.session_state.certification
        except AttributeError:
            pass
        try:
            job = st.session_state.jobx
            self.process_input("job", job)
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
            self.process_input("transferable_skills", transferable_skills)
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
            self.process_input("location_input", location_input)
            st.session_state["users"][self.userId]["location_input"] = st.session_state.location_input
        except AttributeError:
            pass
        try:
            st.session_state["resume"] = st.session_state.resumex
            if st.session_state.resume:
                process_resume(st.session_state.resume)
        except AttributeError:
            pass

    def process_input(self, input_type, input_value):

        if input_type=="birthday":
            st.session_state.birthday = input_value.strftime('%Y-%m-%d')
        if input_type=="certification":
            st.session_state.certification = input_value.split(",")
        if input_type=="study":
            st.session_state.study = input_value.split(",")
        if input_type=="job":
            st.session_state.job=input_value.split(",")
        if input_type=="location_input":
            st.session_state.location_input=input_value.split(",")
        elif input_type=="transferable_skills":
            st.session_state.transferable_skills=input_value.split(",")

    # def process_file(self, uploaded_file: Any) -> None:

    #     """ Processes user uploaded files including converting all format to txt, checking content safety, and categorizing content type  """
    #     # with st.session_state.file_loading, st.spinner("Processing..."):
    #     # with st.session_state.spinner_placeholder, st.spinner("Processing..."):
    #     # for uploaded_file in uploaded_files:
    #     file_ext = Path(uploaded_file.name).suffix
    #     filename = str(uuid.uuid4())+file_ext
    #     save_path = os.path.join(st.session_state.user_path, self.userId, "basic_info", filename)
    #     end_path =  os.path.join(st.session_state.user_path, self.userId, "basic_info", Path(filename).stem+'.txt')
    #     st.session_state["resume_path"] = end_path
    #     if st.session_state.storage=="LOCAL":
    #         with open(save_path, 'wb') as f:
    #             f.write(uploaded_file.getvalue())
    #     elif st.session_state.storage=="CLOUD":
    #         st.session_state.s3_client.put_object(Body=uploaded_file.getvalue(), Bucket=bucket_name, Key=save_path)
    #         print("Successful written file to S3")
    #     # Convert file to txt and save it 
    #     if convert_to_txt(save_path, end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client): 
    #         content_safe, content_type, content_topics = check_content(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #         print(content_type, content_safe, content_topics) 
    #         if content_safe and content_type=="resume":
    #             st.toast(f"your {content_type} is successfully submitted")
    #         else:
    #             delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #             # delete_file(save_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #             st.toast(f"Failed processing your resume. Please try again!")



    def display_profile(self):

        """Loads from user file and displays profile"""
  
    def update_personal_info(self):

        # update user information to vectorstore
        # vectorstore=create_vectorstore("elasticsearch", index_name=self.userId)
        # record_manager=create_record_manager(self.userId)
        # update_index(docs, record_manager, vectorstore)
        try:
            del st.session_state["init_user1"]
        except Exception:
            pass
        if "init_user1" not in st.session_state:
            self.about_user1()
        if "init_user1" in st.session_state and st.session_state["init_user1"]==True and "init_user2" not in st.session_state:
            self.about_user2()




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
    user = User()

