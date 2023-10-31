import geocoder
import streamlit as st
from streamlit_chat import message
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_modal import Modal
import json
from st_pages import show_pages_from_config, add_page_title, show_pages, Page
from st_clickable_images import clickable_images
import base64
from langchain.agents import load_tools
from basic_utils import ascrape_playwright
from langchain_utils import create_web_extraction_chain, create_babyagi_chain
from typing import Any, List, Union, Dict
from langchain.agents.agent_toolkits import PlayWrightBrowserToolkit
from langchain.tools.playwright.utils import (
    create_async_playwright_browser,
    create_sync_playwright_browser,  # A synchronous browser is available, though it isn't compatible with jupyter.
)

from common_utils import get_web_resources
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from dotenv import load_dotenv, find_dotenv
import asyncio

_ = load_dotenv(find_dotenv()) # read local .env file
placeholder = st.empty()
token_limit = 4000
llm=ChatOpenAI(temperature=0, cache = False)

class Resources():

    def __init__(self):

        pass
        # self.set_clickable_icons()
        # self._create_resources()

    @st.cache_data(experimental_allow_widgets=True)
    def set_clickable_icons(_self):

        images = []
        for file in ["image1.png", "image2.png"]:
            with open(file, "rb") as image:
                encoded = base64.b64encode(image.read()).decode()
                images.append(f"data:image/png;base64,{encoded}")
        clicked = clickable_images(
            images,
            titles=[f"Image #{str(i)}" for i in range(2)],
            div_style={"display": "flex", "justify-content": "center", "flex-wrap": "wrap"},
            img_style={"margin": "5px", "height": "200px"},
        )
        # if "clicked_job_fair" not in st.session_state:
        #     st.session_state["clicked_job_fair"] = clicked_job_fair
        # clicked_networking = clickable_images(
        #     [images[1]],
        #     titles = "Social Networking",
        #     div_style = {"display": "flex", "justify-content": "center", "flex-wrap": "wrap"},
        #     img_style={"margin": "5px", "height": "200px"},
        # )
        # if "clicked_networking" not in st.session_state:
        #     st.session_state["clicked_networking"] = clicked_networking
        # if st.session_state.clicked_job_fair
        # if clicked:
        #     _self.find_job_fairs()

            
    # async def find_job_fairs(self):

    #     job_fair_schema = {
    #         "properties": {
    #             "datetime": {"type": "string"},
    #             "location": {"type": "string"},
    #         },
    #         "required": ["datetime", "location"],
    #     }
    #     html_content = await ascrape_playwright(url, tags)

    #     print("Extracting content with LLM")

    #     html_content_fits_context_window_llm = html_content[:token_limit]

    #     extracted_content = create_extraction_chain(html_content_fits_context_window_llm, job_fair_schema)


    #     # TODO Job fair events
    #     print("inside search job fairs")
    #     # ask user to use their current location or somewhere else
    #     location = self.get_location()



    



async def scrape_with_playwright(url: str, tags: List[str], schema):


    html_content = await ascrape_playwright(url, tags)

    print(f"Extracting content with LLM: {html_content}")

    html_content_fits_context_window_llm = html_content[:token_limit]

    extracted_content = create_web_extraction_chain(html_content_fits_context_window_llm, schema)

    print(extracted_content)

    # TODO Job fair events
    # ask user to use their current location or somewhere else

    async_browser = create_async_playwright_browser()
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()
    print(tools)
    agent_chain = initialize_agent(
        tools,
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )
    result = await agent_chain.arun("list all the job affairs in Birmingham, Alabama")
    print(result)



 

def get_location():

    g = geocoder.ip('me')
    print(g.latlng)


if __name__== '__main__':
    # resources = Resources()
    # url= "https://www.eventbrite.com/d/al--birmingham/job-fairs/"
    # job_fair_schema = {
    #     "properties": {
    #         "event_name": {"type": "string"}, 
    #         "event_datetime": {"type": "string"},
    #         "event_location": {"type": "string"},
    #         "event_url": {"type": "string"},
    #     },
    #     "required": ["event_name", "event_datetime", "event_location", "event_url"],
    # }

    # asyncio.run(scrape_with_playwright(
    #     url=url,
    #     tags=[ "div"],
    #     schema=job_fair_schema,
    # ))
    # scrape_with_playwright1()
    get_web_resources("Search JobFairX for job fairs near Birmingham, Alabama. Get the name, datetime, and location.")
    # get_web_resources("Retrieve job related events such as digital talks on LinkedIn in the next five days.", with_source=True)
    # print(create_babyagi_chain("Search JobFairX and retrieve job fairs near Birmingham, Alabama. Get the name, datetime, and location."))