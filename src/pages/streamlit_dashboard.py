import streamlit as st
from backend.upgrade_resume import evaluate_resume, tailor_resume, eval_dict, tailor_dict
from streamlit.components.v1 import html, iframe
import pandas as pd
import threading
import multiprocessing


st.set_page_config(layout="wide")
st.session_state["tabs"] = []
html("""
    <script>
      parent.window.onbeforeunload = function() {
        return "Data will be lost if you leave the page, are you sure?";
        };
    </script>
    """)
section_names = {"objective_summary_section", "work_experience_section"}

def main():
    if "evaluation" in st.session_state:
        st.session_state["tabs"].append("Evaluation")
    # if "reformatting" in st.session_state:
    #     st.session_state["tabs"].append("Reformatted resume")
    if "tailoring" in st.session_state:
        st.session_state["tabs"].append("Tailoring")

    tabs = st.tabs(st.session_state["tabs"])
    num_tabs = len(st.session_state.tabs)
    count=0
    
    if "Evaluation" in st.session_state.tabs:
        with tabs[count]:
            display_resume_eval()
            thread = threading.Thread(
                target = evaluate_resume,
                args=(
                    st.session_state["resume_path_final"], 
                    st.session_state["resume_dict"], 
                    st.session_state["job_posting_dict"] if "job_posting_path" in st.session_state else "",
                ),
                daemon=True, 
                )
            thread.start()
        count+=1
    # if "Reformatted resume" in st.session_state.tabs: 
    #     with tabs[count]:
    #         if type=="chronological":
    #             reformat_chronological_resume(resume_file=st.session_state["resume_path_final"], 
    #                                 posting_path = st.session_state["job_posting_path"] if "job_posting_path" in st.session_state else "", 
    #                                 template_file=st.session_state["template_path"],
    #                                 )
    #         elif type=="functional":
    #             reformat_functional_resume(resume_file=st.session_state["resume_path_final"], 
    #                                 posting_path = st.session_state["job_posting_path"] if "job_posting_path" in st.session_state else "", 
    #                                 template_file=st.session_state["template_path"],
    #                                 )
    #         elif type=="student":
    #             reformat_student_resume(resume_file=st.session_state["resume_path_final"], 
    #                                 posting_path = st.session_state["job_posting_path"] if "job_posting_path" in st.session_state else "", 
    #                                 template_file=st.session_state["template_path"],
    #                                 )
    #     count+=1
    if "Tailoring" in st.session_state.tabs:
        with tabs[count]:
            display_tailoring()
            thread = threading.Thread(
                target = tailor_resume, 
                args = (
                    st.session_state["resume_dict"], 
                    st.session_state["job_posting_dict"] if "job_posting_dict" in st.session_state else "", 
                ),
                daemon=True,
            )
            thread.start()
        count+=1
    # del st.session_state.resume_path, st.session_state.job_posting_path, st.session_state.job_description

def get_dict(type):
    if type=="evaluation":
        return eval_dict
    elif type=="tailoring":
        return tailor_dict

@st.experimental_fragment(run_every=1)
def display_tailoring():
    try:
        tailor_dict = get_dict("tailoring")
    except Exception:
        tailor_dict={}
    st.write("Generated tailoring tips")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.write("**Skills Section**")
        try:
            original_skills = tailor_dict["original_skills"]
            tailored_skills_dict=tailor_dict["tailored_skills"]
            if original_skills!="":
                st.write("You seem to lack a skills section. If you would like to add one, here are some tailoring suggestions you can reference.")
            irrelevant_skills = tailored_skills_dict["irrelevant_skills"]
            additional_skills = tailored_skills_dict["additional_skills"]
            # ranked_skills = tailored_skills_dict["ranked_skills"]
            relevant_skills = tailored_skills_dict["relevant_skills"]
            st.write("""Some of the skills you have in your resume may distract the HR from reading the skills that truly matter to them. 
                    You may remove them or rank them lower on the list.""")
            st.write(irrelevant_skills)
            st.write("""There are skills that can benefit you if you add them to your resume. However, if you don't have them, don't add them! 
                    Remember, a HR looks for your integrity as much as your talent!""")
            st.write(additional_skills)
            st.write("""These skills are the most relevant to the job position that will make you stand out. Make sure to rank them higher on the list!""")
            st.write(relevant_skills)
        except Exception:
            st.write("Evaluating...")  
    with c2:
        st.write("**Objective Section**")
        try:
            original_objective = tailor_dict["original_objective"]
            tailored_objective_dict=tailor_dict["tailored_objective"]
            if original_objective:
                replacement_list = tailored_objective_dict["replacements"]
                # Convert list of dictionaries to DataFrame
                df = pd.DataFrame(replacement_list)
                # Rename the columns
                df.columns = ['replaced_words', 'substitution']
                st.table(df)

                # c3, c4=st.columns([1, 1])
                # for replacement in replacement_list:
                #     with c3:
                #         replaced_word = replacement["replaced_word"]
                #         st.write(f":red[{replaced_word}]")  
                #     with c4:
                #         replacement = replacement["replacement"]
                #         st.write(f":green[{replacement}]")
                st.write(original_objective)
            else:
                st.write("You don't seem to have a summary/objective section. If you would like to add one, here's a tailored draft for this job. ")
                generated_objective = tailored_objective_dict["generated_objective"]
                st.write(generated_objective)
        except Exception:
            st.write("Evaluating...")  
    st.write("**Experience Section**")
    try:
        tailored_experience = tailor_dict["tailored_experience"]
        st.write(tailored_experience)
    except Exception:
        st.write("Evaluating...")


@st.experimental_fragment(run_every=3)
def display_resume_eval(): 
    """ Displays resume evaluation result"""
    _, c1, c2 = st.columns([1, 2, 2])
    try:
        eval_dict= get_dict("evaluation")
    except Exception:
        eval_dict={}
    with c1:
        with st.container():
            st.title("Length")
            st.write("A resume has an ideal length or 450 to 650 words, about one page long.")
            #TODO: use a gauge chart to display
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
                st.write(f"The ideal type for your resume: \n{ideal_type}")
                my_type = eval_dict["type"]
                st.write(f"Your resume type: \n {my_type}")
            except Exception:
                st.write("Evaluating...")
            # st.help(functional)
    _, c3, c4 = st.columns([1, 2, 2])
    with c3:
        with st.container():
            st.title("Impression")
            st.write("How close does your resume compare to others of the same industry?")
            try:
                comparison = eval_dict["comparison"]
                if comparison:
                    #TODO: draw bullet graph or something 
                    st.write(comparison)
            except Exception:
                st.write("Evaluating...")
            st.write("How well does your resume reflect the career you want?")
            try:
                cohesiveness = eval_dict["cohesiveness"]
                st.write(cohesiveness)
            except Exception:
                st.write("Evaluating...")
    with c4:
        with st.container():
            st.title("In-depth Analysis")
            try:
                evaluated_work = eval_dict["in_depth"]["work experience"]
                st.write(f"Work experience: {evaluated_work}")
            except Exception:
                st.write("Evaluating...")

    back = st.button("Go back to main menu", type="primary", )
    if back:
        st.switch_page("pages/streamlit_interviewbot.py")

# main()