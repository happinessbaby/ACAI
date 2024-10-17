import streamlit as st

def callback():
    call = st.session_state.test_balloons
    if call:
        print("AAAAAAAAAAAa")
        st.balloons()
    else:
        print("BBBBBBBBBBBBBBB")


# @st.fragment
def test():
    button = st.toggle("turn on", on_change=callback, value=True, key="test_balloons")
    # if button:
    #     st.balloons()

test()
