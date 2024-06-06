import streamlit as st
import uuid
import os
import json
from json import JSONDecodeError
from backend.job_recommender import Recommender
from utils.cookie_manager import get_cookie, decode_jwt

STORAGE = os.environ['STORAGE']
bucket_name = os.environ["BUCKET_NAME"]
login_file = os.environ["LOGIN_FILE_PATH"]
db_path=os.environ["LANCEDB_PATH"]
user_profile_file=os.environ["USER_PROFILE_FILE"]

st.markdown("<style> ul {display: none;} </style>", unsafe_allow_html=True)


class Job():
    
    # cookie = get_cookie("userInfo")
    # aws_session = get_aws_session()
    # cookie_manager = get_cookie_manager()
    # st.write(get_all_cookies())

    def __init__(self):
        # NOTE: userId is retrieved from browser cookie
        self.cookie = get_cookie("userInfo")
        print("Cookie", self.cookie)
        if self.cookie:
            self.userId = str(decode_jwt(self.cookie, "test").get('username'))
        else:
            # Ask user to sign in
            print("User needs to sign in first before job search")
            st.switch_page("pages/streamlit_user.py")
            #TODO: redirect back to this page
        self._init_session_states()
        self._init_job_recommender()



    @st.cache_data()
    def _init_session_states(_self, ):
            # Open users profile file
        with open(user_profile_file, 'r') as file:
            try:
                users = json.load(file)
            except JSONDecodeError:
                users = {}  
                users[_self.userId]={}
        st.session_state["users"] = users

    def _init_job_recommender(self):
         if "base_recommender" not in st.session_state:
            st.session_state["base_recommender"]= Recommender()
            self.recommend_job()

    def recommend_job(self):

        try:
            query = st.session_state["users"][self.userId]["summary"]
            matched_urls = st.session_state.base_recommender.match_job(query)
            for url in matched_urls:
                st.markdown(url)
        except Exception:
            raise

if __name__ == '__main__':
    job = Job()