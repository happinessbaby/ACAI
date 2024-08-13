import streamlit as st
import time
from streamlit_modal import Modal
import os
import extra_streamlit_components as stx
# Note that you can also import these from streamlit directly
from st_pages import get_pages, get_script_run_ctx 
from streamlit_extras.stylable_container import stylable_container
import plotly.express as px
import plotly.graph_objects as go
import streamlit_antd_components as sac
import pandas as pd
import uuid
import streamlit.components.v1 as components
import base64



# pages = get_pages("")
# ctx = get_script_run_ctx()



@st.dialog(" ", )
def loading(text, container=st.empty(), interval=5):  
    with container.container():
        with st.spinner(text):
            time.sleep(interval)

def nav_to(url):
    nav_script = """
        <meta http-equiv="refresh" content="0; url='%s'">
    """ % (url)
    st.write(nav_script, unsafe_allow_html=True)


def set_streamlit_page_config_once():
    try:
        st.set_page_config(layout="wide")
    except st.errors.StreamlitAPIException as e:
        if "can only be called once per app" in e.__str__():
            # ignore this error
            return
        # raise e

            
def user_menu(userId, page, ):
    _, c1 = st.columns([10, 1])
    with c1:
        if not userId:
            if st.button("Log in", key="profile_button", type="primary"):
                st.session_state["user_mode"] = "signedout"
                st.switch_page("pages/user.py")
        else:
            with stylable_container(
                key="menu_popover",
                css_styles="""
                    button {
                        background: none;
                        border: none;
                        color: #2d2e29;
                        padding: 0;
                        cursor: pointer;
                        font-size: 12px; /* Adjust as needed */
                        text-decoration: none;
                    }
                    """,
            ):
                with st.popover(label=f"{userId}",):
                    # if page!="main":
                    #     if st.button("Home", type="primary"):
                    #         st.switch_page("home.py")
                    if page!="profile":
                        if st.button("My profile", type="primary"):
                            st.switch_page("pages/user.py")
                    st.divider()
                    if st.button("Log out", type="primary"):
                        st.session_state["user_mode"]="signout"
                        st.switch_page("pages/user.py")
                # if page=="profile":
                #     if st.button("Delete my profile", type="primary"):
                #         st.session_state["user_mode"] = "delete_profile"
                #         st.switch_page("pages/user.py")


def progress_bar(page):

    step = sac.steps(
        items=[
            sac.StepsItem(title=" ", subtitle="Complete your profile"),
            sac.StepsItem(title=" ", subtitle="Pick a template"), 
            sac.StepsItem(title=" ", subtitle="Download your resume")
        ], index = page,  color="#47ff5a", key="progress_steps", return_index=True,
    )
    if step==0:
        if "current_page" in st.session_state and st.session_state.current_page!="profile":
            # st.session_state["current_page"]="profile"
            st.switch_page("pages/user.py")
    elif step==1:
        if "current_page" in st.session_state and st.session_state.current_page!="template":
            # st.session_state["current_page"] = "template"
            st.switch_page("pages/templates.py")
    elif step==2:
        if "current_page" in st.session_state and st.session_state.current_page!="download":
            st.switch_page("pages/downloads.py")

    
def length_chart(length):
    if length<300:
        text = "too short"
    elif length>=300 and length<450:
        text="good"
    elif length>=450 and length<=600:
        text="great"
    elif length>600 and length<800:
        text="good"
    else:
        text="too long"
    # Cap the displayed value at 1000, bust keep the actual value for the text annotation
    display_value = min(length, 1000)
    # Create a gauge chart
    fig = go.Figure(go.Indicator(
        mode = "gauge",
        value = display_value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Your resume is:"},
        gauge = {
                # 'shape':"bullet",
                'axis': {'range': [1, 1000]},
                'bar': {'color': "white", "thickness":0.1},
                'steps': [
                    {'range': [1, 300], 'color': "red"},
                    {'range': [300, 450], "color":"yellow"},
                    {'range': [450, 600], 'color': "lightgreen"},
                        {'range': [600, 800], "color":"yellow"},
                    {'range': [800, 1000], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 1},
                    'thickness': 0.2,
                    'value': display_value
                }
            }
    ))
    # Add annotation for the text
    fig.add_annotation(
        x=0.5, 
        y=0.5, 
        text=text, 
        showarrow=False,
        font=dict(size=24)
    )
    return fig


