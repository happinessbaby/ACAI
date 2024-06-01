import streamlit as st
from backend.upgrade_resume import evaluate_resume

st.set_page_config(layout="wide")


def main():
    tab1, tab2, tab3 = st.tabs(["Evaluation Result", "Reformatted Resume", "Tailoring"])
    with tab1:
        display_resume_eval()
        st.session_state["eval_dict"]=evaluate_resume(resume_file=st.session_state["resume_path"], 
                            resume_dict = st.session_state["resume_dict"], 
                            job_posting_dict = st.session_state["job_posting_dict"] if "job_posting_path" in st.session_state else "",
                                )


@st.experimental_fragment(run_every=3)
def display_resume_eval(): 
    """ Displays resume evaluation result"""
    _, c1, c2 = st.columns([1, 2, 2])
    try:
        eval_dict= st.session_state.eval_dict
    except Exception:
        eval_dict={}
    with c1:
        with st.container():
            st.title("Length")
            st.write("A resume has an ideal length or 450 to 650 words, about one page long.")
            try:
                length=eval_dict["word_count"]
                pages=eval_dict["page_number"]
                st.write(f"Yours: {length} words & {pages}")
            except Exception:
                st.write("Evaluating...")
    with c2:
        with st.container():
            st.title("Type")
            st.button("explore template options")
            try:
                ideal_type = eval_dict["ideal_type"]
                st.write(f"The ideal type for your need: \n{ideal_type}")
                type_analysis = eval_dict["type_analysis"]
                st.write(f"Analysis: \n {type_analysis}")
            except Exception:
                st.write("Evaluating...")
            # st.help(functional)
    _, c3, c4 = st.columns([1, 2, 2])
    with c3:
        with st.container():
            st.title("Impression")
            st.write("overall impression: \n")
            try:
                overall_impression = eval_dict["overall_impression"]
                st.write(overall_impression)
            except Exception:
                st.write("Evaluating...")
    with c4:
        with st.container():
            st.title("In-depth Analysis")
            st.write("Work experience")

    back = st.button("Go back to main menu", type="primary", )
    if back:
        st.switch_page("./streamlit_chatbot.py")


main()