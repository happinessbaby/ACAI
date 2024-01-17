from langchain.agents import load_tools, initialize_agent, Tool, AgentExecutor
from langchain.vectorstores import DocArrayInMemorySearch
from langchain.agents import AgentType
from utils.basic_utils import read_txt, convert_to_txt, process_json
from utils.langchain_utils import ( create_compression_retriever, handle_tool_error,
                              split_doc, retrieve_vectorstore, split_doc_file_size, reorder_docs, create_summary_chain)
from langchain.llms import OpenAI
from langchain.vectorstores import FAISS
from langchain.tools import tool
from langchain.output_parsers import PydanticOutputParser
from langchain.tools.file_management.move import MoveFileTool
from pydantic import BaseModel, Field, validator
from langchain.chains import LLMMathChain
from langchain.chains import (create_extraction_chain,
                              create_extraction_chain_pydantic)
import os
import openai
from dotenv import load_dotenv, find_dotenv
import json
import random, string
from json import JSONDecodeError
import base64
from langchain.agents.react.base import DocstoreExplorer
from langchain.document_loaders import TextLoader, DirectoryLoader
from langchain.docstore.wikipedia import Wikipedia
from langchain.utilities.serpapi import SerpAPIWrapper
from langchain.utilities.google_search import GoogleSearchAPIWrapper
from langchain.chains import RetrievalQA,  LLMChain
# from langchain.agents.agent_toolkits import create_retriever_tool
# from langchain.agents.agent_toolkits import (
#     create_vectorstore_agent,
#     VectorStoreToolkit,
#     create_vectorstore_router_agent,
#     VectorStoreRouterToolkit,
#     VectorStoreInfo,
# )
from utils.langchain_utils import create_ensemble_retriever
from typing import List, Union, Any, Optional, Dict
from langchain.tools.base import ToolException

_ = load_dotenv(find_dotenv()) # read local .env file
openai.api_key = os.environ["OPENAI_API_KEY"]
STORAGE = os.environ['STORAGE']

def create_wiki_tools() -> List[Tool]:

    """ Creates wikipedia tool used to lookup and search in wikipedia """
    
    docstore = DocstoreExplorer(Wikipedia())
    tools = [
        Tool(
            name = "Wikipedia_Search",
            func = docstore.search,
            description= "Search for a term in the docstore.",
            handle_tool_error=handle_tool_error,
        ),
        Tool(
            name = "Wikipedia_Lookup",
            func = docstore.lookup,
            description = "Lookup a term in the docstore.",
            handle_tool_error=handle_tool_error,
        ),
    ]
    return tools

def create_math_tools(llm=OpenAI()):

    llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)

    tools = [
    Tool(
        name="Calculator",
        func=llm_math_chain.run,
        description="useful for when you need to answer questions that needs simple math"
    ),
    ]
    return tools


def create_qa_tools(qa_chain):
    tools = [
        Tool(
            name="QA Document",
            # func = qa_chain.run,
            func = qa_chain.__call__,
            coroutine=qa_chain.acall, #if you want to use async
            description="Useful for answering general questions",
            # return_direct=True,
        ),
    ]
    return tools



def create_search_tools(name: str, top_n: int) -> List[Tool]:

    """
    Creates google search tool

    Args: 

        name (str): type of google search, "google" or "serp"

        top_n (int): how many top results to search

    Returns: List[Tool]

    """

    if (name=="google"):
        search = GoogleSearchAPIWrapper(k=top_n)
        tool = [
            Tool(
            name = "web_search", 
            description= "useful for when you need to ask with search",
            func=search.run,
            handle_tool_error = handle_tool_error,
        ),
        ]
    elif (name=="serp"):
        search = SerpAPIWrapper() 
        tool = [
            Tool(
            name="web_search",
            description= "useful for when you need to ask with search",
            func=search.run,
            handle_tool_error=handle_tool_error,
        ),
        ]
    return tool

class DocumentInput(BaseModel):
    question: str = Field()

def create_retriever_tools(retriever: Any, name: str, description: str, llm=OpenAI(), chain_type="stuff") -> List[Tool]:

    """
    Creates retriever tools from all types of retriever. 

    See: https://python.langchain.com/docs/use_cases/question_answering/how_to/vector_db_qa

    Args: 

        retriever (any): any vectorstore retriever

        name (str): tool name

        description (str): tool description

    Key Args:

        llm: OpenAI() by default

        chain_type: "stuff" by default

    Returns:
        
        a list of agent tools

    """
    tool = [
        Tool(
        args_schema=DocumentInput,
        name=name,
        description=description,
        func=RetrievalQA.from_chain_type(llm=llm, retriever=retriever, chain_type=chain_type),
        handle_tool_error=True,
    ),
    ]
    print(f"Succesfully created database tool: {name}")
    return tool


def create_vs_retriever_tools(vectorstore: Any, tool_name: str, tool_description: str) -> List[Tool]:   

    """Create retriever tools from vector store for conversational retrieval agent
    
    See: https://python.langchain.com/docs/use_cases/question_answering/how_to/conversational_retrieval_agents
    
    Args:

        vectorstore (Any): vector store to be used as retriever

        tool_name: name of the tool

        tool_description: description of the tool's usage

    Returns:

        List[Tool]

    """   

    retriever = vectorstore.as_retriever()
    tool = [create_retriever_tool(
        retriever,
        tool_name,
        tool_description
        )]
    print(f"Succesfully created retriever tool: {tool_name}")

    return tool

