import extra_streamlit_components as stx
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
from utils.lancedb_utils import add_to_lancedb_table, retrieve_user_profile_dict, delete_user_from_table, save_user_changes, convert_pydantic_schema_to_arrow
from utils.common_utils import  process_linkedin, create_profile_summary, process_uploads, create_resume_info, process_links, process_inputs, retrieve_or_create_job_posting_info, readability_checker, grammar_checker
from utils.basic_utils import mk_dirs, send_recovery_email
from typing import Any, List
import uuid
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from utils.aws_manager import get_client
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import webbrowser
from utils.pydantic_schema import ResumeUsers
from streamlit_utils import nav_to, user_menu, progress_bar, set_streamlit_page_config_once
from css.streamlit_css import general_button, primary_button, google_button
from backend.upgrade_resume import tailor_resume, evaluate_resume
from streamlit_float import *
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import plotly.graph_objects as go
from st_pages import get_pages, get_script_run_ctx 
from streamlit_extras.stylable_container import stylable_container
import requests
from utils.async_utils import thread_with_trace
import streamlit_antd_components as sac
import streamlit as st


set_streamlit_page_config_once()

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

STORAGE = os.environ['STORAGE']
if STORAGE=="CLOUD":
    login_file = os.environ["S3_LOGIN_FILE_PATH"]
    db_path=os.environ["S3_LANCEDB_PATH"]
    client_secret_json = os.environ["CLIENT_SECRET_JSON"]
    base_uri = os.environ["PRODUCTION_BASE_URI"]
elif STORAGE=="LOCAL":
    login_file = os.environ["LOGIN_FILE_PATH"]
    db_path=os.environ["LANCEDB_PATH"]
    client_secret_json = os.environ["CLIENT_SECRET_JSON"]
    base_uri = os.environ["BASE_URI"]
