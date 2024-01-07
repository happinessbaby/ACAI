from langchain.utilities import SerpAPIWrapper
from langchain.agents import Tool
from langchain.tools.file_management.write import WriteFileTool
from langchain.tools.file_management.read import ReadFileTool
from langchain.vectorstores import FAISS
from langchain.docstore import InMemoryDocstore
from langchain.embeddings import OpenAIEmbeddings
from langchain_experimental.autonomous_agents import AutoGPT
from langchain.chat_models import ChatOpenAI
from utils.agent_tools import search_user_material, create_search_tools
from utils.langchain_utils import retrieve_faiss_vectorstore, create_compression_retriever
import os

faiss_web_data = os.environ["FAISS_WEB_DATA_PATH"]

class PlannerController():

    def __init__(self, userId):
        self._init_assistant()
        self.userId=userId

    def _init_assistant(self):

        # tools = [search_user_material]
        tools = create_search_tools("google", 5)
        vectorstore = retrieve_faiss_vectorstore(faiss_web_data)
        ai_name = "career planner"
        ai_role = "Plans daily goals and todo lists to Human can achieve their dream career life"
        planner = AutoGPT.from_llm_and_tools(
            ai_name=ai_name,
            ai_role=ai_role,
            memory=vectorstore.as_retriever(),
            tools=tools,
            llm=ChatOpenAI(temperature=0),
        )
        self.planner=planner

    def askAI(self, query):
        try:
            self.planner.run([query])
        except Exception as e:
            raise e