import openai
from langchain.agents.react.base import DocstoreExplorer
from langchain.document_loaders import TextLoader, DirectoryLoader, S3FileLoader, S3DirectoryLoader
from langchain.docstore.wikipedia import Wikipedia
# from langchain.indexes import VectorstoreIndexCreator
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.tools.python.tool import PythonREPLTool
from langchain.utilities.serpapi import SerpAPIWrapper
from langchain.utilities.google_search import GoogleSearchAPIWrapper
# from langchain import ElasticVectorSearch
# from langchain.vectorstores.elastic_vector_search import ElasticKnnSearch
# from langchain.embeddings import ElasticsearchEmbeddings
# from elasticsearch import Elasticsearch
from ssl import create_default_context
from langchain.prompts import BaseChatPromptTemplate
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser, initialize_agent, Tool
from langchain.schema import AgentAction, AgentFinish, HumanMessage
from langchain.chains import LLMChain
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA, RetrievalQAWithSourcesChain, TransformChain
from langchain.memory import ConversationBufferMemory
from langchain.chains.qa_with_sources import load_qa_with_sources_chain, stuff_prompt
import os
from langchain.text_splitter import CharacterTextSplitter,  RecursiveCharacterTextSplitter
from langchain.chains.mapreduce import MapReduceChain
from langchain.chains import RetrievalQAWithSourcesChain, StuffDocumentsChain
from langchain.chains import ReduceDocumentsChain, MapReduceDocumentsChain
from langchain.vectorstores.redis import Redis
from langchain.embeddings import OpenAIEmbeddings
import redis
import langchain
from langchain.cache import RedisCache
from langchain.cache import RedisSemanticCache
import json
from typing import List, Union, Any, Optional, Dict
import re
import docx
from langchain.tools import tool
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.agents.agent_types import AgentType
from langchain.agents.agent_toolkits import create_python_agent
from langchain.vectorstores import FAISS,  DocArrayInMemorySearch
from pydantic import BaseModel, Field
from langchain.agents.agent_toolkits import (
    create_vectorstore_agent,
    VectorStoreToolkit,
    create_vectorstore_router_agent,
    VectorStoreRouterToolkit,
    VectorStoreInfo,
)
from langchain.document_transformers import EmbeddingsRedundantFilter
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.text_splitter import CharacterTextSplitter
from langchain.retrievers.document_compressors import EmbeddingsFilter
from langchain.retrievers import ContextualCompressionRetriever
from langchain.docstore.document import Document
from utils.basic_utils import read_txt, timing, timeout
from json import JSONDecodeError
from langchain.document_transformers import LongContextReorder
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.chains import LLMMathChain
from langchain.chains import (create_extraction_chain,
                              create_extraction_chain_pydantic)
from langchain_experimental.autonomous_agents import BabyAGI
import faiss
from langchain.vectorstores import FAISS
from langchain.docstore import InMemoryDocstore
from langchain.chains import create_tagging_chain, create_tagging_chain_pydantic
from langchain.schema import LLMResult, HumanMessage
from langchain.callbacks.base import AsyncCallbackHandler, BaseCallbackHandler
from langchain.schema.messages import BaseMessage
from langchain.tools.base import ToolException
import asyncio
import errno



from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
# You may need to update the path depending on where you stored it
openai.api_key = os.environ["OPENAI_API_KEY"]
aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"]
aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"]
redis_password=os.getenv('REDIS_PASSWORD')
redis_url = f"redis://:{redis_password}@localhost:6379"
redis_client = redis.Redis.from_url(redis_url)



