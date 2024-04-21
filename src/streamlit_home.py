import streamlit as st


# Application Process, Job Search, Mock Interview
st.set_page_config(initial_sidebar_state="collapsed", layout="wide")


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


st.markdown("<h1 style='text-align: center; color: black;'>Welcome</h1>", unsafe_allow_html=True)
st.markdown("#")
st.markdown("<h3 style='text-align: center; color: black ;'> Let AI empower your job application journey</h3>", unsafe_allow_html=True)
# st.markdown("## Let AI empower your job application journey ##")
st.markdown("#")
left_space, c1, c2, c3, right_space = st.columns([1, 1, 1, 1, 1])
with c1:
    st.page_link("pages/streamlit_chatbot.py", label="Resume Help", )
with c2:
    st.page_link("pages/streamlit_user.py", label="Job Search", )
with c3:
    st.page_link("pages/streamlit_interviewbot.py", label="Mock Interview",)