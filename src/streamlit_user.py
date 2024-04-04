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
from cookie_manager import get_cookie, set_cookie, delete_cookie, get_all_cookies, decode_jwt, encode_jwt
import time
from datetime import datetime, timedelta, date
from streamlit_modal import Modal
from utils.dynamodb_utils import save_user_info
from aws_manager import get_aws_session
from utils.dynamodb_utils import init_table, check_attribute_exists
from streamlit_plannerbot import Planner
import streamlit.components.v1 as components
from utils.lancedb_utils import create_table, add_to_table
from utils.langchain_utils import create_record_manager, create_vectorstore, update_index, split_doc_file_size, clear_index, retrieve_vectorstore
from utils.common_utils import get_generated_responses, check_content
from utils.basic_utils import read_txt, delete_file, convert_to_txt
from typing import Any, List
from langchain.docstore.document import Document
from pathlib import Path
from feast import FeatureStore
import faiss
import re
import uuid
from hash_password import save_password
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# st.set_page_config(layout="wide")
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

login_file = os.environ["LOGIN_FILE"]
STORAGE = os.environ['STORAGE']
bucket_name = os.environ["BUCKET_NAME"]
# store = FeatureStore("./my_feature_repo/")



class User():
    
    cookie = get_cookie("userInfo")
    aws_session = get_aws_session()
    # st.write(get_all_cookies())

    def __init__(self):
        # NOTE: userId is retrieved from browser cookie
        time.sleep(2)
        if self.cookie:
            username = decode_jwt(self.cookie, "test").get('username')
            print("cookie exists", username)
            self.userId = username
        else:
            self.userId = None 
        if "sessionId" not in st.session_state:
            st.session_state["sessionId"] = str(uuid.uuid4())
            print(f"Session: {st.session_state.sessionId}")
        self._init_session_states(self.userId, st.session_state.sessionId)
        self._init_user()

    @st.cache_data()
    def _init_session_states(_self, userId, sessionId):

        if _self.cookie is None:
            st.session_state["mode"]="signedin"
        else:
            st.session_state["mode"]="signedin"

        st.session_state["welcome_modal"]=Modal("Welcome", key="register", max_width=500)
        st.session_state["sagemaker_client"]=_self.aws_session.client('sagemaker-featurestore-runtime')

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
                # st.session_state["directory_made"] = True
            except Exception as e:
                pass
        st.session_state["value0"]=""
        st.session_state["value1"]=""
        st.session_state["value2"]=""





    def _init_user(self):

        """ Initalizes user page according to user's sign in status"""
        with open(login_file) as file:
            config = yaml.load(file, Loader=SafeLoader)
        authenticator = stauth.Authenticate( config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'], config['preauthorized'] )
        if st.session_state.mode=="signup":
            print("signing up")
            self.sign_up(authenticator)
        elif st.session_state.mode=="signedout":
            print("signing in")
            self.sign_in(authenticator)
        elif st.session_state.mode=="signedin":
            print("signed in")
            # if "vectorstore" not in st.session_state:
            #     st.session_state["vectorstore"] = retrieve_vectorstore("elasticsearch", self.userId)
            # if st.session_state.vectorstore is not None:
            if "init_user1" not in st.session_state:
                self.about_user1()
            if "init_user1" in st.session_state and st.session_state["init_user1"]==True and "init_user2" not in st.session_state:
                self.about_user2()
            self.sign_out(authenticator)
            with st.sidebar:
                update = st.button(label="update profile", key="update_profile", on_click=self.update_personal_info)
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
            delete_cookie(get_cookie("userInfo"), key="deleteCookie")
            st.session_state["mode"]="signedout"



    def sign_in(self, authenticator):

        # modal = Modal("   ", key="sign_in_popup", max_width=500, close_button=False)
        # with modal.container():
            # st.button("X", on_click=self.close_modal, args=["signin_modal"])
        st.header("Welcome")
        name, authentication_status, username = authenticator.login('', 'main')
        print(name, authentication_status, username)
        # print(name, authentication_status, username)
        if authentication_status:
            print("user signed in through system")
            # set_cookie("userInfo", user_info, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
            # time.sleep(3)
        elif authentication_status == False:
            st.error('Username/password is incorrect')
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
            forgot_password = st.button(label="forgot my password", key="forgot", type="primary") 
        st.markdown("or")
        user_info = my_component(name="signin", key="signin")
        if user_info!=-1:
            user_info=user_info.split(",")
            name = user_info[0]
            email = user_info[1]
            token = user_info[2]
            cookie = encode_jwt(name, email, "test")
            print(f"user signed in through google: {user_info}")
            # NOTE: Google's token expires after 1 hour
            # set_cookie("userInfo", cookie, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
            set_cookie("userInfo", cookie, key="setCookie", path="/", expire_at=datetime.now()+timedelta(days=1))
            time.sleep(3)


    def sign_up(self, authenticator:stauth.Authenticate):

        # modal = Modal("Welcome", key="register", max_width=500)
        # with modal.container():
        print("inside signing up")
        username= authenticator.register_user("Create an account", "main", preauthorization=False)
        if username:
            name = authenticator.credentials["usernames"][username]["name"]
            password = authenticator.credentials["usernames"][username]["password"]
            email = authenticator.credentials["usernames"][username]["email"]
            if save_password( username, name, password, email):
                st.session_state["mode"]="signedin"
                st.success("User registered successfully")
                cookie = encode_jwt(name, username, "test")
                set_cookie("userInfo", cookie, key="setCookie", path="/", expire_at=datetime.now()+timedelta(days=1))
                st.rerun()
            else:
                st.info("Failed to register user, please try again")
                st.rerun()





    # def close_modal(self, name):
    #     st.session_state[name]=False


    # def about_me_popup(_self) -> None:
    
    #     """ Processes user's about me input. """

    #     modal = Modal(title="", key="about_popup", max_width=800, close_button=False)
    #     if st.session_state.get("past", False) and st.session_state.get("present", False) and st.session_state.get("future", False) :
    #         st.session_state.disabled=False
    #     else:
    #         st.session_state.disabled=True
    #     with modal.container():
    #         st.button("X", on_click=_self.close_modal, args=["about_me_modal"])
    #         selected = stx.stepper_bar(steps=["Self Description", "Current Situation", "Career Goals"])
    #         if selected==0:
    #             st.text_input(
    #             label="What can I know about you?", 
    #             placeholder="Tell me about yourself", 
    #             key = "about_past", 
    #             on_change=_self.field_check
    #             )
    #         elif selected==1:
    #             st.text_input(
    #             label="What takes you here?",
    #             placeholder = "Tell me about your present situation",
    #             key="about_present",
    #             on_change = _self.field_check
    #             )
    #         elif selected==2:
    #             st.text_input(
    #             label="What can I do for you?",
    #             placeholder = "Tell me about your career goals",
    #             key="about_future",
    #             on_change=_self.field_check,
    #             )
    #         submitted = st.button("Submit", on_click=_self.form_callback2, disabled=st.session_state.disabled)
    #         if submitted:
    #             st.session_state["init_user"]=True
    #             modal.close()

    def about_user1(self):


        if (st.session_state.get("first_name", False) and st.session_state.get("last_name", False) and st.session_state.get("birthday", False) and st.session_state.get("grad_year", False) and st.session_state.get("degree", False) and st.session_state.get("job", False) and st.session_state.get("job_level", False)) or (st.session_state.get("resume", False)):
            st.session_state.disabled1=False
        else:
            st.session_state.disabled1=True
        st.markdown("**Basic Information**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("First Name", key="first_namex", on_change=self.field_check)
        with c2:
            st.text_input("Last Name", key="last_namex", on_change=self.field_check)
        with c3:
            st.date_input("Date of Birth", date(2019, 7, 6), min_value=date(1950, 1, 1), key="birthdayx", on_change=self.field_check)
        # c1, c2, c3, c4=st.columns(4)
        # with c1:
        #     st.text("Date of Birth")
        # with c2:
        #     st.selectbox("day", key="day", options=(1, 2, 3))
        # with c3:
        #     st.selectbox("month", key="month", options=(1, 2, 3))
        # with c4: 
        #     st.selectbox("year", key="year", options=(1, 2, 3))
        c1, c2, c3, c4 = st.columns([0.5, 1, 1, 1])
        with c1:
            st.text("Highest Level of \n Education")
            # st.text_input("School", key="schoolx")
        with c2:
            st.text_input("Year of Graduation", key="grad_yearx", on_change=self.field_check)
        with c3:
            st.selectbox("Degree", options=(1, 2, 3), key="degreex", on_change=self.field_check)
        with c4:
            st.text_input("Area of study", key="studyx", placeholder="please separate each with a comma", on_change=self.field_check)
        c1, c2, c3 = st.columns([0.5, 1, 1])
        with c1:
            st.text("""Work Experience of \n Your Career of Choice""")
            # components.html( """<div style="text-align: bottom"> Work Experience</div>""")
        with c2:
            st.text_input("Job Title", key="jobx", on_change=self.field_check)
        with c3:
            st.select_slider("Level",  options=["no experience", "entry level", "junior level", "mid level", "senior level"], key='job_levelx', on_change=self.field_check)   
        st.markdown("*OR*")
        st.file_uploader(label="Default Resume", key="resumex", on_change=self.field_check,)
        if st.checkbox("Share my location"):
            loc = get_geolocation()
            if loc:
                address = self.get_address(loc["coords"]["latitude"], loc["coords"]["longitude"])
                st.session_state["address"] = address
        st.button(label="Next", on_click=self.form_callback1, disabled=st.session_state.disabled1)



    def about_user2(self):

        # with st.form(key="about_me2", clear_on_submit=False):
        if st.session_state.get("self_description", False):
        # and st.session_state.get("current_situation", False) and st.session_state.get("career_goals", False) :
            st.session_state.disabled=False
        else:
            st.session_state.disabled=True
        selected = stx.stepper_bar(steps=["Self Description", "Current Situation", "Career Goals"])
        if selected==0 and st.session_state.value0=="":
            value0 = st.text_area(
            label="What can I know about you?", 
            placeholder="Tell me about yourself", 
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
            label="What takes you here?",
            placeholder = "Tell me about your present situation",
            key="current_situationx",
            on_change =self.field_check
            )
            st.session_state["value1"]=value1
        elif selected==1 and st.session_state.value1!="":
            value1=st.text_area(
            label="What takes you here?",
            value=st.session_state["value1"],
            key = "current_situationx",
            on_change=self.field_check
            )
            st.session_state["value1"]=value1
        elif selected==2 and st.session_state.value2=="":
            value2=st.text_area(
            label="What can I do for you?",
            placeholder = "Tell me about your career goals",
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
        # if submitted:
        #     st.session_state["init_user2"]=True



    def form_callback1(self):

        # try:
        #     first_name=st.session_state.first_name
        # except AttributeError:
        #     st.write("first name is required")
        st.session_state["init_user1"]=True

                
    def form_callback2(self):

        #TODO: if user did not fill out info, grab info from resume
        # docs: List[Document] = []
        # if "resume_path" in st.session_state:
        #     resume_docs = split_doc_file_size(path=st.session_state.resume_path, file_type="file", storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
        #     docs.extend(resume_docs)
        #     print("added resume to docs")
        #     if st.session_state.first_name is None and st.session_state.last_name is None:
        #         info_dict=get_generated_responses(resume_content=st.session_state.resume_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
        # basic_info_text = f""" User's name is {st.session_state.first_name} {st.session_state.last_name}. User is born in {st.session_state.birthday}. 
        # User graduated in {st.session_state.grad_year}, with a degree in {st.session_state.degree}, and area of study in {st.session_state.study}.
        # User's career of choice is {st.session_state.job}. The work experience level for this job is {st.session_state.job_level}
        # """
        # description_text = f""" user's name is {st.session_state.first_name} {st.session_state.last_name}. The following are user's self-description, current situation, and future career goals.
        # self-description: {st.session_state.self_description} \
        # """   
        # # current situation: {st.session_state.current_situation} \
        # # career goals: {st.session_state.career_goals} \
        # text = basic_info_text + description_text
        # print(text)
        # save_path =  os.path.join(st.session_state.user_path, self.userId, "basic_info", "user_description.txt")
        # if st.session_state.storage=="LOCAL":
        #     with open(save_path, "wb") as f:
        #         f.write(text)
        # elif st.session_state.storage=="CLOUD":
        #     st.session_state.s3_client.put_object(Body=text, Bucket=bucket_name, Key=save_path)
        #     print("Successful written file to S3")
        # docs = split_doc_file_size(save_path, "file", storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
        # # update user information to vectorstore
        # vectorstore=create_vectorstore("elasticsearch", index_name=self.userId)
        # # res = vectorstore.similarity_search(query="what is the name of the user?", k=2)
        # # print(f"res is {res}")
        # record_manager=create_record_manager(self.userId)
        # update_index(docs, record_manager, vectorstore, cleanup_mode=None)
        # print(f"record manager keys: {record_manager.list_keys()}")
        st.session_state["init_user2"]=True
        # table.add([{"text":text}])
        # field_names = ["first_name", "last_name", "birthday", "grad_year", "degree", "study", "job", "job_level", "past", "present", "future"]
        # field_values=[st.session_state.first_name, st.session_state.last_name, st.session_state.birthday, st.session_state.grad_year, 
        #               st.session_state.degree, st.session_state.study, st.session_state.job, st.session_state.job_level, 
        #               st.session_state.past, st.session_state.present, st.session_state.future]
        # for field_name, field_value in zip(field_names, field_values):
        #     add_to_table(field_name, field_value, table=table)
    def test_clear(self):
        
        vectorstore = retrieve_vectorstore("elasticsearch", index_name=self.userId)
        record_manager=create_record_manager(self.userId)
        print(f"record manager keys: {record_manager.list_keys()}")
        clear_index(record_manager, vectorstore)
        print(f"record manager keys: {record_manager.list_keys()}")

    def get_address(self, latitude, longitude):
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
        except AttributeError:
            pass
        try:
            st.session_state["current_situation"] = st.session_state.current_situationx
        except AttributeError:
            pass
        try:
            st.session_state["career_goals"] = st.session_state.career_goalsx
        except AttributeError:
            pass
        try:
            st.session_state["first_name"] = st.session_state.first_namex
        except AttributeError:
            pass
        try:
            st.session_state["last_name"] = st.session_state.last_namex
        except AttributeError:
            pass
        try:
            st.session_state["birthday"] = st.session_state.birthdayx
        except AttributeError:
            pass
        # try:
        #     st.session_state["school"] = st.session_state.schoolx
        # except AttributeError:
        #     pass
        try:
            st.session_state["grad_year"] = st.session_state.grad_yearx
        except AttributeError:
            pass
        try:
            st.session_state["degree"] = st.session_state.degreex
        except AttributeError:
            pass
        try:
            st.session_state["study"] = st.session_state.studyx
        except AttributeError:
            pass
        try:
            st.session_state["job"] = st.session_state.jobx
        except AttributeError:
            pass
        try:
            st.session_state["job_level"] = st.session_state.job_levelx
        except AttributeError:
            pass
        try:
            st.session_state["resume"] = st.session_state.resumex
            if st.session_state.resume:
                self.process_file(st.session_state.resume)
        except AttributeError:
            pass

    def process_file(self, uploaded_file: Any) -> None:

        """ Processes user uploaded files including converting all format to txt, checking content safety, and categorizing content type  """
        # with st.session_state.file_loading, st.spinner("Processing..."):
        # with st.session_state.spinner_placeholder, st.spinner("Processing..."):
        # for uploaded_file in uploaded_files:
        file_ext = Path(uploaded_file.name).suffix
        filename = str(uuid.uuid4())+file_ext
        save_path = os.path.join(st.session_state.user_path, self.userId, "basic_info", filename)
        end_path =  os.path.join(st.session_state.user_path, self.userId, "basic_info", Path(filename).stem+'.txt')
        st.session_state["resume_path"] = end_path
        if st.session_state.storage=="LOCAL":
            with open(save_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
        elif st.session_state.storage=="CLOUD":
            st.session_state.s3_client.put_object(Body=uploaded_file.getvalue(), Bucket=bucket_name, Key=save_path)
            print("Successful written file to S3")
        # Convert file to txt and save it 
        if convert_to_txt(save_path, end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client): 
            content_safe, content_type, content_topics = check_content(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
            print(content_type, content_safe, content_topics) 
            if content_safe and content_type=="resume":
                st.toast(f"your {content_type} is successfully submitted")
            else:
                delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                # delete_file(save_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                st.toast(f"Failed processing your resume. Please try again!")
           

  
    def update_personal_info(self):

        # update user information to vectorstore
        vectorstore=create_vectorstore("elasticsearch", index_name=self.userId)
        record_manager=create_record_manager(self.userId)
        update_index(docs, record_manager, vectorstore)





# class to filter data and pass the information into
# the prompt template we have above.
# class FeastPromptTemplate(StringPromptTemplate):
#     def format(self, **kwargs) -> str:
#         user_id = kwargs.pop("user_id")
#         feature_vector = feature_service.get_online_features(join_keys={"user_id":user_id}).to_dict()
#         # df = pd.read_csv("./data.csv")
#         # row = df[df["EmpID"] == int(employee_id)]
#         kwargs["full_name"] = row["RecruitmentSource"].values[0]
#         kwargs["date_of_birth"] = row["Salary"].values[0]
#         kwargs["highest_education"] = row["RaceDesc"].values[0]
#         kwargs["year_of_graduation"] = row["Department"].values[0]
#         kwargs["degree"] = row["SpecialProjectsCount"].values[0]
#         kwargs["area_of_study"] = row["Employee_Name"].values[0]
#         kwargs["desired_job"] = row["Department"].values[0]
#         kwargs["experience_level"] = row["SpecialProjectsCount"].values[0]
#         kwargs["self_description"] = row["Employee_Name"].values[0]
#         kwargs["current_situation"] = row["Employee_Name"].values[0]
#         kwargs["career_goals"] = row["Employee_Name"].values[0]
#         return prompt.format(**kwargs)





if __name__ == '__main__':
    user = User()