# def create_vectorstore_agent_toolkit(embeddings, index_name, vs_name, vs_description, llm=OpenAI()):

#     """ See: https://python.langchain.com/docs/integrations/toolkits/vectorstore"""

#     store = retrieve_faiss_vectorstore(embeddings,index_name)
#     vectorstore_info = VectorStoreInfo(
#         name=vs_name,
#         description=vs_description,
#         vectorstore=store,
#         )
#     router_toolkit = VectorStoreRouterToolkit(
#     vectorstores=[vectorstore_info,], llm=llm
#         )  
#     return router_toolkit

def create_sample_tools(related_samples: List[str], sample_type: str,) -> Union[List[Tool], List[str]]:

    """ Creates a set of tools from files along with the tool names for querying multiple documents. 
        
        Note: Document comparison benefits from specifying tool names in prompt. 
     
      The files are split into Langchain Document, which are turned into ensemble retrievers then made into retriever tools. 

      Args:

        related_samples (list[str]): list of sample file paths

        sample_type (str): "resume" or "cover letter"
    
    Returns:

        a list of agent tools and a list of tool names
          
    """

    tools = []
    tool_names = []
    for file in related_samples:
        docs = split_doc_file_size(file, splitter_type="tiktoken")
        tool_description = f"This is a {sample_type} sample. Use it to compare with other {sample_type} samples"
        ensemble_retriever = create_ensemble_retriever(docs)
        tool_name = f"{sample_type}_{random.choice(string.ascii_letters)}"
        tool = create_retriever_tools(ensemble_retriever, tool_name, tool_description)
        tool_names.append(tool_name)
        tools.extend(tool)
    print(f"Successfully created {sample_type} tools")
    return tools, tool_names



@tool()
def search_user_material(json_request: str) -> str:

    """Searches and looks up user uploaded material, if available.

      Input should be a single string strictly in the following JSON format: '{{"user_material_path":"<user_material_path>", "user_query":"<user_query>" \n"""

    try:
        args = json.loads(process_json(json_request))
    except JSONDecodeError as e:
        print(f"JSON DECODE ERROR: {e}")
        return "Format in a single string JSON and try again."
 
    vs_path = args["user_material_path"]
    query = args["user_query"]
    try:
        if STORAGE=="LOCAL":
            vs_type="faiss"
            vs = retrieve_vectorstore("faiss", vs_path)
        elif STORAGE=="CLOUD":
            vs_type="open_search"
            vs = retrieve_vectorstore("open_search", vs_path)
        # subquery_relevancy = "how to determine what's relevant in resume"
        # option 1: compression retriever
        retriever = create_compression_retriever(vs_type=vs_type, vectorstore=vs)
        # option 2: ensemble retriever
        # retriever = create_ensemble_retriever(split_doc())
        # option 3: vector store retriever
        # db = retrieve_faiss_vectorstore(vs_path)
        # retriever = db.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": .5, "k":1})
        docs = retriever.get_relevant_documents(query)
        # reordered_docs = reorder_docs(retriever.get_relevant_documents(subquery_relevancy))
        texts = [doc.page_content for doc in docs]
        texts_merged = "\n\n".join(texts)
        return texts_merged
    except Exception:
        return "Stop using the search_user_material tool. There is no user material or query to look up. Use another tool."



@tool(return_direct=True)
def file_loader(json_request: str) -> str:

    """Outputs a file. Use this whenever you need to load a file. 
    DO NOT USE THIS TOOL UNLESS YOU ARE TOLD TO DO SO.
    Input should be a single string in the following JSON format: '{{"file": "<file>"}}' \n """

    try:
        args = json.loads(process_json(json_request))
        file = args["file"]
        file_content = read_txt(file)
        if os.path.getsize(file)<2000:    
            print(file_content)   
            return file_content
        else:
            prompt_template = "summarize the follwing text. text: {text} \n in less than 100 words."
            return create_summary_chain(file, prompt_template=prompt_template)
    except Exception as e:
        return "file did not load successfully. try another tool"
    


@tool("help and instruction")
def provide_help_and_instruction(query:str) -> str:

    """ Useful when user asks you to help them navigate the site, such as where to upload and download their files, and also provide them with what you can do as an AI career advisor."""

    #TODO: help user navigate the site.



# https://python.langchain.com/docs/modules/agents/agent_types/self_ask_with_search
@tool("search chat history")
def search_all_chat_history(query:str)-> str:

    """ Used when there's miscommunication in the current conversation and agent needs to reference chat history for a solution. """

    try:
        if STORAGE=="LOCAL":
            db = retrieve_vectorstore("faiss", "chat_debug")
        retriever=db.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": .5, "k":1})
        # docs = retriever.get_relevant_documents(query)
        # texts = [doc.page_content for doc in docs]
        # #TODO: locate solution 
        # return "\n\n".join(texts)
        tools = create_retriever_tools(retriever, "Intermediate Answer", "useful for when you need to ask with search")
        llm = OpenAI(temperature=0)
        self_ask_with_search = initialize_agent(
            tools, llm, agent=AgentType.SELF_ASK_WITH_SEARCH, verbose=True
        )
        response = self_ask_with_search.run(query)
        return response
    except Exception:
        return ""

#TODO: conceptually, search chat history is self-search, debug error is manual error handling 
@tool
def debug_error(self, error_message: str) -> str:

    """Useful when you need to debug the cuurent conversation. Use it when you encounter error messages. Input should be in the following format: {error_messages} """

    return "shorten your prompt"






