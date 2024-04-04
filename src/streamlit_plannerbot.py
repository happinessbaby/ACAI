import streamlit as st
import extra_streamlit_components as stx
from backend.profile_builder import ProfileController
import uuid


class Planner():

    def __init__(self, userId):
        self.userId=userId
        if "sessionId" not in st.session_state:
            st.session_state["sessionId"] = str(uuid.uuid4())
            print(f"Session: {st.session_state.sessionId}")
        self._init_session_states()


    def _init_session_states(self):
        if "planner" not in st.session_state:
            st.session_state.planner = ProfileController(self.userId)


    def _create_user_page(self):
        try:
            self.planner = st.session_state.planner
        except Exception as e:
            raise e
        chosen_id = stx.tab_bar(data=[
                stx.TabBarItemData(id=1, title="ToDo", description="Tasks to take care of"),
                stx.TabBarItemData(id=2, title="Done", description="Tasks taken care of"),
                stx.TabBarItemData(id=3, title="Overdue", description="Tasks missed out"),
            ], default=1)
        st.info(f"{chosen_id=}")
        #TODO ADD USER PERSONALIZED PAGE HERE
        # if chosen_id=="1":
        #     self.create_to_do()

    def create_to_do(self):
        response = self.planner.askAI("User wants to be a software engineer, help user prepare a to do list.")
        print(response)