def comparison_chart(data):
    # Mapping from similarity categories to numeric values
    similarity_mapping = {
        'no similarity': 0,
        'some similarity': 1,
        'very similar': 2,
            'no data': -1  # Map empty strings to -1,
    }
    size_mapping = {
        'no similarity': 10,
        'some similarity': 20,
        'very similar': 30,
        'no data': 5  # Size for empty strings
    }
    # Extract fields and similarity values
    fields = []
    values = []
    hover_texts = []
    sizes = []
    for item in data:
        for field, similarity in item.items():
            fields.append(field)
            values.append(similarity_mapping[similarity["closeness"] if similarity["closeness"] else 'no data'])
            sizes.append(size_mapping[similarity["closeness"] if similarity["closeness"] else "no data"])
            hover_texts.append(similarity["reason"] if similarity["reason"] else " ")

    # Create scatter plot
    # fig = px.scatter(
    #     x=fields,
    #     y=values,
    #     # color=values,
    #     # color_continuous_scale='Viridis',
    #     mode='markers',
    #     marker=dict(
    #         size=sizes
    #     ),
    #     labels={'x': 'Resume Field', 'y': 'Similarity Level'},
    #     # title='Resume Similarity Scatter Plot',
    #     # hover_data={'x': fields, 'y': [list(similarity_mapping.keys())[list(similarity_mapping.values()).index(val)] for val in values]}
    # )
    # Create scatter plot
    fig = go.Figure(data=go.Scatter(
        x=fields,
        y=values,
        mode='markers',
        marker=dict(
            size=sizes
        ),
        text=hover_texts,  # Add custom hover text
        hoverinfo='text'  # Display only the custom hover text
    ))
    # Add custom hover text
    fig.update_traces(
        hovertext=hover_texts,
        hoverinfo='text'  # Display only the custom hover text
    )
    fig.update_yaxes(
        tickmode='array',
        tickvals=[-1, 0, 1, 2],
        ticktext=['No data', 'No similarity', 'Some similarity', 'Very similar'],
        range=[0, 2]
    )
    return fig



def language_radar(data_list):
    # Sample data
    # Mapping from categories to numeric values
    category_mapping = {"no data": 0, 'bad': 1, 'good': 2, 'great': 3}
    metrics = []
    values = []
    hover_texts=[]
    for item in data_list:
        for metric, details in item.items():
            metrics.append(metric)
            values.append(category_mapping[details['rating'] if details['rating'] else 'no data'])
            hover_texts.append(details["reason"] if details['reason'] else " ")

    # Add the first value at the end to close the radar chart circle
    values.append(values[0])
    metrics.append(metrics[0])
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=metrics,
        fill='toself', 
        hovertext=hover_texts,  # Add custom hover text
        hoverinfo='text'  # Display only the hover text
    ))
    # Define axis labels
    axis_labels = {1: 'Bad', 2: 'Good', 3: 'Great'}
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 3],  # Set the range for the radial axis
                tickvals=list(axis_labels.keys()),  # Specify the ticks
                ticktext=[axis_labels[val] for val in axis_labels.keys()]  # Set the labels
            )
        ),
    )
    return fig

def readability_indicator(self, data):

    # print(data)
    df = pd.DataFrame(list(data.items()), columns=['Metric', 'Score'])
    fig = px.bar(df, x='Metric', y='Score', title="readability stats",
            labels={"Score": "Score Value", "Metric": "Text Metric"})
    return fig


# def automatic_download(self, file_path ):

#         # Read the binary file
#     with open(file_path, 'rb') as file:
#         binary_data = file.read()

#     # Encode the binary data using Base64
#     b64 = base64.b64encode(binary_data)
#     st.markdown()
#     id_link = '_'+str(uuid.uuid4())
#     components.html(
#         f"""<html><body>                                   
#         <a href="data:application/pdf;base64,{b64}" download="cover_letter.docx" id="{id_link}"></a>""" +
#         """<script>                                    
#                 window.onload = function () {                                            
#                     document.getElementById('""" + id_link + """').click();
#                                     };                                        
#                                 </script>
#                             </body></html>                                    
#                             """, height=0, width=0)