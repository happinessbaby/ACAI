import streamlit as st

# Custom CSS 
st.markdown(
    '''
    <style>
    .streamlit-expanderHeader {
        background-color: orange;
        color: orange; # Adjust this for expander header color
    }
    .streamlit-expanderContent {
        background-color: orange;
        color: orange; # Expander content color
    }
    </style>
    ''',
    unsafe_allow_html=True
)

with st.expander("Expand"):
    st.write("Content inside the expander")