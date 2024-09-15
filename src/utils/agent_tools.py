from langchain.agents import initialize_agent
from langchain.agents import AgentType
from utils.basic_utils import process_json
from utils.langchain_utils import ( create_compression_retriever, handle_tool_error,
                              split_doc, retrieve_vectorstore, split_doc_file_size, reorder_docs, create_summary_chain)
from langchain_openai import ChatOpenAI, OpenAI, OpenAIEmbeddings
from pydantic import BaseModel, Field, validator
import os
import openai
from dotenv import load_dotenv, find_dotenv
import json
import random, string
from json import JSONDecodeError
from langchain.agents.react.base import DocstoreExplorer
from langchain_community.document_loaders import TextLoader, DirectoryLoader, S3DirectoryLoader
from langchain.chains import RetrievalQA,  LLMChain, QAGenerationChain, LLMMathChain
from utils.langchain_utils import create_ensemble_retriever
from typing import List, Union, Any, Optional, Dict, Type
from langchain.tools.retriever import create_retriever_tool
# from langchain_experimental.smart_llm import SmartLLMChain
import boto3
import re
from langchain_community.docstore import Wikipedia
# from langchain_community.tools import MoveFileTool
from langchain_community.utilities import GoogleSearchAPIWrapper, SerpAPIWrapper
# from langchain_community.vectorstores import DocArrayInMemorySearch, FAISS
from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
# from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.tools import BaseTool, Tool, tool


_ = load_dotenv(find_dotenv()) # read local .env file
openai.api_key = os.environ["OPENAI_API_KEY"]
STORAGE = os.environ['STORAGE']
if STORAGE=="S3":
    bucket_name = os.environ["BUCKET_NAME"]
    s3_save_path = os.environ["S3_CHAT_PATH"]
    session = boto3.Session(         
                    aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"],
                    aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"],
                )
    s3 = session.client('s3')
else:
    bucket_name=None
    s3=None
aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"]
aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"]

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


def create_vs_retriever_tools(retriever: Any, tool_name: str, tool_description: str) -> List[Tool]:   

    """Create retriever tools from vector store.
    
    Example: https://python.langchain.com/docs/use_cases/question_answering/how_to/conversational_retrieval_agents
    
    Args:

        retriever (Any): any type of retriever including vector store as retriever

        tool_name: name of the tool

        tool_description: description of the tool's usage

    Returns:

        List[Tool]

    """   

    tool = [create_retriever_tool(
        retriever,
        tool_name,
        tool_description
        )]
    print(f"Succesfully created retriever tool: {tool_name}")

    return tool


