import openai
# from langchain.agents.react.base import DocstoreExplorer
from langchain_community.document_loaders import TextLoader, DirectoryLoader, S3FileLoader, S3DirectoryLoader
# from langchain.indexes import VectorstoreIndexCreator
# from langchain.chat_models import ChatOpenAI
# from langchain.llms import OpenAI
from langchain_openai import OpenAI, ChatOpenAI, OpenAIEmbeddings
from langchain.agents import AgentOutputParser, initialize_agent
from langchain.chains.summarize import load_summarize_chain
# from langchain.memory import ConversationBufferMemory
from langchain.chains.qa_with_sources import load_qa_with_sources_chain, stuff_prompt
import os
# from langchain.chains.mapreduce import MapReduceChain
from langchain.chains import ( RetrievalQA, RetrievalQAWithSourcesChain, TransformChain, StuffDocumentsChain,  create_tagging_chain, create_tagging_chain_pydantic, 
                               ReduceDocumentsChain, MapReduceDocumentsChain, create_extraction_chain, LLMMathChain,
                              create_extraction_chain_pydantic,  LLMChain)
# import redis
# import json
from typing import List, Union, Any, Optional, Dict
import re
from langchain.agents.agent_types import AgentType
# from pydantic import BaseModel, Field
from langchain_community.document_transformers import EmbeddingsRedundantFilter, LongContextReorder
from langchain.retrievers.document_compressors import DocumentCompressorPipeline, EmbeddingsFilter, CohereRerank
from langchain.retrievers import ContextualCompressionRetriever
from utils.basic_utils import read_file
from json import JSONDecodeError
from langchain.retrievers import EnsembleRetriever
from langchain_community.document_transformers.openai_functions import create_metadata_tagger
from langchain_experimental.autonomous_agents import BabyAGI
import faiss
from utils.lancedb_utils import create_lancedb_table
# from langchain.docstore import InMemoryDocstore
from langchain.indexes import SQLRecordManager, index
from langchain_community.vectorstores import Redis, ElasticsearchStore, OpenSearchVectorSearch, FAISS, DocArrayInMemorySearch, LanceDB
# from opensearchpy import RequestsHttpConnection
from langchain.indexes import SQLRecordManager, index
from langchain_experimental.smart_llm import SmartLLMChain
from langchain_core.prompts import BaseChatPromptTemplate, PromptTemplate, ChatPromptTemplate
from utils.aws_manager import get_client




from dotenv import load_dotenv, find_dotenv
# from langchain_community.cache import RedisCache, RedisSemanticCache
# from langchain_community.docstore import Wikipedia
# from langchain_community.embeddings import ElasticsearchEmbeddings
from langchain_community.retrievers import BM25Retriever
# from langchain_community.utilities import GoogleSearchAPIWrapper, SerpAPIWrapper
from langchain_core.agents import AgentAction, AgentFinish
# from langchain_core.callbacks import AsyncCallbackHandler, BaseCallbackHandler
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import CommaSeparatedListOutputParser
# from langchain_core.outputs import LLMResult
from langchain_core.tools import Tool, ToolException, tool
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter

_ = load_dotenv(find_dotenv()) # read local .env file
# You may need to update the path depending on where you stored it
openai.api_key = os.environ["OPENAI_API_KEY"]
aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"]
aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"]
# redis_password=os.getenv('REDIS_PASSWORD')
# redis_url = f"redis://:{redis_password}@localhost:6379"
# redis_client = redis.Redis.from_url(redis_url)


STORAGE = os.environ["STORAGE"]
if STORAGE=="CLOUD":
    bucket_name = os.environ["BUCKET_NAME"]
    s3_save_path = os.environ["S3_CHAT_PATH"]
    s3 = get_client('s3')
else:
    bucket_name=None
    s3=None