def split_doc(path='./web_data/', path_type='dir', storage = "LOCAL", bucket_name=None, splitter_type = "recursive", chunk_size=200, chunk_overlap=10) -> List[Document]:

    """Splits file or files in directory into different sized chunks with different text splitters.
    
    For the purpose of splitting text and text splitter types, reference: https://python.langchain.com/docs/modules/data_connection/document_transformers/
    
    Keyword Args:

        path (str): file or directory path

        path_type (str): "file" or "dir"

        splitter_type (str): "recursive" or "tiktoken"

        chunk_size (int): smaller chunks in retrieval tend to alleviate going over token limit

        chunk_overlap (int): how many characters or tokens overlaps with the previous chunk

    Returns:

        List[Documents]
    
    """
    if storage=="LOCAL":
        if (path_type=="file"):
            loader = TextLoader(path)
        elif (path_type=="dir"):
            loader = DirectoryLoader(path, glob="*.txt", recursive=True)
    elif storage=="S3":
        if (path_type=="file"):
            loader = S3FileLoader(bucket_name, path, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        elif (path_type=="dir"):
            loader = S3DirectoryLoader(bucket_name, path, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    documents = loader.load()
    # Option 1: tiktoken from openai
    if (splitter_type=="tiktoken"):
        text_splitter = CharacterTextSplitter.from_tiktoken_encoder(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    # option 2: 
    elif (splitter_type=="recursive"):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            length_function = len,
            chunk_overlap=chunk_overlap,
            separators=[" ", ",", "\n"])
    docs = text_splitter.split_documents(documents)
    return docs

def split_doc_file_size(path: str, storage="LOCAL", bucket_name=None, s3=None,  splitter_type = "tiktoken", chunk_size=2000) -> List[Document]:
    
    if storage=="LOCAL":
        bytes = os.path.getsize(path)
    elif storage=="S3":
        response = s3.head_object(Bucket=bucket_name, Key=path)
        bytes = response['ContentLength']
    docs: List[Document] = []
    # if file is small, don't split
    # 1 byte ~= 1 character, and 1 token ~= 4 characters, so 1 byte ~= 0.25 tokens. Max length is about 4000 tokens for gpt3.5, so if file is less than 15000 bytes, don't need to split. 
    if bytes<15000:
        docs.extend([Document(
            page_content = read_txt(path, storage=storage, bucket_name=bucket_name, s3=s3)
        )])
    else:
        docs.extend(split_doc(path, "file", storage=storage, bucket_name=bucket_name, chunk_size=chunk_size, splitter_type=splitter_type))
    return docs


# def get_index(path = ".", path_type="file"):

#     if (path_type=="file"):
#         loader = TextLoader(path, encoding='utf8')
#     elif (path_type=="dir"):
#         loader = DirectoryLoader(path, glob="*.txt")
#     # loader = TextLoader(file, encoding='utf8')
#     index = VectorstoreIndexCreator(
#         vectorstore_cls=DocArrayInMemorySearch
#     ).from_loaders([loader])
#     return index

    
def reorder_docs(docs: List[Document]) -> List[Document]:

    """ Reorders documents so that most relevant documents are at the beginning and the end, as in long context, the middle text tend to be ignored.

     See: https://python.langchain.com/docs/modules/data_connection/document_transformers/post_retrieval/long_context_reorder

     Args: 

        docs (List[Document]): a list of Langchain Documents

    Returns:

        a list of reordered Langchain Documents

    """
    reordering = LongContextReorder()
    reordered_docs = reordering.transform_documents(docs)
    return reordered_docs



def create_ensemble_retriever(docs: List[Document]) -> Any:

    """See purpose and usage: https://python.langchain.com/docs/modules/data_connection/retrievers/ensemble"""

    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = 2
    faiss_retriever = FAISS.from_documents(docs, OpenAIEmbeddings()).as_retriever(search_kwargs={"k": 2})
    ensemble_retriever = EnsembleRetriever(retrievers=[bm25_retriever, faiss_retriever], weights=[0.5, 0.5])
    return ensemble_retriever



def create_QASource_chain(chat, vectorstore, docs=None, chain_type="stuff", index_name="redis_web_advice"):

    qa_chain= load_qa_with_sources_chain(chat, chain_type=chain_type, prompt = stuff_prompt.PROMPT, document_prompt= stuff_prompt.EXAMPLE_PROMPT) 
    qa = RetrievalQAWithSourcesChain(combine_documents_chain=qa_chain, retriever=vectorstore.as_retriever(),
                                     reduce_k_below_max_tokens=True, max_tokens_limit=3375,
                                     return_source_documents=True)
    return qa


def create_compression_retriever(vectorstore: str) -> ContextualCompressionRetriever:

    """ Creates a compression retriever given a vector store path. 
    
    TO see its purpose: https://python.langchain.com/docs/modules/data_connection/retrievers/contextual_compression/

    Keyword Args:

        vectorstore: default is "index_web_advice", files contained in "web_data" directory

    """

    embeddings = OpenAIEmbeddings()
    splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=0, separator=". ")
    redundant_filter = EmbeddingsRedundantFilter(embeddings=embeddings)
    relevant_filter = EmbeddingsFilter(embeddings=embeddings, similarity_threshold=0.76)
    pipeline_compressor = DocumentCompressorPipeline(
        transformers=[splitter, redundant_filter, relevant_filter]
    )
    store = retrieve_faiss_vectorstore(vectorstore)
    retriever = store.as_retriever(search_type="mmr",  search_kwargs={"k":1})
    # retriever = store.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": .5, "k":3})

    compression_retriever = ContextualCompressionRetriever(base_compressor=pipeline_compressor, base_retriever=retriever)

    return compression_retriever



# def create_elastic_knn():
#     # Define the model ID
#     model_id = "mymodel"
#   # Create Elasticsearch connection
#     context = create_default_context(cafile="/home/tebblespc/Downloads/certs.pem")
#     es_connection = Elasticsearch(
#     hosts=["https://127.0.0.1:9200"], basic_auth=("elastic", "changeme"), ssl_context = context)   

#  # Instantiate ElasticsearchEmbeddings using es_connection
#     embeddings = ElasticsearchEmbeddings.from_es_connection(
#         model_id,
#         es_connection,
#     )

#     query = "Hello"
#     knn_result = knn_search.knn_search(query=query, model_id="mymodel", k=2)
#     print(f"kNN search results for query '{query}': {knn_result}")
#     print(
#         f"The 'text' field value from the top hit is: '{knn_result['hits']['hits'][0]['_source']['text']}'"
#     )

#     # Initialize ElasticKnnSearch
#     knn_search = ElasticKnnSearch(
#         es_connection=es_connection, index_name="elastic-index", embedding=embeddings
#     )
    
#     return knn_search

def create_summary_chain(path: str, prompt_template: str, chain_type = "stuff", chunk_size=2000,  llm=OpenAI()) -> str:

    """ See summarization chain: https://python.langchain.com/docs/use_cases/summarization
    
    Args:

        file (str): file path

        prompt_template (str): prompt with input variable "text"

    Keyword Args:

        chain_type (str): default is "stuff

        llm (BaseModel): default is OpenAI()

    Returns:
    
        a summary of the give file
    
    """
    docs = split_doc_file_size(path, chunk_size=chunk_size)
    PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])
    chain = load_summarize_chain(llm, chain_type="stuff", prompt=PROMPT)
    response = chain.run(docs)
    print(f"Sucessfully got summary: {response}")
    return response