user_profile_file=os.environ["USER_PROFILE_FILE"]
lance_users_table = os.environ["LANCE_USERS_TABLE"]
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
        self.userId = st.session_state.cm.retrieve_userId()
        if self.userId:
            if "user_mode" not in st.session_state:
                st.session_state["user_mode"]="signedin"
            st.session_state["user_profile_dict"]= retrieve_user_profile_dict(self.userId)
        else:
            if "user_mode" not in st.session_state:  
                st.session_state["user_mode"]="signedout"
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
        if st.session_state.user_mode=="signup":
            print("signing up")
            self.sign_up()
        elif st.session_state.user_mode=="signedout":
            print("signed out")
            self.sign_in()
        elif st.session_state.user_mode=="signedin":
            print("signed in")
            if "redirect_page" in st.session_state:
                st.switch_page(st.session_state.redirect_page)
            else:
                try:
                    if not st.session_state["user_profile_dict"]:
                        print("user profile does not exists yet")
                        # ask user for their resumes
                        self.initialize_resume()
                    else:
                        #display the progress bar
                        progress_bar(0)
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
        elif st.session_state.user_mode=="signout":
            self.sign_out()
        # elif st.session_state.user_mode=="reset_password":
        #     self.reset_password()

          
    


    

    def sign_out(self, ):

        print('signing out')
        #NOTE: can't get authenticator logout to delete cookies so manually doing it with the cookie manager wrapper class
        # still needs the logout code since the authenticator needs to be cleared
        st.session_state.authenticator.logout(location="unrendered")
        self.google_signout()
        st.session_state.cm.delete_cookie()
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
                # st.header("Welcome back")
                st.markdown("<h1 style='text-align: center; color: #2d2e29;'>Welcome back</h1>", unsafe_allow_html=True)
                self.google_signin()
                # add_vertical_space(1)
                # sac.divider(label='or',  align='center', color='gray')
                st.divider()
                name, authentication_status, username = st.session_state.authenticator.login()
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
                signup_col, forgot_password_col, forgot_username_col = st.columns([4, 1, 1])
                with signup_col:
                    add_vertical_space(2)
                    sign_up = st.button(label="**Sign up**", key="signup",  type="primary")
                    if sign_up:
                        st.session_state["user_mode"]="signup"
                        st.rerun()
                with forgot_password_col:
                    if st.button(label="forgot my password", key="forgot_password", type="primary"):
                        self.recover_password_username_popup(type="password")
                with forgot_username_col:
                    if st.button(label="forgot my username", key="forgot_username", type="primary"):
                        self.recover_password_username_popup(type="username")
                # print(name, authentication_status, username)
                if authentication_status:
                    # email = st.session_state.authenticator.credentials["usernames"][username]["email"]
                    st.session_state["user_mode"]="signedin"
                    time.sleep(5)
                    st.rerun()
                elif authentication_status==False:
                    placeholder_error.error('Username/password is incorrect')

    @st.experimental_dialog(title=" ")
    def recover_password_username_popup(self, type):
        add_vertical_space(1)
        # if type=="password":
        #     try:
        #         username, email, random_passowrd = st.session_state.authenticator.forgot_password(fields={"Form name": "", "Username":"Please provide the username associated with your account"})
        #         if username:
        #             st.write('Please check your email on steps to reset your password')
        #             if send_recovery_email(email, type, username=username, password=random_passowrd):
        #                 st.success('Please check your email to reset your password')
        #         elif username==False:
        #             st.error("Username not found")
        #     except Exception as e:
        #         st.error("something went wrong, please try again.")
        # elif type=="username":
        try:
            username, email = st.session_state.authenticator.forgot_username(fields={"Form name": "", "Email":"Please provide the email associated with your account"})
            if username:
                # if type=="password":
                    if send_recovery_email(email, type, username=username, ):
                        st.success('Please check your email')
                # elif type=="username":
                #     # The developer should securely transfer the username to the user.
                #     if send_recovery_email(email, type, username=username):
                #         st.success('Please check your email for your username')
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
            redirect_uri=st.session_state.redirect_page if "redirect_page" in st.session_state else base_uri+"/streamlit_user",
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
                    st.success("User registered successfully")
                    time.sleep(5)
                    st.rerun()
            except Exception as e:
                st.info(e)

    def reset_password(self, token, username):
    
        _, c, _ = st.columns([1, 1, 1])
        with c:
            if self.verify_token(token):
                with st.form(key="password_reset_form"):
                # Display the password reset form
                    new_password = st.text_input("New Password", type="password", )
                    confirm_password = st.text_input("Confirm Password", type="password")               
                    if st.form_submit_button("Reset Password"):
                        if new_password == confirm_password:
                            # Update the user's password in the database
                            self.save_password(new_password, username)
                            st.success("Password has been reset successfully!")
                            time.sleep(5)
                            st.session_state["user_mode"]="signedout"
                            nav_to(base_uri+"/streamlit_user")                              
                        else:
                            st.error("Passwords do not match.")
            else:
                st.error("Invalid or expired token.")
 
                

    def save_password(self, password, username, filename=login_file):

        try:
            with open(filename, 'r') as file:
                credentials = yaml.safe_load(file)
                print(credentials)
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
                    # the following takes to "create_empty_profile", which has a rerun, so cannot be in callback
                    self.display_profile()
                 
        

    def about_future(self):

        st.text_area("Where do you see yourself in 5 years?")




    def about_career(self):

        c1, c2 = st.columns([1, 1])
        # components.html( """<div style="text-align: bottom"> Work Experience</div>""")
        with c1:
            st.text_input("Desired job title(s)", placeholder="please separate each with a comma", key="jobx", on_change=self.form_callback)
        with c2:
            st.select_slider("Level of experience",  options=["no experience", "entry level", "junior level", "mid level", "senior level"], key='job_levelx', on_change=self.form_callback)   
        c1, c2=st.columns([1, 1])
        with c1:
            min_pay = st.text_input("Minimum pay", key="min_payx", on_change=self.form_callback)
        with c2: 
            pay_type = st.selectbox("", ("hourly", "annually"), index=None, placeholder="Select pay type...", key="pay_typex", on_change=self.form_callback)
        job_unsure=st.checkbox("Not sure about the job")
        if job_unsure:
            st.multiselect("What industries interest you?", ["Healthcare", "Computer & Technology", "Advertising & Marketing", "Aerospace", "Agriculture", "Education", "Energy", "Entertainment", "Fashion", "Finance & Economic", "Food & Beverage", "Hospitality", "Manufacturing", "Media & News", "Mining", "Pharmaceutical", "Telecommunication", " Transportation" ], key="industryx", on_change=self.form_callback)
        career_switch = st.checkbox("Career switch", key="career_switchx", on_change=self.form_callback)
        if career_switch:
            st.text_area("Transferable skills", placeholder="Please separate each transferable skill with a comma", key="transferable_skillsx", on_change=self.form_callback)
        location = st.checkbox("Location is important to me")
        # location = st.radio("Is location important to you?", [ "no, I can relocate","I only want to work remotely", "I want to work near where I currently live", "I have a specific place in mind"], key="locationx", on_change=self.form_callback)
        if location:
            location_input = st.radio("", ["I want remote work", "work near where I currently live", "I have a specific place in mind"])
            if location_input=="I want remote work":
                st.session_state.location_input = "remote"
            if location_input == "I have a specific place in mind":
                st.text_input("Location", "e.g., the west coast, NYC, or a state", key="location_inputx", on_change=self.form_callback)
            if location_input == "work near where I currently live":
                if st.checkbox("Share my location"):
                    loc = get_geolocation()
                    if loc:
                        address = self.get_address(loc["coords"]["latitude"], loc["coords"]["longitude"])
                        st.session_state["location_input"] = address




    def initialize_resume_callback(self, ):

        """Saves user resume to a lancedb table"""

        resume_dict = create_resume_info(st.session_state.user_resume_path,)
        resume_dict.update({"resume_path":st.session_state.user_resume_path})
        resume_dict.update({"user_id": self.userId}) 
        #NOTE: the data added has to be a LIST!
        schema = convert_pydantic_schema_to_arrow(ResumeUsers)
        add_to_lancedb_table(lance_users_table, [resume_dict], schema)
        print("Successfully added user to lancedb table")
    



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
        
    def form_callback(self):


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
            resume = st.session_state.user_resume
            if resume:
                self.process([resume], "resume")
        except AttributeError:
            pass
        try:
            posting_link = st.session_state.posting_link
            if posting_link:
                self.process(posting_link, "job_posting")
        except AttributeError:
            pass
        try:
            job_descr = st.session_state.job_descriptionx
            if job_descr:
                self.process(job_descr, "job_description")
        except AttributeError:
            pass



    def process(self, input_value: Any, input_type:str):

        """ Processes and checks user inputs and uploads"""

        if input_type=="resume":
            result = process_uploads(input_value, st.session_state.users_upload_path, )
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

        # if input_type=="location_input":
        #     st.session_state.location_input=input_value.split(",")
        # elif input_type=="transferable_skills":
        #     st.session_state.transferable_skills=input_value.split(",")



    @st.experimental_fragment()
    def display_skills(self, ):

        """ Interactive display of skills section of the profile"""

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

        """ Interactive display of specific details such as bullet points in each field"""

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
                    st.button("**+**", key=f"add_{field_name}_{field_detail}_{x}", on_click=add_new_entry, help="add another to list", use_container_width=True)

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

        """Interactive display of content of each profile/resume field """
        #TODO: FUTURE USING DRAGGABLE CONTAINERS TO ALLOW REORDER CONTENT https://discuss.streamlit.io/t/draggable-streamlit-containers/72484?u=yueqi_peng
        def get_display():

            for idx, value in enumerate(st.session_state["profile"][name]):
                add_container(idx, value)
            st.button("add", key=f"add_{name}_button", on_click=add_new_entry, use_container_width=True)
                  
        def add_new_entry():
            # adds new empty entry to profile dict
            if name=="certifications" or name=="licenses":
                st.session_state["profile"][name].append({"description":[],"issue_date":"", "issue_organization":"", "title":""})
            elif name=="work_experience":
                st.session_state["profile"][name].append({"company":"","description":[],"end_date":"","job_title":"","location":"","start_date":""})
            elif name=="awards":
                st.session_state["profile"][name].append({"description":[],"title":""})
            elif name=="projects" or name=="qualifications":
                st.session_state["profile"][name].append({"description":[],"title":""})
            
        def delete_container(placeholder, idx):

            #deletes field container
            print("deleted", st.session_state["profile"][name][idx])
            del st.session_state["profile"][name][idx]
            placeholder.empty()


        def add_container(idx, value):
            
            # adds field container
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
                    get_display= self.display_field_details("work_experience", idx, "description", "bullet_points")
                    get_display()
                

        def callback(idx):
       

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

    def display_field_analysis(self, field_name):

        """ Displays the field-specific analysis UI """

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
                    st.button("tailor again ✨", key=f"tailor_again_{field_name}_button", on_click=self.tailor_callback, args=(field_name, ), )
            else:
                tailor = st.button("tailor ✨",key=f"tailor_{field_name}_button", on_click=self.tailor_callback, args=(field_name, ))

     
          

    @st.experimental_dialog("Please provide a job posting")   
    def job_posting_popup(self,):

        """ Opens a popup for adding a job posting """

        # disables the next button until user provides a job posting
        if "job_posting_path" in st.session_state or "job_description" in st.session_state:
            st.session_state["job_posting_disabled"]=False
        else:
            st.session_state["job_posting_disabled"]=True
        st.info("In case when a job link does not work, please copy and paste the complete job posting into the job description")
        job_posting = st.radio(f" ", 
                                key="job_posting_radio", options=["job description", "job posting link"], 
                                index = 1 if "job_description"  not in st.session_state else 0
                                )
        if job_posting=="job posting link":
            job_posting_link = st.text_input(label="Job posting link",
                                            key="posting_link", 
                                            on_change=self.form_callback,
                                            )
        elif job_posting=="job description":
            job_description = st.text_area("Job description", 
                                        key="job_descriptionx", 
                                        value=st.session_state.job_description if "job_description" in st.session_state else "",
                                        on_change=self.form_callback
                                            )
        if st.button("Next", key="job_posting_button", disabled=st.session_state.job_posting_disabled,):
            # deletes previously generated job posting dictionary 
            try: 
                del st.session_state["job_posting_dict"]
            except Exception:
                pass
            # creates a new job posting dictionary
            st.session_state["job_posting_dict"] = retrieve_or_create_job_posting_info(
                        st.session_state.job_posting_path if "job_posting_path" in st.session_state and st.session_state.job_posting_radio=="job posting link" else "",
                        st.session_state.job_description if "job_description" in st.session_state and st.session_state.job_posting_radio=="job description" else "",  
                    )
            # starts field tailoring if called to tailor a field
            if "tailoring_field" in st.session_state:
                tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"], st.session_state["tailoring_field"])
            # delete "init_tailoring" variable to prevent popup from being called again
            del st.session_state["init_tailoring"]
            st.rerun()

    
    def tailor_callback(self, field_name=None):
      
        if "job_posting_dict" in st.session_state and field_name:
            # starts specific field tailoring
            tailor_resume(st.session_state["profile"], st.session_state["job_posting_dict"], field_name)
        else:
            # initialize a job posting popup 
            st.session_state["init_tailoring"] = True
            if field_name:
                st.session_state["tailoring_field"]=field_name



    def evaluation_callback(self, field_name=None, ):

        if field_name:
            # starts specific evaluation of a field
            evaluate_resume(resume_dict=st.session_state["profile"], type=field_name,)
        else:
            # start general evaluation if haven't done so
            if "eval_dict" not in st.session_state:
                self.eval_thread = thread_with_trace(target=evaluate_resume, args=(st.session_state["profile"], "general", ))
                add_script_run_ctx(self.eval_thread, self.ctx)
                self.eval_thread.start()   
         

    
    def display_profile(self,):

        """Displays interactive user profile UI"""

    
        # initialize a temporary copy of the user profile 
        if "profile" not in st.session_state:
            st.session_state["profile"]=st.session_state["user_profile_dict"]
            # If user has not uploaded a resume, create an empty profile
            if not st.session_state["profile"]:
                self.create_empty_profile() 
                st.rerun()
        # if user calls to tailor fields
        if "init_tailoring" in st.session_state:
            self.job_posting_popup()
        eval_col, profile_col, _ = st.columns([1, 3, 1])   
        _, menu_col, _ = st.columns([3, 1, 3])   
        with eval_col:
            float_container= st.container()
            with float_container:
                # during first preview of the profile, display a button for general evaluation
                # otherwise, unless page refresh, general evaluation will be in a popover
                if "init_eval" not in st.session_state:
                    if st.button("Evaluate my profile ✨", key="init_profile_eval_button"):
                        st.session_state["init_eval"]=True
                        st.rerun()
                else:
                    self.display_general_evaluation(float_container)
                    self.evaluation_callback()
            float_parent()
        # the main profile column
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
                    website = st.session_state["profile"]["contact"]["websites"]
                    st.markdown("Personal websites")
                    display_detail=self.display_field_details("contact", -1, "websites", "bullet_points")
                    display_detail()
            with c2:
                with st.expander(label="Education", expanded=True):
                    degree = st.session_state["profile"]["education"]["degree"]
                    if st.text_input("Degree", value=degree, key="profile_degree", )!=degree:
                        st.session_state["profile"]["education"]["degree"]=st.session_state.profile_degree
                    study = st.session_state["profile"]["education"]["study"]
                    if st.text_input("Area of study", value=study, key="profile_study", )!=study:
                        st.session_state["profile"]["education"]["study"]=st.session_state.profile_study
                    grad_year = st.session_state["profile"]["education"]["graduation_year"]
                    if st.text_input("Graduation year", value=grad_year, key="profile_grad_year", )!=grad_year:
                        st.session_state["profile"]["education"]["graduation_year"]=st.session_state.profile_grad_year
                    gpa = st.session_state["profile"]["education"]["gpa"]
                    if st.text_input("GPA", value=gpa, key="profile_gpa", )!=gpa:
                        st.session_state["profile"]["education"]["gpa"]=st.session_state.profile_gpa
                    st.markdown("Course works")
                    display_detail=self.display_field_details("education", -1, "coursework", "bullet_points")
                    display_detail()
                    # #TODO list courseworks
            with st.expander(label="Summary/Objective",):
                self.display_field_analysis("summary")
                pursuit_jobs = st.session_state["profile"]["pursuit_jobs"]
                if st.text_input("Pursuing job titles", value=pursuit_jobs, key="profile_pursuit_jobs",)!=pursuit_jobs:
                    st.session_state["profile"]["pursuit_jobs"] = st.session_state.pursuit_jobs
                summary = st.session_state["profile"]["summary_objective"]
                if st.text_area("Summary", value=summary, key="profile_summary",)!=summary:
                    st.session_state["profile"]["summary_objective"] = st.session_state.profile_summary
                # if st.button("readability checker"):
                #     st.write(readability_checker(summary))
            with st.expander(label="Work experience",):
                self.display_field_analysis("work_experience")
                get_display=self.display_field_content("work_experience")
                get_display()
            with st.expander(label="Skills",):
                self.display_field_analysis("skills")
                suggested_skills = st.session_state["profile"]["suggested_skills"]
                self.skills_set= set( st.session_state["profile"]["included_skills"])
                self.generated_skills_set=set()
                for skill in suggested_skills:
                    self.generated_skills_set.add(skill["skill"])
                get_display=self.display_skills()
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
        # the menu container
        with menu_col:
            with stylable_container(key="custom_button1",
                            # border-radius: 20px;
                            # background-color: #4682B4;
                        css_styles=["""button {
                            color: white;
                            background-color: #FF6347;
                        }""",
                        # """{
                        #     border: 1px solid rgba(49, 51, 63, 0.2);
                        #     border-radius: 0.5rem;
                        #     padding: calc(1em - 1px)
                        # }
                        # """
                        ],
                ):
                st.button("Set as default", key="profile_save_button", on_click=save_user_changes, args=(st.session_state.profile, ResumeUsers,), use_container_width=True)
                if st.button("Upload a new resume", key="new_resume_button", use_container_width=True):
                    # NOTE:cannot be in callback because streamlit dialogs are not supported in callbacks
                    self.delete_profile_popup()
                st.button("Upload a new job posting", key="new_posting_button", on_click = self.tailor_callback, use_container_width=True)



        

    
    @st.experimental_fragment(run_every=st.session_state["eval_rerun_timer"])
    def display_general_evaluation(self, container):

        """ Displays the general evaluation result of the profile """

        # eval_dict= self.get_dict("evaluation")
        try:
            eval_dict= st.session_state["eval_dict"]
        except Exception:
            eval_dict={}
        if eval_dict:
            if "finished_eval" in st.session_state:
                display_name = "Your evaluation results are in! ✨"
                button_name = "evaluate again ✨"
            else:
                display_name = "Your profile is being evaluated ✨..."
                button_name="stop evaluation"
            with st.popover(display_name):
                c1, c2=st.columns([1, 1])
                with c1:
                    st.write("**Length**")
                    try:
                        length=eval_dict["word_count"]
                        pages=eval_dict["page_number"]
                        fig = self.display_length_chart(length)
                        st.plotly_chart(fig, 
                                        # use_container_width=True
                                        )
                    except Exception:
                        if "finished_eval" not in st.session_state:
                            st.write("Evaluating...")
                with c2:
                    st.write("**Formatting**")
                    try:
                        add_vertical_space(3)
                        ideal_type = eval_dict["ideal_type"]
                        resume_type=eval_dict["resume_type"]
                        if ideal_type==resume_type:
                            st.subheader(":green[Good]")
                            st.write(f"The best type of resume for you is **{ideal_type}** and your resume is also **{resume_type}**")
                        else:
                            st.subheader(":red[Mismatch]")
                            st.write(f"The best type of resume for you is **{ideal_type}** but your resume seems to be **{resume_type}**")
                        if not st.session_state["eval_rerun_timer"]:
                            add_vertical_space(1)
                            if st.button("Why the right type matters?", type="primary", key="resume_type_button"):
                                self.resume_type_popup()
                            # add_vertical_space(1)
                            # if st.button("Explore template options", key="resume_template_explore_button"):
                            #     self.explore_template_popup()
                    except Exception:
                        if "finished_eval" not in st.session_state:
                            st.write("Evaluating...")
                st.write("**Language**")
                try:
                    fig = self.display_language_radar(eval_dict["language"])
                    st.plotly_chart(fig)
                    # st.scatter_chart(df)
                except Exception:
                    if "finished_eval" not in st.session_state:
                        st.write("Evaluating...")
                st.write("**How does your resume compared to other resume?**")
                try:
                    fig = self.display_comparison_chart(eval_dict["comparison"])
                    st.plotly_chart(fig)
                except Exception:
                    if "finished_eval" not in st.session_state:
                        st.write("Evaluating...")
                st.write("**Impression**")
                try:
                    impression = eval_dict["impression"]
                    st.write(impression)
                    # finished evaluataion, stop timer
                    if "finished_eval" not in st.session_state:
                        st.session_state["finished_eval"] = True
                        st.session_state["eval_rerun_timer"]=None
                        st.rerun()
                except Exception:
                    if "finished_eval" not in st.session_state:
                        st.write("Evaluating...")
                if st.button(button_name, key=f"eval_button", ):
                    if button_name=="evaluate again ✨":
                        container.empty()
                        # delete previous evaluation states
                        try:
                            del st.session_state["eval_dict"]
                            del st.session_state["finished_eval"]
                        except Exception:
                            pass
                        finally:
                            # reset evaluation rerun timer
                            st.session_state["eval_rerun_timer"]=3
                            st.rerun()
                    elif button_name=="stop evaluation":
                        try:
                            # kill the evaluation thread 
                            self.eval_thread.kill()
                            self.eval_thread.join()
                        except Exception as e:
                            print(e)
                            pass
                        finally:
                            # stop timer and finished evaluation
                            st.session_state["eval_rerun_timer"] = None
                            st.session_state["finished_eval"] = True
                        st.rerun()


    @st.experimental_dialog(" ")
    def resume_type_popup(self, ):
        st.image("./resources/functional_chronological_resume.png")
    
    @st.experimental_dialog(" ", width="large")
    def explore_template_popup(self, ):
        """"""
        type = sac.tabs([
            sac.TabsItem(label='functional',),
            sac.TabsItem(label='chronological',),
            sac.TabsItem(label='mixed', ),
        ], align='center', variant="outline")

        if type=="functional":
            st.image(["./resources/functional/functional0.png", "./resources/functional/functional1.png", "./resources/functional/functional2.png"])
        elif type=="chronological":
            st.image(["./resources/chronological/chronological0.png", "./resources/chronological/chronological1.png", "./resources/chronological/chronological2.png"])


    def create_empty_profile(self):

        """ In case user did not upload a resume, this creates an empty profile and saves it as a lancedb table entry"""

        filename = str(uuid.uuid4())
        end_path =  os.path.join( st.session_state.user_save_path, "", "uploads", filename+'.txt')
        #creates an empty file
        with open(end_path, "w") as f:
            pass
        st.session_state["profile"] = {"user_id": self.userId, "resume_path": end_path, "resume_content":"",
                   "contact": {"city":"", "email": "", "linkedin":"", "name":"", "phone":"", "state":"", "websites":[], }, 
                   "education": {"coursework":[], "degree":"", "gpa":"", "graduation_year":"", "institution":"", "study":""}, 
                   "pursuit_jobs":"", "summary_objective":"", "included_skills":[], "work_experience":[], "projects":[], 
                   "certifications":[], "suggested_skills":[], "qualifications":[], "awards":[], "licenses":[], "hobbies":[]}
        save_user_changes(st.session_state.profile, ResumeUsers)
       


    @st.experimental_dialog("Warning")
    def delete_profile_popup(self):

        """ Opens a popup that warns user before uploading a new resume """

        add_vertical_space(2)
        st.warning("Your current profile will be lost. Are you sure?")
        add_vertical_space(2)
        c1, _, c2 = st.columns([1, 1, 1])
        with c2:
            if st.button("yes, I'll upload a new one", type="primary", ):
                delete_user_from_table(self.userId)
                 # delete session-specific copy of the profile and evaluation
                try:
                    del st.session_state["profile"]
                    del st.session_state["eval_dict"]
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
                
    def display_length_chart(self, length):
        if length<300:
            text = "too short"
        elif length>=300 and length<450:
            text="could be longer"
        elif length>=450 and length<=600:
            text="good length"
        elif length>600 and length<800:
            text="could be shorter"
        else:
            text="too long"
        # Cap the displayed value at 1000, bust keep the actual value for the text annotation
        display_value = min(length, 1000)
        # Create a gauge chart
        fig = go.Figure(go.Indicator(
            mode = "gauge",
            value = display_value,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Your resume is:"},
            gauge = {
                    # 'shape':"bullet",
                    'axis': {'range': [1, 1000]},
                    'bar': {'color': "white", "thickness":0.1},
                    'steps': [
                        {'range': [1, 300], 'color': "red"},
                        {'range': [300, 450], "color":"yellow"},
                        {'range': [450, 600], 'color': "lightgreen"},
                            {'range': [600, 800], "color":"yellow"},
                        {'range': [800, 1000], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 1},
                        'thickness': 0.2,
                        'value': display_value
                    }
                }
        ))
        # Add annotation for the text
        fig.add_annotation(
            x=0.5, 
            y=0.5, 
            text=text, 
            showarrow=False,
            font=dict(size=24)
        )
        return fig


    def display_comparison_chart(self, data):
        # Mapping from similarity categories to numeric values
        similarity_mapping = {
            'no similarity': 0,
            'some similarity': 1,
            'very similar': 2,
             'no data': -1  # Map empty strings to -1,
        }
        size_mapping = {
            'no similarity': 10,
            'some similarity': 20,
            'very similar': 30,
            'no data': 5  # Size for empty strings
        }
        # Extract fields and similarity values
        fields = []
        values = []
        hover_texts = []
        sizes = []
        for item in data:
            for field, similarity in item.items():
                fields.append(field)
                values.append(similarity_mapping[similarity["closeness"] if similarity["closeness"] else 'no data'])
                sizes.append(size_mapping[similarity["closeness"] if similarity["closeness"] else "no data"])
                hover_texts.append(similarity["reason"] if similarity["reason"] else " ")

        # Create scatter plot
        # fig = px.scatter(
        #     x=fields,
        #     y=values,
        #     # color=values,
        #     # color_continuous_scale='Viridis',
        #     mode='markers',
        #     marker=dict(
        #         size=sizes
        #     ),
        #     labels={'x': 'Resume Field', 'y': 'Similarity Level'},
        #     # title='Resume Similarity Scatter Plot',
        #     # hover_data={'x': fields, 'y': [list(similarity_mapping.keys())[list(similarity_mapping.values()).index(val)] for val in values]}
        # )
        # Create scatter plot
        fig = go.Figure(data=go.Scatter(
            x=fields,
            y=values,
            mode='markers',
            marker=dict(
                size=sizes
            ),
            text=hover_texts,  # Add custom hover text
            hoverinfo='text'  # Display only the custom hover text
        ))
        # Add custom hover text
        fig.update_traces(
            hovertext=hover_texts,
            hoverinfo='text'  # Display only the custom hover text
        )
        fig.update_yaxes(
            tickmode='array',
            tickvals=[-1, 0, 1, 2],
            ticktext=['No data', 'No similarity', 'Some similarity', 'Very similar'],
            range=[0, 2]
        )
        return fig
        
    def display_language_radar(self, data_list):
        # Sample data
        # Mapping from categories to numeric values
        category_mapping = {"no data": 0, 'bad': 1, 'good': 2, 'great': 3}
        metrics = []
        values = []
        hover_texts=[]
        for item in data_list:
            for metric, details in item.items():
                metrics.append(metric)
                values.append(category_mapping[details['rating'] if details['rating'] else 'no data'])
                hover_texts.append(details["reason"] if details['reason'] else " ")

        # Add the first value at the end to close the radar chart circle
        values.append(values[0])
        metrics.append(metrics[0])
        print("ratings", values)
        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=metrics,
            fill='toself', 
            hovertext=hover_texts,  # Add custom hover text
            hoverinfo='text'  # Display only the hover text
        ))
        # Define axis labels
        axis_labels = {1: 'Bad', 2: 'Good', 3: 'Great'}
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 3],  # Set the range for the radial axis
                    tickvals=list(axis_labels.keys()),  # Specify the ticks
                    ticktext=[axis_labels[val] for val in axis_labels.keys()]  # Set the labels
                )
            ),
        )
        return fig


    def display_readability_indicator(self, value):
        min_value = 0
        max_value = 100
        steps = [20, 40, 60, 80]
        indicator_color = "red"
        line_color = "black"

        # Create the figure
        fig = go.Figure()

        # Add the horizontal line
        fig.add_trace(go.Scatter(
            x=[min_value, max_value],
            y=[0, 0],
            mode='lines',
            line=dict(color=line_color, width=2)
        ))

        # Add the indicators
        for step in steps:
            fig.add_trace(go.Scatter(
                x=[step, step],
                y=[-0.1, 0.1],
                mode='lines',
                line=dict(color=line_color, width=2)
            ))

        # Add the dot for the value
        fig.add_trace(go.Scatter(
            x=[value],
            y=[0],
            mode='markers',
            marker=dict(color=indicator_color, size=10)
        ))

        # Update layout to remove axis
        fig.update_layout(
            xaxis=dict(
                range=[min_value, max_value],
                showgrid=False,
                zeroline=False,
                showline=False,
                showticklabels=False
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=False,
                showticklabels=False
            ),
            margin=dict(l=0, r=0, t=0, b=0)
        )
        return fig






if __name__ == '__main__':

        user=User()
    