def split_doc(path, path_type='dir', splitter_type = "recursive", chunk_size=200, chunk_overlap=10) -> List[Document]:

    """ Splits file or files in directory into different sized chunks with different text splitters.
    
    For the purpose of splitting text and text splitter types, reference: https://python.langchain.com/docs/modules/data_connection/document_transformers/
    
    Keyword Args:

        path (str): file or directory path

        path_type (str): "file" or "dir"

        splitter_type (str): "recursive" or "tiktoken"

        chunk_size (int): smaller chunks in retrieval tend to alleviate going over token limit

        chunk_overlap (int): how many characters or tokens overlaps with the previous chunk

    Returns:

        a list of LangChain Document
    
    """
    # if STORAGE=="LOCAL":
    if (path_type=="file"):
        loader = TextLoader(path)
    elif (path_type=="dir"):
        loader = DirectoryLoader(path, glob="*.txt", recursive=True)
    # elif STORAGE=="CLOUD":
    #     if (path_type=="file"):
    #         loader = S3FileLoader(bucket_name, path, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    #     elif (path_type=="dir"):
    #         loader = S3DirectoryLoader(bucket_name, path, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
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
    # yield from text_splitter.split_documents(documents)
    docs = text_splitter.split_documents(documents)
    return docs

def split_doc_file_size(path: str, file_type="file", use_bytes_threshold=True, threshold_bytes=1500,  splitter_type = "tiktoken", chunk_size=200, ) -> List[Document]:

    """ Splits files into LangChain Document according to file size. If less than threshold bytes, file is not split. Otherwise, calls "split_doc" function to split the file. 
    
    Args:

        path: file or directory path

    Keyword Args:

        file_type (str): "file" or "dir"

        threshold_bytes (int): default is 15000

        storage (str): "LOCAL" or "CLOUD"

        splitter_type (str): "tiktoken" or "recursive"

        chunk_size (int)

        bucket_name (str): name of the S3 bucket that contains the files, None is storage is local

        s3 (Any): instance of boto3's S3 client for connecting to the bucket

    Returns:

        a list of LangChain Document
        
    """
    
    # if STORAGE=="LOCAL":
    bytes = os.path.getsize(path)
    # elif STORAGE=="CLOUD":
    #     response = s3.head_object(Bucket=bucket_name, Key=path)
    #     bytes = response['ContentLength']
    print(f"File size is {bytes} bytes")
    docs: List[Document] = []
    # if file is small, don't split
    # 1 byte ~= 1 character, and 1 token ~= 4 characters, so 1 byte ~= 0.25 tokens. Max length is about 4000 tokens for gpt3.5, so if file is less than 15000 bytes, don't need to split. 
    if use_bytes_threshold and  bytes<threshold_bytes:
        docs.extend([Document(
            page_content = read_file(path,)
        )])
    else:
        docs.extend(split_doc(path, "file", chunk_size=chunk_size, splitter_type=splitter_type))
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

def create_record_manager(name: str):
    """LangChain indexing makes use of a record manager (RecordManager) that keeps track of document writes into the vector store."""
    namespace = f"elasticsearch/{name}"
    record_manager = SQLRecordManager(
    namespace, db_url="sqlite:///record_manager_cache.sql" )
    record_manager.create_schema()
    return record_manager

    
def update_index(docs: List[Document], record_manager: SQLRecordManager, vectorstore: Any, cleanup_mode="full"):

    """ See: https://python.langchain.com/docs/modules/data_connection/indexing """

    indexing_stats = index(docs,
        record_manager, 
        vectorstore,
        cleanup=cleanup_mode,
        # source_id_key="source",
        # force_update=os.environ.get("FORCE_UPDATE") or "false"
        )
    print(f"Indexing stats: {indexing_stats}")
    

def clear_index(record_manager: SQLRecordManager, vectorstore:Any, cleanup_mode="full"):

    """ See: https://python.langchain.com/docs/modules/data_connection/indexing """

    indexing_stats = index(
        [],
        record_manager,
        vectorstore,
        cleanup=cleanup_mode,
        # source_id_key="source",
    )
    print(f"Indexing stats: {indexing_stats}")

def add_metadata(doc: Document, field_name, field_value) -> Document:

    """ Adds metadata to document. 
    See example on adding and filtering metadata: https://python.langchain.com/docs/integrations/vectorstores/elasticsearch#basic-example """

    doc.metadata[field_name] = field_value
    return doc


    
