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
from utils.langchain_utils import retrieve_vectorstore, create_compression_retriever
from langchain.indexes import VectorstoreIndexCreator
from langchain.indexes.vectorstore import VectorStoreIndexWrapper
import os

faiss_web_data = os.environ["FAISS_WEB_DATA_PATH"]


#### THIS SHOULD BE CONNECTED TO BE THE USER_PROFILE_BUILDER

class ProfileController():

    def __init__(self, userId):
        self._init_assistant()
        self.userId=userId

    # def _init_assistant(self):

    #     # tools = [search_user_material]
    #     tools = create_search_tools("google", 5)
    #     vectorstore = retrieve_vectorstore("faiss", faiss_web_data)
    #     ai_name = "career planner"
    #     ai_role = "Plans daily goals and todo lists to Human can achieve their dream career life"
    #     planner = AutoGPT.from_llm_and_tools(
    #         ai_name=ai_name,
    #         ai_role=ai_role,
    #         memory=vectorstore.as_retriever(),
    #         tools=tools,
    #         llm=ChatOpenAI(temperature=0),
    #     )
    #     self.planner=planner

    def askAI(self, query):
        try:
            self.planner.run([query])
        except Exception as e:
            raise e
        

        #  Reference solution: https://aws.amazon.com/blogs/machine-learning/personalize-your-generative-ai-applications-with-amazon-sagemaker-feature-store/
# The user profiling engine builds a profile for each user, capturing their preferences and interests. 
# This profile can be represented as a vector with elements mapping to features like movie genres, with values indicating the user’s level of interest. 
# The user profiles in the feature store allow the system to suggest personalized recommendations matching their interests. 
# User profiling is a well-studied domain within recommendation systems. To simplify, you can build a regression algorithm using a user’s previous ratings across different categories to infer their overall preferences. This can be done with algorithms like XGBoost.

    def build_user_profile():
        return None

    def build_feature_store():
        return None
        
    ### TO be used with feature store updates of job application status
    
    autoGPT_sample1 = """ For every job applied, search for a similar job to apply. 
    For every job applied with no hearing back, list some areas of improvement with application."""