def create_sample_tools(related_samples: List[str], sample_type: str, llm=ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613")) -> Union[List[Tool], List[str]]:

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
        docs = split_doc_file_size(file, use_bytes_threshold=False, splitter_type="tiktoken", chunk_size=100)
        tool_description = f"This is a {sample_type} sample. Use it to compare with candidate {sample_type}"
        tool_name = f"{sample_type}_{random.choice(string.ascii_letters)}"
        ensemble_retriever = create_ensemble_retriever(docs)
        compression_retriever= create_compression_retriever(ensemble_retriever, )
        tool_names.append(tool_name)
        tool = create_vs_retriever_tools(compression_retriever, tool_name, tool_description)
        tools.extend(tool)
    print(f"Successfully created {sample_type} tools")
    return tools, tool_names


# VECTOR STORE ADVANCED RETRIEVER AS CUSTOM TOOL
@tool()
def search_user_material(json_request: str) -> str:

    """Searches and looks up user uploaded material.

    Use this tool more than other tools when user question is relevant in user_material_topics.

    Input should be a single string strictly in the following JSON format: '{{"user_material_path":"<user_material_path>", "user_query":"<user_query>"}}' """

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
        elif STORAGE=="CLOUD":
            vs_type="elasticsearch"
        vs = retrieve_vectorstore(vs_type=vs_type, index_name=vs_path)
        # subquery_relevancy = "how to determine what's relevant in resume"
        # option 1: compression retriever
        retriever = create_compression_retriever(vs.as_retriever())
        # option 2: ensemble retriever
        # retriever = create_ensemble_retriever(split_doc())
        # option 3: vector store retriever
        # db = retrieve_faiss_vectorstore(vs_path)
        # retriever = db.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": .5, "k":1})
        docs = retriever.get_relevant_documents(query)
        # reordered_docs = reorder_docs(retriever.get_relevant_documents(subquery_relevancy))
        texts = [doc.page_content for doc in docs]
        texts_merged = "\n\n".join(texts)
        print(f"SEARCH USER MATERIAL TOOL RESPONSE: {texts_merged}")
        return texts_merged
    except Exception as e:
        raise e
        return "Stop using the search_user_material tool. There is no user material or query to look up. Use another tool."
    
#In-Memory ADVANCED RETRIEVER AS CUSTOM TOOL
class GenerateQA(BaseModel):
    json_request: str = Field(description="""Input should be a single string strictly in the following JSON format:'{{"interview_material_path":"<interview_material_path>"}}'""")
# @tool(args_schema=GenerateQA, return_direct=False)
# def generate_interview_QA(json_request: str,) -> str:

#     """Generates interview questions and answers base on the user material provided in a directory path. 

#     Use this tool more than any other tools to generate interview questions. """

#     try:
#         args = json.loads(process_json(json_request))
#     except JSONDecodeError as e:
#         print(f"JSON DECODE ERROR: {e}")
#         return "Format in a single string JSON and try again."
 
#     file_path = args["user_material_path"]
#     file_path=re.sub(r"[\n\t\s]*", "", file_path)
#     try:
#         if STORAGE=="LOCAL":
#             loader = DirectoryLoader(file_path)
#         if STORAGE=="CLOUD":
#             loader = S3DirectoryLoader(bucket_name, file_path, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
#         llm = ChatOpenAI(temperature=0.9)
#         chain = QAGenerationChain.from_llm(llm)
#         docs = loader.load()[0]
#         response = chain.run(docs.page_content)
#         print(response[0])
#         return response[0]
#     except Exception as e:
#         raise e
    
#In-Memory ADVANCED RETRIEVER AS CUSTOM TOOL
#SAME AS ABOVE BUT WRITTEN DIFFERENTLY
class generateQATool(BaseTool):
    name: str="generate_interview_QA"
    description: str =  """Generates interview questions and answers base on the user material provided in a directory path. 
    Use this tool more than any other tools to generate interview questions. """
    args_schema: Type[BaseModel] = GenerateQA
    return_direct: bool=False

    def _run(self, json_request:str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            args = json.loads(process_json(json_request))
        except JSONDecodeError as e:
            print(f"JSON DECODE ERROR: {e}")
            return "Format in a single string JSON and try again."
    
        file_path = args["interview_material_path"]
        file_path=re.sub(r"[\n\t\s]*", "", file_path)
        try:
            if STORAGE=="LOCAL":
                loader = DirectoryLoader(file_path)
            if STORAGE=="CLOUD":
                loader = S3DirectoryLoader(bucket_name, file_path, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
            llm = ChatOpenAI(temperature=0.9)
            chain = QAGenerationChain.from_llm(llm)
            docs = loader.load()[0]
            response = chain.run(docs.page_content)
            print(response[0])
            return response[0]
        except Exception as e:
            raise e
        
    def _arun(self, json_request:str, ):
        raise NotImplementedError("This tool does not support async")
    

# class ResumeTemplateDesign(BaseModel):
#     json_request: str = Field(description="""Input should be a single string strictly in the following JSON format:'{{"resume_file":"<resume_file>"}}'""")
# @tool(args_schema=ResumeTemplateDesign, return_direct=False)
# def design_resume_template(json_request:str):

#     """Creates a resume_template for rewriting of resume. Use this tool more than any other tool when user asks to reformat, redesign, or rewrite their resume according to a particular type or template.
#     Do not use this tool to evaluate or customize and tailor resume content. Do not use this tool if resume_template_file is provided in the prompt. 
#     When there is resume_template_file in the prompt, use the "resume_writer" tool instead. """
#     from backend.upgrade_resume import research_resume_type
#     try:
#         args = json.loads(process_json(json_request))
#     except JSONDecodeError as e:
#       print(f"JSON DECODER ERROR: {e}")
#       return "Reformat in JSON and try again."
#     # if resume doesn't exist, ask for resume
#     if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
#       return "Please provide your resume file and try again. "
#     else:
#         resume_file = args["resume_file"]
#     resume_type= research_resume_type(resume_file)
#     return resume_type


# @tool(return_direct=True)
# def resume_template_design_tool(resume_file: str) -> str:

#     """
#     Creates a resume_template for rewriting of resume. Use this tool more than any other tool when user asks to reformat, redesign, or rewrite their resume according to a particular type or template.
#     Do not use this tool to evaluate or customize and tailor resume content. Do not use this tool if resume_template_file is provided in the prompt. 
#     When there is resume_template_file in the prompt, use the "resume_writer" tool instead. 
#     """
#     from backend.upgrade_resume import research_resume_type
#     resume_type= research_resume_type(resume_file)
#     return resume_type

@tool(return_direct=True)
def file_loader(json_request: str) -> str:

    """Outputs the summary of file. Use this whenever you need to load a file. 
    DO NOT USE THIS TOOL UNLESS YOU ARE TOLD TO DO SO.
    Input should be a single string in the following JSON format: '{{"file": "<file>"}}' \n """

    try:
        args = json.loads(process_json(json_request))
        file = args["file"]
        prompt_template = "summarize the follwing text. text: {text} \n in less than 100 words."
        return create_summary_chain(file, prompt_template=prompt_template, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    except Exception as e:
        return "file did not load successfully. try another tool"
    


@tool("help and instruction")
def provide_help_and_instruction(query:str) -> str:

    """ Useful when user asks you to help them navigate the site, such as where to upload and download their files, and also provide them with what you can do as an AI career advisor."""

    #TODO: help user navigate the site.



# https://python.langchain.com/docs/modules/agents/agent_types/self_ask_with_search
#TODO: can use a vector store + document retriever so current conversation and past conversation are combined
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