def reorder_docs(docs: List[Document]) -> List[Document]:

    """ Reorders documents so that most relevant documents are at the beginning and the end, as in long context, the middle text tend to be ignored.
     See: https://python.langchain.com/docs/modules/data_connection/document_transformers/post_retrieval/long_context_reorder

     Args: 

        docs: a list of Langchain Documents

    Returns:

        a list of reordered Langchain Documents

    """
    reordering = LongContextReorder()
    reordered_docs = reordering.transform_documents(docs)
    return reordered_docs



def create_ensemble_retriever(docs: List[Document]) -> Any:

    """See purpose and usage: https://python.langchain.com/docs/modules/data_connection/retrievers/ensemble
    
    Args:

        docs: a list of LangChain Document class

    returns:

        vector store retriever
    """

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

""
def create_compression_retriever(retriever: Any, compressor_type="redundant_filter", search_type="mmr", search_kwargs={"k":1}) -> ContextualCompressionRetriever:

    """ Creates a compression retriever given a vector store path. 
    For redundant filter compressor: https://python.langchain.com/docs/modules/data_connection/retrievers/contextual_compression/
    For cohere rerank compressor: https://python.langchain.com/docs/integrations/retrievers/cohere-reranker

    Args:

        retriever: any retriever    
    
    Keyword Args:

        compressor_type (str): redundant_filter or cohere_rerank

        search_type (str): mmr, similar_score_threshold, etc.

        search_kwargs (str): depends on search_type

    Returns:

        vector store retriever

    """

    embeddings = OpenAIEmbeddings()
    splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=0, separator=". ")
    if compressor_type=="redundant_filter":
        redundant_filter = EmbeddingsRedundantFilter(embeddings=embeddings)
        relevant_filter = EmbeddingsFilter(embeddings=embeddings, similarity_threshold=0.76)
        compressor = DocumentCompressorPipeline(
            transformers=[splitter, redundant_filter, relevant_filter]
        )
    elif compressor_type=="cohere_rerank":
        compressor = CohereRerank()
    # store = retrieve_vectorstore(vs_type, vectorstore)
    # retriever = vectorstore.as_retriever(search_type=search_type,  search_kwargs=search_kwargs)
    # retriever = store.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": .5, "k":3})

    compression_retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=retriever)

    return compression_retriever


def create_summary_chain(path: str, prompt_template: str, chain_type = "stuff", chunk_size=2000,  llm=OpenAI(),) -> str:

    """ See summarization chain: https://python.langchain.com/docs/use_cases/summarization
    
    Args:

        file: file path

        prompt_template: for example
            "Write a concise summary of the following:
            "{text}"
            CONCISE SUMMARY:"

    Keyword Args:

        chain_type (str): stuff, map_reduce, refine

        llm (BaseModel)

        storage: LOCAL or CLOUD

        bucket_name: s3 bucket name

        s3: s3 client

    Returns:
    
        a summary of the give file
    
    """
    docs = split_doc_file_size(path, chunk_size=chunk_size,)
    PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])
    chain = load_summarize_chain(llm, chain_type="stuff", prompt=PROMPT)
    response = chain.run(docs)
    print(f"Sucessfully got summary: {response}")
    return response

