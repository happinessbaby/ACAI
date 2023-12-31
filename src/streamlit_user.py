import streamlit as st
import extra_streamlit_components as stx
from my_component import my_component
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from cookie_manager import get_cookie, set_cookie, delete_cookie, get_all_cookies
import time
import datetime
from streamlit_modal import Modal
from dynamodb_utils import save_user_info
from langchain.utilities import SerpAPIWrapper
from langchain.agents import Tool
from langchain.tools.file_management.write import WriteFileTool
from langchain.tools.file_management.read import ReadFileTool
from langchain.vectorstores import FAISS
from langchain.docstore import InMemoryDocstore
from langchain.embeddings import OpenAIEmbeddings
from langchain_experimental.autonomous_agents import AutoGPT
from langchain.chat_models import ChatOpenAI
from aws_manager import get_aws_session
from dynamodb_utils import init_table, check_attribute_exists
import faiss
import re
import uuid


from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

login_file = os.environ["LOGIN_FILE"]
STORAGE = os.environ['STORAGE']


class User():
    
    cookie = get_cookie("userInfo")
    aws_session = get_aws_session()
    # st.write(get_all_cookies())

    def __init__(self):
             # self.userId = self.cookie.split("###")[1]
        if self.cookie:
            self.userId = re.split("###|@", self.cookie)[1]
            print(self.userId)
        else:
            self.userId = None
        if "sessionId" not in st.session_state:
            st.session_state["sessionId"] = str(uuid.uuid4())
            print(f"Session: {st.session_state.sessionId}")
        self._init_session_states()
        self._init_user()

    def _init_session_states(_self):

        if _self.userId is not None:
            if "dnm_table" not in st.session_state:
                st.session_state["dnm_table"] = init_table(session=_self.aws_session, userId=_self.userId)
                print('successfully initiated dnm_table')
            if "init_user" not in st.session_state:
                # if check_attribute_exists(st.session_state.dnm_table, key=_self.userId, attribute="about user")==False:
                try:
                    if st.session_state["about_me_modal"]:
                        _self.about_me_popup()
                except KeyError:
                    st.session_state["about_me_modal"]=True
                    _self.about_me_popup()

                # if _self.about_me_popup():
                #     st.session_state["init_user"]=True
                # else:
                #     st.session_state["init_user"]=False
        if "s3_client" not in st.session_state:
            if STORAGE=="LOCAL":
                st.session_state["s3_client"]=None
            elif STORAGE=="S3":
                st.session_state["s3_client"] = _self.aws_session.client('s3') 


    def _init_user(self):

        if self.cookie is None:
            with open(login_file) as file:
                config = yaml.load(file, Loader=SafeLoader)
            authenticator = stauth.Authenticate( config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'], config['preauthorized'] )
            try:
                if st.session_state["signin_modal"]:
                     self._sign_in(authenticator)
                else:
                    st.sidebar.button("signin")
            except KeyError:
                st.session_state["signin_modal"]=True
                self._sign_in(authenticator)
        else:
            with open(login_file) as file:
                config = yaml.load(file, Loader=SafeLoader)
            authenticator = stauth.Authenticate( config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'], config['preauthorized'] )
            logout = authenticator.logout('Logout', 'sidebar')
            if logout:
                # Hacky way to log out of Google
                with st.spinner("logging out"):
                    print(get_all_cookies())
                    delete_cookie(get_cookie("userInfo"), key="deleteCookie")
                    _ = my_component("signout", key="signout")
            self._create_user_page()
    




    def _sign_in(self, authenticator:stauth.Authenticate):

        modal = Modal("   ", key="sign_in_popup", max_width=500, close_button=False)
        with modal.container():
            st.button("X", on_click=self.close_modal, args=["signin_modal"])
            user_info = my_component(name="signin", key="signin")
            st.markdown("or")
            with st.expander(label="log in"):
                name, authentication_status, username = authenticator.login('', 'main')
                col1, col2 = st.columns(2, gap='large')
                with col2:
                    forgot_password = st.button(label="forgot my password", key="forgot", type="primary")

            print(user_info)
            if user_info!=-1:
                print(f"user signed in through google: {user_info}")
                # NOTE: Google's token expires after 1 hour
                set_cookie("userInfo", user_info, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
                # st.write(get_all_cookies())
                # st.rerun()
            # print(name, authentication_status, username)
            if authentication_status:
                print("user signed in through system")
                set_cookie("userInfo", user_info, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
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
            col1, col2 = st.columns(2, gap='large')
            with col1:
                sign_up = st.button(label="sign up", key="signup", on_click=self._sign_up, args=[authenticator], type="primary")
            


    def _sign_up(self, authenticator:stauth.Authenticate):

        try:
            modal = Modal("Welcome", key="register", max_width=500)
            with modal.container():
                if authenticator.register_user("Create an account", "main", preauthorization=False):
                    st.success("User registered successfully")
                    set_cookie("userInfo", user_info, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
        except Exception as e:
            st.error(e)
    

        # with open(login_file, "w") as file:
        #     yaml.dump(config, file, default_flow_style=False)



    def close_modal(self, name):
        st.session_state[name]=False


    def about_me_popup(_self) -> None:
    
        """ Processes user's about me input. """

        modal = Modal(title="", key="about_popup", max_width=800, close_button=False)
        if st.session_state.get("past", False) and st.session_state.get("present", False) and st.session_state.get("future", False) :
            st.session_state.disabled=False
        else:
            st.session_state.disabled=True
        with modal.container():
            st.button("X", on_click=_self.close_modal, args=["about_me_modal"])
            selected = stx.stepper_bar(steps=["Self Description", "Current Situation", "Career Goals"])
            if selected==0:
                st.text_input(
                label="What can I know about you?", 
                placeholder="Tell me about yourself", 
                key = "about_past", 
                on_change=_self.about_me_form_check
                )
            elif selected==1:
                st.text_input(
                label="What takes you here?",
                placeholder = "Tell me about your present situation",
                key="about_present",
                on_change = _self.about_me_form_check
                )
            elif selected==2:
                st.text_input(
                label="What can I do for you?",
                placeholder = "Tell me about your career goals",
                key="about_future",
                on_change=_self.about_me_form_check,
                )
            submitted = st.button("Submit", on_click=_self.form_callback, disabled=st.session_state.disabled)
            if submitted:
                st.session_state["init_user"]=True
                modal.close()

                
        
    def about_me_form_check(self):

        # Hacky way to save input text for stepper bar for batch submission
        try:
            st.session_state["past"] = st.session_state.about_past
        except AttributeError:
            pass
        try:
            st.session_state["present"] = st.session_state.about_present
        except AttributeError:
            pass
        try:
            st.session_state["future"] = st.session_state.about_future
        except AttributeError:
            pass

    def _create_user_page(self):
        chosen_id = stx.tab_bar(data=[
                stx.TabBarItemData(id=1, title="ToDo", description="Tasks to take care of"),
                stx.TabBarItemData(id=2, title="Done", description="Tasks taken care of"),
                stx.TabBarItemData(id=3, title="Overdue", description="Tasks missed out"),
            ], default=1)
        st.info(f"{chosen_id=}")
        #TODO ADD USER PERSONALIZED PAGE HERE

    def form_callback(self):

        try:
            about_past = st.session_state.past
            save_user_info(st.session_state.dnm_table, self.userId, "self description", about_past)
            print("successfully saved about past")
        except Exception:
            pass
        try:
            about_present = st.session_state.present
            save_user_info(st.session_state.dnm_table, self.userId, "current situation", about_present)
        except Exception:
            pass
        try:
            about_future = st.session_state.future
            save_user_info(st.session_state.dnm_table, self.userId, "career goal", about_future)
        except Exception:
            pass





if __name__ == '__main__':
    user = User()