def create_refine_chain(files: List[str], prompt_template:str, refine_template:str, llm=ChatOpenAI()) -> str:

    """ Creates a refine chain for multiple documents summarization: https://python.langchain.com/docs/use_cases/summarization#option-3-refine

        Args: 

            files (List[str]): a list of file paths 

            prompt_template (str): main prompt

            refine_template (str): refine prompt at each intermediate step
        
        Keyword Args:

            llm (Basemodel): default is ChatOpenAI()

        Returns:

            a sequential summary on the provided set of documents

    """
    docs: List[Document]=[]
    for file in files: 
        docs.extend(split_doc_file_size(file))
    prompt = PromptTemplate.from_template(prompt_template)
    refine_prompt = PromptTemplate.from_template(refine_template)
    chain = load_summarize_chain(
        llm=llm,
        chain_type="refine",
        question_prompt=prompt,
        refine_prompt=refine_prompt,
        return_intermediate_steps=True,
        input_key="input_documents",
        output_key="output_text",
    )
    result = chain({"input_documents": docs}, return_only_outputs=True)
    return result["output_text"]


def create_mapreduce_chain(files: List[str], map_template:str, reduce_template:str, llm = ChatOpenAI()) -> str:

    """ Creates a map-reduce chain for multiple documents summarization and generalization: https://python.langchain.com/docs/use_cases/summarization#option-2-map-reduce 
    
        Args: 

            files (List[str]): a list of file paths 

            map_template (str): mapping stage prompt

            reduce_template (str): reducing stage prompt

        
        Keyword Args:

            llm (Basemodel): default is OpenAI()

        Returns:

            a summary on the provided set of documents
        
        """

    docs: List[Document]=[]
    for file in files: 
        docs.extend(split_doc_file_size(file))
    # Map
    map_prompt = PromptTemplate.from_template(map_template)
    map_chain = LLMChain(llm=llm, prompt=map_prompt)
    # Reduce
    reduce_prompt = PromptTemplate.from_template(reduce_template)
     # Run chain
    reduce_chain = LLMChain(llm=llm, prompt=reduce_prompt)

    # Takes a list of documents, combines them into a single string, and passes this to an LLMChain
    combine_documents_chain = StuffDocumentsChain(
        llm_chain=reduce_chain, document_variable_name="doc_summaries"
    )

    # Combines and iteravely reduces the mapped documents
    reduce_documents_chain = ReduceDocumentsChain(
        # This is final chain that is called.
        combine_documents_chain=combine_documents_chain,
        # If documents exceed context for `StuffDocumentsChain`
        collapse_documents_chain=combine_documents_chain,
        # The maximum number of tokens to group documents into.
        token_max=4000,
    )
    # Combining documents by mapping a chain over them, then combining results
    map_reduce_chain = MapReduceDocumentsChain(
        # Map chain
        llm_chain=map_chain,
        # Reduce chain
        reduce_documents_chain=reduce_documents_chain,
        # The variable name in the llm_chain to put the documents in
        document_variable_name="docs",
        # Return the results of the map steps in the output
        return_intermediate_steps=False,
    )

    # text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
    #     chunk_size=1000, chunk_overlap=0
    # )
    # split_docs = text_splitter.split_documents(docs)

    print(map_reduce_chain.run(docs))