def create_refine_chain(files: List[str], prompt_template:str, refine_template:str, llm=ChatOpenAI()) -> str:

    """ Creates a refine chain for multiple documents summarization: https://python.langchain.com/docs/use_cases/summarization#option-3-refine

        Args: 

            files: a list of file paths 

            prompt_template: for example 
             "Write a concise summary of the following:
                {text}
                CONCISE SUMMARY:"
            
            refine_template: for example
                "Your job is to produce a final summary\n"
                "We have provided an existing summary up to a certain point: {existing_answer}\n"
                "We have the opportunity to refine the existing summary"
                "(only if needed) with some more context below.\n"
                "------------\n"
                "{text}\n"
                "------------\n"
                "Given the new context, refine the original summary in Italian"
                "If the context isn't useful, return the original summary."
            )

        Keyword Args:

            llm (Basemodel)

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

            files: a list of file paths 

            map_template: mapping stage prompt

            reduce_template: reducing stage prompt

        
        Keyword Args:

            llm (Basemodel)

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

    return map_reduce_chain.run(docs)

def create_input_tagger(schema, user_input, llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")) -> Dict[str, Any]:

    """ Tags input text according to schema: https://python.langchain.com/docs/use_cases/tagging """

    #  Args:

    #   schema: for example
    #    {
    # "properties": {
    #     "aggressiveness": {
    #         "type": "integer",
    #         "enum": [1, 2, 3, 4, 5],
    #         "description": "describes how aggressive the statement is, the higher the number the more aggressive",
    #     },
    #     "language": {
    #         "type": "string",
    #         "enum": ["spanish", "english", "french", "german", "italian"],
    #     },
    # },
    # "required": ["language", "sentiment", "aggressiveness"],
    # }

    # user_input: usually a query

    # Keyword Args:

    #     llm (BaseModel)
       
    # Returns:

    #     dictionary of metadata

    chain = create_tagging_chain(schema, llm)
    response = chain.run(user_input)
    # tagging_prompt = ChatPromptTemplate.from_template(
    # """
    #     Extract the desired information from the following passage.

    #     Only extract the properties mentioned in the 'Classification' function.

    #     Passage:
    #     {input}
    #     """
    #     )
    # llm = llm.with_structured_output(
    #     schema
    # )
    # chain = tagging_prompt | llm
    # response = await chain.ainvoke({"input":user_input})
    print(response)
    return response

def create_document_tagger(schema:Dict[str, Any], doc:Document, llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")) -> Dict[str, Any]:

    """ Tags a document according to schema: https://python.langchain.com/docs/integrations/document_transformers/openai_metadata_tagger

    Args:
        schema: for example  
            {
                "properties": {
                    "movie_title": {"type": "string"},
                    "critic": {"type": "string"},
                    "tone": {"type": "string", "enum": ["positive", "negative"]},
                },
                "required": ["movie_title", "critic", "tone"],
            }
        doc: for example
            Document(
                page_content="TEST"
            )

    Keyword Args:

        llm (BaseModel)

    Returns:

        dictionary of metadata
    """
    document_transformer = create_metadata_tagger(metadata_schema=schema, llm=llm)
    enhanced_document = document_transformer.transform_documents([doc])
    return enhanced_document[0].metadata


def create_structured_output_chain(content:str, schema: Dict[str, Any], llm=ChatOpenAI(temperature=0, cache = False)):

    """ For structured output according to a schema, see: https://python.langchain.com/docs/use_cases/extraction.
     
      Args:
       
        content: for example  "Alex is 5 feet tall. Claudia is 1 feet taller Alex and jumps higher than him. Claudia is a brunette and Alex is blonde."
         
        schema: for example

                {
            "properties": {
                "name": {"type": "string"},
                "height": {"type": "integer"},
                "hair_color": {"type": "string"},
            },
            "required": ["name", "height"] ,
        }

        Keyword Args:

            llm (BaseModel)

        Returns:

            for example [{'name': 'Alex', 'height': 5, 'hair_color': 'blonde'},
                        {'name': 'Claudia', 'height': 6, 'hair_color': 'brunette'}]

          """

    chain = create_extraction_chain(schema, llm)
    response = chain.run(content)
    return response

def create_pydantic_parser(content:str, schema, llm=ChatOpenAI(model="gpt-4o-mini"), ):
    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert extraction algorithm. "
            "Only extract relevant information from the text. "
            "If you do not know the value of an attribute asked to extract, "
            "return null for the attribute's value.",
        ),
        # Please see the how-to about improving performance with
        # reference examples.
        # MessagesPlaceholder('examples'),
        ("human", "{content}"),
            ]
        )
    
    runnable = prompt | llm.with_structured_output(schema=schema)
    response = runnable.invoke({"content": content})
    response_dict = response.dict()
    # print(response_dict)
    return response_dict

