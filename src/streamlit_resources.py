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
from utils.basic_utils import ascrape_playwright
from utils.langchain_utils import create_web_extraction_chain, create_babyagi_chain
from typing import Any, List, Union, Dict
from langchain.agents.agent_toolkits import PlayWrightBrowserToolkit
from langchain.tools.playwright.utils import (
    create_async_playwright_browser,
    create_sync_playwright_browser,  # A synchronous browser is available, though it isn't compatible with jupyter.
)

from utils.common_utils import get_web_resources
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from dotenv import load_dotenv, find_dotenv
import asyncio
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="geoapiExercises")

_ = load_dotenv(find_dotenv()) # read local .env file
placeholder = st.empty()
token_limit = 4000
llm=ChatOpenAI(temperature=0, cache = False)
job_fair_schema = {
        "properties": {
            "event_name": {"type": "string"}, 
            "event_datetime": {"type": "string"},
            "event_location": {"type": "string"},
            "event_url": {"type": "string"},
        },
        "required": ["event_name", "event_datetime", "event_location", "event_url"],
    }

images = []
for file in ["./resources/jobfair.png", "./resources/jobsearch.png"]:
    with open(file, "rb") as image:
        encoded = base64.b64encode(image.read()).decode()
        images.append(f"data:image/png;base64,{encoded}")
clicked = clickable_images(
    images,
    titles=[f"Image #{str(i)}" for i in range(2)],
    div_style={"display": "flex", "justify-content": "center", "flex-wrap": "wrap"},
    img_style={"margin": "5px", "height": "200px"},
)


class Resources():

    def __init__(self):
        
        self.entry_point()
        # self.set_clickable_icons()
        # self._create_resources()

    def entry_point(self):

        if clicked!=-1:
            if clicked==0:
                print("JOB FAIR LOGO CLICKED")
                url = "https://www.eventbrite.com/"
                self.find_job_fairs(url)
            elif clicked==1:
                print("JOB SEARCH LOGO CLICKED")
                url = "https://linkedin.com"
    





            
    def find_job_fairs(self, url):


        print("inside search job fairs")
        # ask user to use their current location or somewhere else
        modal = Modal(title="Allow access to you location?", key="access_popup", max_width=500)
        with modal.container():
            yes = st.button("yes")
            if yes:
                city, state = self.get_location()
                #TODO: Step 1 get a list of sites
                # Step 2: scrape the site
                asyncio.run(self.scrape_with_playwright(
                    url=url,
                    tags=[ "div"],
                    schema=job_fair_schema,
                ))

        # TODO Job fair events



    



    async def scrape_with_playwright(url: str, tags: List[str], schema):


        html_content = await ascrape_playwright(url, tags)

        print(f"Extracting content with LLM: {html_content}")

        html_content_fits_context_window_llm = html_content[:token_limit]

        extracted_content = create_web_extraction_chain(html_content_fits_context_window_llm, schema)

        print(extracted_content)

    # TODO Job fair events
    # ask user to use their current location or somewhere else

    # async_browser = create_async_playwright_browser()
    # toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    # tools = toolkit.get_tools()
    # print(tools)
    # agent_chain = initialize_agent(
    #     tools,
    #     llm,
    #     agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    #     verbose=True,
    # )
    # result = await agent_chain.arun("list all the job affairs in Birmingham, Alabama")
    # print(result)



 

    def get_location(self):

        coord = geocoder.ip('me')
        print(coord.latlng)
        location = geolocator.reverse(coord, exactly_one=True)
        address = location.raw['address']
        city = address.get('city', '')
        state = address.get('state', '')
        country = address.get('country', '')
        print(city, state, country)
        return city, state


if __name__== '__main__':
    # resources = Resources()
    # url= "https://www.eventbrite.com/d/al--birmingham/job-fairs/"

    # asyncio.run(scrape_with_playwright(
    #     url=url,
    #     tags=[ "div"],
    #     schema=job_fair_schema,
    # ))
    # scrape_with_playwright1()
    # get_web_resources("Search JobFairX for job fairs near Birmingham, Alabama. Get the name, datetime, and location.")
    get_web_resources("Get top 10 links to jobs in Birmingham, Alabama.", with_source=True)
    # print(create_babyagi_chain("Search JobFairX and retrieve job fairs near Birmingham, Alabama. Get the name, datetime, and location."))