def create_tag_chain(schema, user_input, llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613")):

    chain = create_tagging_chain(schema, llm)
    response = chain.run(user_input)
    return response


def create_web_extraction_chain(content:str, schema, schema_type="dict", llm=ChatOpenAI(temperature=0, cache = False)):

    if schema_type=="dict":
        chain = create_extraction_chain(schema, llm)
        response = chain.run(content)
        return response

def create_babyagi_chain(OBJECTIVE: str, llm = OpenAI(temperature=0)):
    
    embeddings = OpenAIEmbeddings()
    embedding_size = 1536
    index = faiss.IndexFlatL2(embedding_size)
    vectorstore = FAISS(embeddings.embed_query, index, InMemoryDocstore({}), {})
    # Logging of LLMChains
    # If None, will keep on going forever
    max_iterations: Optional[int] = 3
    baby_agi = BabyAGI.from_llm(
        llm=llm, vectorstore=vectorstore, verbose=True, max_iterations=max_iterations
    )
    response = baby_agi({"objective": OBJECTIVE})

def generate_multifunction_response(query: str, tools: List[Tool], early_stopping=False, max_iter = 2, llm = ChatOpenAI(model="gpt-3.5-turbo-0613", cache=False)) -> str:

    """ General purpose agent that uses the OpenAI functions ability.
     
    See: https://python.langchain.com/docs/modules/agents/agent_types/openai_multi_functions_agent 

    Args:

        query (str)

        tools (List[Tool]): all agents must have at least one tool

    Keyworkd Args:

        max_iter (int): maximum iteration for early stopping, default is 2

        llm (BaseModel): default is ChatOpenAI(model="gpt-3.5-turbo-0613")

    Returns:

        answer to the query
    
    """
    if early_stopping:
        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.OPENAI_MULTI_FUNCTIONS, 
            max_iterations=max_iter,
            early_stopping_method="force",
            verbose=True
        )
    else:
        agent = initialize_agent(
            tools, llm, agent=AgentType.OPENAI_MULTI_FUNCTIONS
        )
    try: 
        response = agent({"input": query}).get("output", "")   
        print(f"Successfully got multifunction response: {response}")
    except Exception as e:
        print(e)
        response = ""
    return response


def create_vectorstore(vs_type: str, file: str, file_type: str, index_name: str, embeddings = OpenAIEmbeddings()) -> FAISS or Redis:

    """ Main function used to create any types of vector stores.

    Args:

        vs_type (str): vector store type, "faiss" or "redis"

        file (str): file or directory path

        file_type (str): "dir" or "file"

        index_name (str): name of vector store 

    Returns:

        Faiss or Redis vector store


    """

    try: 
        docs = split_doc(file, file_type, splitter_type="tiktoken")
        if (vs_type=="faiss"):
            db=FAISS.from_documents(docs, embeddings)
            # db.save_local(index_name)
            print("Succesfully created Faiss vector store.")
        elif (vs_type=="redis"):
            db = Redis.from_documents(
                docs, embeddings, redis_url=redis_url, index_name=index_name
            )
            print("Successfully created Redis vector store.")
                # db=create_redis_index(docs, embeddings, index_name, source)
    except Exception as e:
        raise e
    return db

        


def retrieve_redis_vectorstore(index_name, embeddings=OpenAIEmbeddings()) -> Redis or None:

    """ Retrieves the Redis vector store if exists, else returns None  """

    try:
        rds = Redis.from_existing_index(
        embeddings, redis_url=redis_url, index_name=index_name
        )
        return rds
    except Exception as e:
        raise e
    