async def acreate_pydantic_parser(content:str, schema, llm=ChatOpenAI(model="gpt-4o-mini"), ):
    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert extraction algorithm. "
            "Only extract relevant information from the text. "
            "If you do not know the value of an attribute asked to extract, "
            "return null for the attribute's value.",
        ),
        # Please see the how-to about improving performance with
        # reference examples.
        # MessagesPlaceholder('examples'),
        ("human", "{content}"),
            ]
        )
    
    runnable = prompt | llm.with_structured_output(schema=schema)
    response = await runnable.ainvoke({"content": content})
    response_dict = response.dict()
    # print(response_dict)
    return response_dict

def create_comma_separated_list_parser(input_variables, base_template, query_dict):

    """Outputs in comma separated list format: https://python.langchain.com/v0.1/docs/modules/model_io/output_parsers/types/csv/
    
    Example parameters: 
    prompt = PromptTemplate(
        template="List five {subject}.\n{format_instructions}",
        input_variables=["subject"],
        partial_variables={"format_instructions": format_instructions},
    )
    chain.invoke({"subject": "ice cream flavors"})
   
     """

    output_parser = CommaSeparatedListOutputParser()

    format_instructions = output_parser.get_format_instructions()
    prompt = PromptTemplate(
        template= base_template + """\n{format_instructions}""",
        input_variables=input_variables,
        partial_variables={"format_instructions": format_instructions},
    )

    model = ChatOpenAI(temperature=0, model="gpt-4o-mini")
    chain = prompt | model | output_parser
    response = chain.invoke(query_dict)
    print(response)
    return response

def create_babyagi_chain(OBJECTIVE: str, vectorstore:Any, llm = OpenAI(temperature=0)):
    
    embeddings = OpenAIEmbeddings()
    embedding_size = 1536
    index = faiss.IndexFlatL2(embedding_size)
    # vectorstore = FAISS(embeddings.embed_query, index, InMemoryDocstore({}), {})
    # Logging of LLMChains
    # If None, will keep on going forever
    max_iterations: Optional[int] = 3
    baby_agi = BabyAGI.from_llm(
        llm=llm, vectorstore=vectorstore, verbose=True, max_iterations=max_iterations
    )
    response = baby_agi({"objective": OBJECTIVE})
    return response


async def create_smartllm_chain(query, n_ideas=3, verbose=True, llm=ChatOpenAI()):

    prompt = PromptTemplate.from_template(query)
    chain = SmartLLMChain(llm=llm, prompt=prompt, n_ideas=n_ideas, verbose=verbose)
    response = await chain.arun({})
    print(response)
    return response

# Assuming you have an instance of BaseOpenAI or OpenAIChat called `llm_instance`

