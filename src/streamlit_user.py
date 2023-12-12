import streamlit as st
from my_component import my_component
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import os
from google.oauth2 import id_token
from google.auth.transport import requests

CLIENT_ID = os.environ['GOOGLE_DEFAULT_CLIENT_ID'].split(".")[0]
sign_in_placeholder=st.empty()




class User():
    
    signed_in = False if "signed_in" not in st.session_state else True

    def __init__(self):
        self._sign_in()

    def _sign_in(self):

# client_secret = os.environ['GOOGLE_DEFAULT_CLIENT_SECRET']
# # client = GoogleOAuth2(client_id, client_secret)
# redirect_uri = os.environ['REDIRECT_URI']


    # async def write_authorization_url(self, client,
    #                               redirect_uri):
    #     authorization_url = await client.get_authorization_url(
    #         redirect_uri,
    #         scope=["email"],
    #         extras_params={"access_type": "offline"},
    #     )
    #     return authorization_url
    
    # async def write_access_token(self, client,
    #                          redirect_uri,
    #                          code):
    #     token = await client.get_access_token(code, redirect_uri)
    #     return token

# def google_token_check():

#     try:
#         # Specify the CLIENT_ID of the app that accesses the backend:
#         idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)

#         # Or, if multiple clients access the backend server:
#         # idinfo = id_token.verify_oauth2_token(token, requests.Request())
#         # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
#         #     raise ValueError('Could not verify audience.')

#         # If auth request is from a G Suite domain:
#         # if idinfo['hd'] != GSUITE_DOMAIN_NAME:
#         #     raise ValueError('Wrong hosted domain.')

#         # ID token is valid. Get the user's Google Account ID from the decoded token.
#         userid = idinfo['sub']
#         #After you have verified the token, check if the user is already in your user database.
#         #  If so, establish an authenticated session for the user. If the user isn't yet in your user database, create a new user record from the information in the ID token payload, and establish a session for the user. 
#         # You can prompt the user for any additional profile information you require when you detect a newly created user in your app.
#         st.session_state.signed_in=True
#     except ValueError:
#         # Invalid token
#         pass

# if "signed_in" not in st.session_state:
#     st.session_state["signed_in"]=False
        with open('./user_login.yaml') as file:
            config = yaml.load(file, Loader=SafeLoader)
        authenticator = stauth.Authenticate( config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'], config['preauthorized'] )

        if self.signed_in==False:
            with sign_in_placeholder.container():
                user_info = my_component(name="signin", key="signin")
                if user_info:
                    st.session_state["signed_in"] = "google"
                    st.rerun()
                # if token:
                #     try:
                #         token = requests.get("http://localhost:8501")
                #         # Specify the CLIENT_ID of the app that accesses the backend:
                #         idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
                #         # ID token is valid. Get the user's Google Account ID from the decoded token.
                #         userid = idinfo['sub']
                #         #After you have verified the token, check if the user is already in your user database.
                #         #  If so, establish an authenticated session for the user. If the user isn't yet in your user database, create a new user record from the information in the ID token payload, and establish a session for the user. 
                #         # You can prompt the user for any additional profile information you require when you detect a newly created user in your app.
                #         st.session_state["signed_in"]="google"
                #         st.rerun()
                #     except ValueError:
                #         # Invalid token
                #         pass


            # authorization_url = asyncio.run(
                        #     self.write_authorization_url(client=client,
                        #                         redirect_uri=redirect_uri)
                        # )
                        # google = st.link_button(label="Google", url=authorization_url)
                        # google = st.write(f'''
                        #     <a target="_self" href={authorization_url}>
                        #         <button>
                        #             Please login via Google
                        #         </button>
                        #     </a>
                        #     ''',
                        #     unsafe_allow_html=True
                        # )
                        # sign_in = st.button(label="sign in")
                        # sign_up = st.button(label="sign up")
                        # if google:
                        #     try:
                        #         code = st.experimental_get_query_params()['code']
                        #     except Exception:
                        #         pass
                name, authentication_status, username = authenticator.login('Login', 'main')
                print(name, authentication_status, username)
                if authentication_status:
                    st.session_state["signed_in"] = "system"
                    st.rerun()
                elif authentication_status == False:
                    st.error('Username/password is incorrect')
                elif authentication_status == None:
                    st.warning('Please enter your username and password')
                sign_up = st.button(label="sign up", key="signup")
                if sign_up:
                    st.session_state["signed_in"] = "system"
                    st.rerun()

                    # try:
                    #     if authenticator.register_user("Register user", "main", preauthorization=False):
                    #         st.success("User registered successfully")
                    #         st.session_state["signed_in"]="system"
                    #         st.rerun()
                    # except Exception as e:
                    #     st.error(e)

                        # with open("./login.yaml", "w") as file:
                        #     yaml.dump(config, file, default_flow_style=False)
                            # if code:
                        #     token = asyncio.run(
                        #     self.write_access_token(client=client,
                        #                 redirect_uri=redirect_uri,
                        #                     code=code))
                        # st.session_state["login"] = token if token is not None else st.session_state.userid   
        else:
            logout = authenticator.logout('Logout', 'sidebar')
            if logout:
                logout = my_component("signout", key="signout")
                del st.session_state.signed_in
                print("logging out")
            st.title("welcome back!") 
            #TODO ADD USER PERSONALIZED PAGE HERE



if __name__ == '__main__':
    user = User()