def drop_redis_index(index_name: str) -> None:

    """ Drops the redis vector store with index name. """

    print(Redis.drop_index(index_name, delete_documents=True, redis_url=redis_url))





def merge_faiss_vectorstore(index_name_main: str, file: str, embeddings=OpenAIEmbeddings()) -> FAISS:

    """ Merges files into existing Faiss vecstores if main vector store exists. Else, main vector store is created.

    Args:

        index_name_main (str): name of the main Faiss vector store where others would merge into

        file (str): file path 

    Returns:

        main Faiss vector store 
    
    """
    
    main_db = retrieve_faiss_vectorstore( index_name_main)
    if main_db is None:
        main_db = create_vectorstore("faiss", file, "file", index_name_main)
        print(f"Successfully created vectorstore: {index_name_main}")
    else:
        db = create_vectorstore("faiss", file, "file", "temp")
        main_db.merge_from(db)
        print(f"Successfully merged vectorestore {index_name_main}")
    return main_db
    


def retrieve_faiss_vectorstore(path: str, embeddings = OpenAIEmbeddings()) -> FAISS or None:

    """ Retrieves the Faiss vector store if exists, else returns None  """
    
    try:
        db = FAISS.load_local(path, embeddings)
        return db
    except Exception as e:
        return None
    
def handle_tool_error(error: ToolException) -> str:

    """ Handles tool exceptions. """

    if error==JSONDecodeError:
        return "Reformat in JSON and try again"
    elif error.args[0].startswith("Too many arguments to single-input tool"):
        return "Format in a SINGLE JSON STRING. THIS IS A SINGLE-INPUT TOOL!."
    return (
        "The following errors occurred during tool execution:"
        + error.args[0]
        + "Please try another tool.")



# # Set up a prompt template
class CustomPromptTemplate(BaseChatPromptTemplate):
    # The template to use
    template: str
    # The list of tools available
    tools: List[Tool]
    
    def format_messages(self, **kwargs) -> str:
        # Get the intermediate steps (AgentAction, Observation tuples)
        # Format them in a particular way
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "
        # Set the agent_scratchpad variable to that value
        kwargs["agent_scratchpad"] = thoughts
        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])
        formatted = self.template.format(**kwargs)
        return [HumanMessage(content=formatted)]
    
class CustomOutputParser(AgentOutputParser):
    
    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:
        # Check if agent should finish
        if "Final Answer:" in llm_output:
            return AgentFinish(
                # Return values is generally always a dictionary with a single `output` key
                # It is not recommended to try anything else at the moment :)
                return_values={"output": llm_output.split("Final Answer:")[-1].strip()},
                log=llm_output,
            )
        # Parse out the action and action input
        regex = r"Action\s*\d*\s*:(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)
        # Return the action and action input
        return AgentAction(tool=action, tool_input=action_input.strip(" ").strip('"'), log=llm_output)

job_done = object() # signals the processing is done  

class CustomStreamingCallbackHandler(BaseCallbackHandler):
    """Callback Handler that Stream LLM response."""

    def __init__(self, queue):
        self.queue = queue

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running. Clean the queue."""
        while not self.q.empty():
            try:
                self.q.get(block=False)
            except Empty:
                continue
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""
        self.queue.put(token)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        self.q.put(job_done)

class MyCustomAsyncHandler(AsyncCallbackHandler):
    
    """Async callback handler that can be used to handle callbacks from langchain."""

    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        print("zzzz....")
        await asyncio.sleep(0.3)
        class_name = serialized["name"]
        print("Hi! I just woke up. Your llm is starting")

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when chain ends running."""
        print("zzzz....")
        await asyncio.sleep(0.3)
        print("Hi! I just woke up. Your llm is ending")


class MyCustomSyncHandler(BaseCallbackHandler):

    """Callback handler that can be used to handle callbacks from langchain."""

    @timeout(5, os.strerror(errno.ETIMEDOUT))
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        print("zzzz....")
        print("Hi! I just woke up. Your llm is starting")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when chain ends running."""
        print("zzzz....")
        print("Hi! I just woke up. Your llm is ending")


    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> Any:
        """Run when chain ends running."""
        print("zzzz....")
        print("Hi! I just woke up. Your chain is ending")


if __name__ == '__main__':

    # db =  create_vectorstore("redis", "./web_data/", "dir", "index_web_advice")
     db = create_vectorstore("faiss", "./interview_data/", "dir", "faiss_interview_data")
     db.save_local("faiss_interview_data")
    #  create_vectorstore("faiss", "./log/", "dir", "chat_debug")
 

    