def generate_multifunction_response(query: str, tools: List[Tool], early_stopping=True, max_iter = 2, llm = ChatOpenAI(model="gpt-4o-mini", cache=False)) -> str:

    """ General purpose agent that uses the OpenAI functions ability.
     
    See: https://python.langchain.com/docs/modules/agents/agent_types/openai_multi_functions_agent 

    Args:

        query

        tools: all agents must have at least one tool

    Keyworkd Args:

        max_iter (int): maximum iteration for early stopping

        llm (BaseModel)

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
        response = agent.invoke({"input": query}) 
        print(f"Successfully got multifunction response: {response}")
    except Exception as e:
        print(e)
        response = ""
    return response.get("output", "") if response else response



def create_vectorstore(vs_type: str, index_name: str, file="", file_type="file",awsauth=None, embeddings = OpenAIEmbeddings()) -> Any:

    """ Main function used to create any types of vector stores.
    Redis: https://python.langchain.com/docs/integrations/vectorstores/redis
    Faiss: https://python.langchain.com/docs/integrations/vectorstores/faiss
    OpenSearch: https://python.langchain.com/docs/integrations/vectorstores/opensearch#using-aoss-amazon-opensearch-service-serverless

    Args:

        vs_type: faiss, redis, or open_search

        file: file or directory path

        index_name: name or path of the index
    
    Keyword Args:

        file_type (str):  "dir" or "file"

        storage (str):  LOCAL or CLOUD

        bucket_name (str): name of the S3 bucket, None if local storage

        s3 (Any): instance of a boto3 S3 client, None if local storage

        awsauth (AWS4Auth): instance of an AWS4Auth, None if local storage

        embeddings (Any)

    Returns:

        Faiss or Redis vector store """

    try: 
        if (file!=""):
            docs = split_doc_file_size(file, splitter_type="tiktoken")
        if (vs_type=="faiss"):
            db=FAISS.from_documents(docs, embeddings)
            db.save_local(index_name)
            print("Succesfully created Faiss vector store.")
        # elif (vs_type=="redis"):
        #     db = Redis.from_documents(
        #         docs, embeddings, redis_url=redis_url, index_name=index_name
        #     )
        #     print("Successfully created Redis vector store.")
                # db=create_redis_index(docs, embeddings, index_name, source)
        elif (vs_type=="lancedb"):
            table = create_lancedb_table()
            db= LanceDB.from_documents(docs, embeddings, connection=table)
            # query = "What did a set in Tableau"
            # docs = db.similarity_search(query)
            # print(docs[0].page_content)
        elif (vs_type=="elasticsearch"):
            db= ElasticsearchStore(
                es_url="http://localhost:9200", index_name=index_name, embedding=embeddings,
                #  strategy=ElasticsearchStore.ApproxRetrievalStrategy(),
            )
        elif (vs_type=="open_search"):
            print("before open search")
            # db = OpenSearchVectorSearch.from_documents(
            #     docs,
            #     embeddings,
            #     opensearch_url="http://localhost:9200",
            #     http_auth=awsauth,
            #     timeout=300,
            #     use_ssl=True,
            #     verify_certs=True,
            #     connection_class=RequestsHttpConnection,
            #     index_name=index_name,
            #     engine="faiss",
            # )
            db= OpenSearchVectorSearch.from_documents(
                docs,
                embeddings,
                opensearch_url="http://localhost:9200",
                # engine="faiss",
                # space_type="innerproduct",
                # ef_construction=256,
                # m=48,
            )
            docs = db.similarity_search("what is a set in tableau")
            print(docs[0].page_content)
            # db = ElasticsearchStore.from_documents(
            # docs,
            # embeddings,
            # es_url="http://localhost:9200",
            # index_name=index_name,
            # )
            # embeddings = ElasticsearchEmbeddings.from_credentials(
            #     model_id,
            #     es_cloud_id='your_cloud_id',
            #     es_user='your_user',
            #     es_password='your_password'
            #     )
            # document_embeddings = embeddings.embed_documents(docs)
            print("Successfully created OpenSearch vector store.")

    except Exception as e:
        raise e
    print(f"Successfully created vector store {index_name}")
    return db

def retrieve_vectorstore(vs_type:str, index_name:str, embeddings = OpenAIEmbeddings(), ) -> Any:

    """ Retrieves vector store according to the index name.
     
      Args:

        vs_type: faiss, redis, or open_search

        index_name: name or path
    
    Keyword Args:

        embeddings (Any)
    
    Returns:

        vector store
        
    """

    # if vs_type=="redis":
    #     try:
    #         rds = Redis.from_existing_index(
    #         embeddings, redis_url=redis_url, index_name=index_name
    #         )
    #         return rds
    #     except Exception as e:
    #         return None
    if vs_type=="faiss":
        try:
            db = FAISS.load_local(index_name, embeddings, allow_dangerous_deserialization=True)
            return db
        except Exception as e:
            print(e)
            return None
    elif vs_type=="elasticsearch":
        try:
            db = ElasticsearchStore(
                es_url="http://localhost:9200",
                index_name=index_name,
                embedding=embeddings
            )
            return db
        except Exception as e:
            raise e
    elif vs_type=="open_search":
        try:
            db = OpenSearchVectorSearch(
                index_name=index_name,
                embedding_function=embeddings,
                opensearch_url="http://localhost:9200",
            )
            return db
        except Exception as e:
            return None


def update_vectorstore(end_path: str, vs_path:str, index_name: str, record_name=None, ) -> None:

    """ Creates and updates vector store for AI agent to be used as RAG. 
    
    Args:
    
        end_path: path to file

        index_name: name of the vector store

        vs_path: path where vector store is saved

    Keyword Args:

        record_name: name of the record manager for the vector store, if using record manager

        storage: LOCAL or CLOUD

        bucket_name: S3 bucket name

        s3: BOTO3's S3 client instance
        
    """
    if STORAGE=="LOCAL":
        vs = merge_faiss_vectorstore(index_name, end_path)
        vs.save_local(vs_path) 
    elif STORAGE=="CLOUD":
        docs = split_doc_file_size(end_path, "file", )
        vectorstore = retrieve_vectorstore("elasticsearch", index_name=index_name)
        record_manager=create_record_manager(record_name)
        if vectorstore is None:
            vectorstore = create_vectorstore(vs_type="elasticsearch", 
                            index_name=index_name, 
                            )
        update_index(docs=docs, record_manager=record_manager, vectorstore=vectorstore, cleanup_mode=None)



# def drop_redis_index(index_name: str) -> None:

#     """ Drops the redis vector store with index name. """

#     print(Redis.drop_index(index_name, delete_documents=True, redis_url=redis_url))





def merge_faiss_vectorstore(main_db: str, file: str, file_type="dir", index_name="tmp", merge_type="tmp_into_main", embeddings=OpenAIEmbeddings()) -> FAISS:

    """ Merges files into existing Faiss vecstores if main vector store exists. Else, main vector store is created.

    Args:

        index_name_main: name of the main Faiss vector store where others would merge into

        file: file path 

    Keyword Args:

        embeddings (Any)

    Returns:

        main Faiss vector store 
    
    """
    
    db = create_vectorstore(vs_type="faiss", index_name=index_name, file=file, file_type=file_type,)
    print(f"{index_name} vector store", db)
    if "main_into_other":
        db.merge_from(main_db)
        print(f"Successfully merged vectorestore main into {index_name}")
        return main_db
    elif "tmp_into_main":
        main_db.merge_from(db)
        print(f"Successfully merged vectorestore tmp into main")
        return main_db
    

        
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


# class MyCustomAsyncHandler(AsyncCallbackHandler):
    
#     """Async callback handler that can be used to handle callbacks from langchain."""

#     async def on_llm_start(
#         self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
#     ) -> None:
#         """Run when chain starts running."""
#         print("zzzz....")
#         await asyncio.sleep(0.3)
#         class_name = serialized["name"]
#         print("Hi! I just woke up. Your llm is starting")

#     async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
#         """Run when chain ends running."""
#         print("zzzz....")
#         await asyncio.sleep(0.3)
#         print("Hi! I just woke up. Your llm is ending")


# class MyCustomSyncHandler(BaseCallbackHandler):

#     """Callback handler that can be used to handle callbacks from langchain."""

#     @timeout(5, os.strerror(errno.ETIMEDOUT))
#     def on_llm_start(
#         self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
#     ) -> None:
#         """Run when chain starts running."""
#         print("zzzz....")
#         print("Hi! I just woke up. Your llm is starting")

#     def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
#         """Run when chain ends running."""
#         print("zzzz....")
#         print("Hi! I just woke up. Your llm is ending")


#     def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> Any:
#         """Run when chain ends running."""
#         print("zzzz....")
#         print("Hi! I just woke up. Your chain is ending")


if __name__ == '__main__':

    # db =  create_vectorstore("redis", "./web_data/", "dir", "index_web_advice")
    # db = create_vectorstore("faiss", "./backend/faiss_interview_data", "./interview_data/", "dir", )
    retrieve_vectorstore("faiss", "./backend/faiss_interview_data/")
    #  create_vectorstore("faiss", "./log/", "dir", "chat_debug")
 

    


