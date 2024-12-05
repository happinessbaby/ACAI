import json
from utils.cookie_manager import retrieve_cookie, init_cookies
from streamlit_utils import nav_to, user_menu, progress_bar, set_streamlit_page_config_once, bottom_info
# from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.buy_me_a_coffee import button
import streamlit as st

set_streamlit_page_config_once()

# STORAGE = os.environ["STORAGE"]
# if STORAGE=="CLOUD":
#     bucket_name = os.environ["BUCKET_NAME"]
#     s3_save_path = os.environ["S3_CHAT_PATH"]
#     session = boto3.Session(         
#                     aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"],
#                     aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"],
#                 )
#     s3 = session.client('s3')
#     s3_fs = s3fs.S3FileSystem(key=os.environ["AWS_SERVER_PUBLIC_KEY"], secret=os.environ["AWS_SERVER_SECRET_KEY"])
# else:
#     bucket_name=None
#     s3=None
# st.logo("./resources/logo_acareerai.png")

class Feedback():


    def __init__(self):
        
        # st.session_state["current_page"] = "feedback"
        init_cookies()
        if "userId" not in st.session_state:
            st.session_state["userId"] = retrieve_cookie()
        self._init_display()

    # def _init_session_states(_self, ):

    #     if "user_save_path" not in st.session_state:
    #         if STORAGE=="CLOUD":
    #             st.session_state["user_save_path"] = os.path.join(os.environ["S3_USER_PATH"], _self.userId, "profile")
    #         elif STORAGE=="LOCAL":
    #             st.session_state["user_save_path"] = os.path.join(os.environ["USER_PATH"], _self.userId, "profile")
    #         # Get the current time
    #         now = datetime.now()
    #         # Format the time as "year-month-day-hour-second"
    #         formatted_time = now.strftime("%Y-%m-%d-%H-%M")
    #         st.session_state["users_upload_path"] = os.path.join(st.session_state.user_save_path, "uploads", formatted_time)
    #         st.session_state["users_download_path"] =  os.path.join(st.session_state.user_save_path, "downloads", formatted_time)
    #         paths=[st.session_state["users_download_path"]]
    #         mk_dirs(paths,)

    def _init_display(self, ):

        user_menu(st.session_state.userId, page="feedback")
        # progress_bar(2)
        add_vertical_space(10)
        self.leave_feedback()
        st.divider()
        bottom_info()


    def leave_feedback(self, ):
        _, c1, _ = st.columns([1, 1, 1])
        with c1: 
            with st.container(border=True):
                st.write("**Your feedback will help us improve**")
                st.write("Helpfulness")
                helpfulness = st.feedback(options="faces", key="helpfulness_rating",)
                st.write('Ease of use')
                use = st.feedback(options="faces", key="use_rating")
                st.write('Speed')
                speed = st.feedback(options="faces", key="speed_rating")
                st.write("How likely are you to use the resume builder?")
                likeliness=st.feedback(options="faces", key="continue_rating")
                # helpfulness = sac.rate(label='helpfulness', color="yellow", )
                # use= sac.rate(label='ease of use', color="yellow",)
                # speed = sac.rate(label='speed', color="yellow",)
                suggestions = st.text_area("Anything else you'd like to let us know?", )
                st.button("Submit", on_click=self.save_feedback, args = (helpfulness, use, speed, suggestions, likeliness))

    def save_feedback(self, helpfulness, use, speed, suggestions, likeliness):
        # st.session_state["feedback"]=True
        feedback = {st.session_state.userId:{"helpfulness":helpfulness, "ease of use":use, "speed":speed, "suggestions":suggestions, "continue":likeliness}}
        with open("user_feedback.json", "w") as f:
            json.dump(feedback, f)
        st.success("Thank you for your feedback! We will use your feedback to continue improving our products.")

        

        



          

if __name__ == '__main__':

    feedback=Feedback()