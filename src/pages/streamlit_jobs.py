import streamlit as st
import uuid
import os
import json
from json import JSONDecodeError
from backend.job_recommender import Recommender
from utils.cookie_manager import CookieManager

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
        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
            # Ask user to sign in
        if not self.userId:
            print("User needs to sign in first before job search")
            st.session_state.redirect_page="http://localhost:8501/streamlit_jobs"
            st.switch_page("pages/user.py")
        self._init_session_states()
        self._init_job_recommender()



    @st.cache_data()
    def _init_session_states(_self, ):
            # Open users profile file
        try:
            st.session_state["users"]
        except Exception:
            with open(user_profile_file, 'r') as file:
                try:
                    users = json.load(file)
                except JSONDecodeError:
                    raise
                    # users = {}  
                    # users[_self.userId]={}
            st.session_state["users"] = users
            st.session_state["users_dict"] = {user['userId']: user for user in st.session_state.users}
        try:
            st.session_state["user_profile"]=st.session_state["users_dict"][_self.userId]
        except Exception:
            st.session_state.redirect_page="http://localhost:8501/streamlit_jobs"
            st.switch_page("pages/user.py")
      

    

    def _init_job_recommender(self):


        if "base_recommender" not in st.session_state:
            st.session_state["base_recommender"]= Recommender()
            self.recommend_job()

    def recommend_job(self):

        try:
            query = st.session_state["user_profile"]
            matched_urls = st.session_state.base_recommender.match_job(query)
            for url in matched_urls:
                st.markdown(url)
        except Exception:
            raise

if __name__ == '__main__':
    job = Job()