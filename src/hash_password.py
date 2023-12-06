import streamlit_authenticator as stauth
hashed_passwords = stauth.Hasher(['Pyq901210', 'def']).generate()
print(hashed_passwords)