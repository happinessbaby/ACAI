import openai
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.cache import InMemoryCache
import langchain
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
import json
from json import JSONDecodeError
import os
from pathlib import Path
from typing import Any
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from utils.common_utils import  check_content
from utils.langchain_utils import retrieve_vectorstore
# from langchain.prompts import BaseChatPromptTemplate
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.memory import ConversationBufferMemory, ReadOnlySharedMemory
from langchain.agents import initialize_agent
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.memory import ChatMessageHistory
from langchain.schema import messages_from_dict, messages_to_dict, AgentAction
from langchain.docstore import InMemoryDocstore
from langchain.agents import AgentExecutor, ZeroShotAgent
from langchain.tools.human.tool import HumanInputRun
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks import get_openai_callback, StdOutCallbackHandler, FileCallbackHandler
from langchain.agents.openai_functions_agent.agent_token_buffer_memory import AgentTokenBufferMemory
from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage
from langchain.prompts import MessagesPlaceholder
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.vectorstores import FAISS
# from feast import FeatureStore
import pickle
import json
import langchain
import faiss
from loguru import logger
from langchain.evaluation import load_evaluator
from utils.basic_utils import convert_to_txt, read_txt
from utils.openai_api import get_completion
from langchain.schema import OutputParserException
from multiprocessing import Process, Queue, Value
from typing import List, Dict
from json import JSONDecodeError
from langchain.tools import tool
import re
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt
from langchain.tools.file_management.read import ReadFileTool
from langchain.cache import InMemoryCache
from langchain.tools import StructuredTool
from urllib import request
from langchain.globals import set_llm_cache
from utils.agent_tools import create_retriever_tools, create_vs_retriever_tools
from langchain.tools.retriever import create_retriever_tool


from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

memory_key="chat_history"
memory_max_token = 500
openai.api_key = os.environ["OPENAI_API_KEY"]
log_path = os.environ["LOG_PATH"]
save_path = os.environ["SAVE_PATH"]
faiss_interview_data_path= os.environ["FAISS_INTERVIEW_DATA_PATH"]
# set recording parameters
duration = 5 # duration of each recording in seconds
fs = 44100 # sample rate
channels = 1 # number of channel
# Code for audio part: https://github.com/VRSEN/langchain-agents-tutorial/blob/main/main.py


class InterviewController():

    llm = ChatOpenAI(streaming=True,  callbacks=[StreamingStdOutCallbackHandler()], temperature=0)
    set_llm_cache(InMemoryCache())
    embeddings = OpenAIEmbeddings()
    # chat_memory = ReadOnlySharedMemory(memory=chat_memory)
    # initialize new memory (shared betweeen interviewer and grader_agent)
    interview_memory = AgentTokenBufferMemory(memory_key=memory_key, llm=llm, input_key="input", max_token_limit=memory_max_token)


    def __init__(self, userid, additional_prompt_info, generated_dict):
        self.userid = userid
        self.additional_interview_info = additional_prompt_info
        self.generated_dict = generated_dict
        self._initialize_log()
        self._initialize_interview_agent()
        self._initialize_interview_grader()



    def _initialize_log(self) -> None:
         
        """ Initializes log: https://python.langchain.com/docs/modules/callbacks/filecallbackhandler """

         # initialize file callback logging
        self.logfile = log_path + f"{self.userid}.log"
        self.handler = FileCallbackHandler(self.logfile)
        logger.add(self.logfile,  enqueue=True)
        # Upon start, all the .log files will be deleted and changed to .txt files
        for path in  Path(log_path).glob('**/*.log'):
            file = str(path)
            file_name = path.stem
            if file_name != self.userid: 
                # convert all non-empty log from previous sessions to txt and delete the log
                if os.stat(file).st_size != 0:  
                    convert_to_txt(file, log_path+f"{file_name}.txt")
                os.remove(file)


    def _initialize_interview_agent(self) -> None:


        """ Initialize interviewer agent, a Conversational Retrieval Agent: https://python.langchain.com/docs/use_cases/question_answering/how_to/conversational_retrieval_agents

        Args: 

            json_request (str): input argument from human's question, in this case the interview topic that may be contained in the Human input.

        """

        store = retrieve_vectorstore("faiss", faiss_interview_data_path)
        retriever = store.as_retriever()
        general_tool_description = """Use this tool to generate general interview questions and answer.
        Prioritize other tools over this tool. """
        # general_tool= create_retriever_tools(retriever, "search_interview_database", general_tool_description)
        general_tool = [create_retriever_tool(
            retriever,
            "search_general_database",
            general_tool_description,
        )]
        self.interview_tools = general_tool

        # create vector store retriever tool for interview material
        vs_directory = os.path.join(save_path, self.userid, "interview_material")
        try:
            subfolders= [f.path for f in os.scandir(vs_directory) if f.is_dir()]
            for dirname in list(subfolders):
                vs = FAISS.load_local(dirname, self.embeddings)
                retriever = vs.as_retriever()
                # suffix = dirname.rfind("_")
                # tool_name = "search_" + dirname[:suffix].removeprefix(vs_directory)
                tool_name = "search_" + dirname.removeprefix(vs_directory).removesuffix(f"_{self.userid}")
                tool_description =  """Useful for generating interview questions and answers. 
                    Use this tool more than any other tool during a mock interview session to generate interview questions.
                    Do not use this tool to load any files or documents.  """ 
                tools = create_retriever_tool(retriever, tool_name, tool_description)
                self.interview_tools+=tools
        except FileNotFoundError:
            pass  


            # Human may also have asked for a specific interview topic: {topic}
        #initialize interviewer agent

        template =   f"""
            You are an AI job interviewer. The following, if available, are things pertaining to the interview. Generate your interview questions from them. 
            
           {self.additional_interview_info}

            The main interview content is contained in the tool "search_interview_material", if available. Generate your interview questions from this tool.

            If you have other tools, use them as well to generate interview questions. Please don't skip using the tools if you have any. 

            As an interviewer, you do not need to assess Human's response to your questions. Their response will be sent to a professional grader.         

            Sometimes you will be provided with the professional grader's feedback. They will be handed out to the Human at the end of the session. You should ignore them. 

            Always remember your role as an interviewer. Unless you're told to stop interviewing, you should not stop asking interview questions.

            If the Human is asking about other things instead of answering an interview question, please steer them back to the interview process.

            You do not need to provide any sort of feedbacks. 

            Remember to ask one interview question at a time!

            Please ask your interview question now:

           """
        
        system_message = SystemMessage(
        content=(
          template
        )
        )
        prompt = OpenAIFunctionsAgent.create_prompt(
            system_message=system_message,
            extra_prompt_messages=[MessagesPlaceholder(variable_name="chat_history")]
            )

        print(f"INTERVIEW AGENT TOOLS: {[tools.name for tools in self.interview_tools]}")
        agent = OpenAIFunctionsAgent(llm=self.llm, tools=self.interview_tools, prompt=prompt)

        # messages = chat_prompt.format_messages(
        #           grader_feedback = self.grader_feedback,
        #         instructions = self.instructions
        # )

        # prompt = OpenAIFunctionsAgent.create_prompt(
        #         # system_message=system_msg,
        #         extra_prompt_messages=messages,
        #     )
        # agent = OpenAIFunctionsAgent(llm=llm, tools=study_tools, prompt=prompt)

        self.interview_agent = AgentExecutor(agent=agent,
                                    tools=self.interview_tools, 
                                    memory=self.interview_memory, 
                                    # verbose=True,
                                    return_intermediate_steps=True,
                                    handle_parsing_errors=True,
                                    callbacks = [self.handler])
        




    def _initialize_interview_grader(self) -> None:


        """ Initialize interview grader agent, a Conversational Retrieval Agent: https://python.langchain.com/docs/use_cases/question_answering/how_to/conversational_retrieval_agents """

        system_message = SystemMessage(
        content=(

          f"""You are a professional interview grader who grades the quality of responses to interview questions. 
          
          Access your memory and retrieve the very last piece of the conversation, if available.

          Determine if the AI has asked an interview question. If it has, you are to grade the Human input based on how well it answers the question.

          Otherwise, respond with the phrase "skip" only.

          The following, if available, are things pertaining to the interview.
            
           {self.additional_interview_info}

           The main interview content is contained in the tool "search_interview_material", if available.

           If you have other tools, they may also be helpful to you as a grader. 
        
           Remember to use these tools to search for the correct answer.

          If the answer cannot be found in your tools, use your best knowledge. 

          Remember, the Human may not know the answer or may have answered the question incorrectly. Therefore it is important that you provide an informative feedback to the Human's response in the format:

          Positive Feedback: <in which ways the Human answered the question well>

          Negative Feedback: <in which ways the Human failed to answer the question>
        
            """
        #   Your feedback should take both the correct answer and the Human's response into consideration. When the Human's response implies that they don't know the answer, provide the correct answer in your feedback.
        )
        )
        prompt = OpenAIFunctionsAgent.create_prompt(
        system_message=system_message,
        extra_prompt_messages=[MessagesPlaceholder(variable_name="chat_history")]
        )
        agent = OpenAIFunctionsAgent(llm=self.llm, tools=self.interview_tools, prompt=prompt)
        self.grader_agent = AgentExecutor(agent=agent, 
                                        tools=self.interview_tools, 
                                        memory=self.interview_memory, 
                                        # verbose=True,
                                        return_intermediate_steps=True, 
                                        handle_parsing_errors=True,
                                        callbacks = [self.handler])
        

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),  # Exponential backoff between retries
        stop=stop_after_attempt(5)  # Maximum number of retry attempts
    )
    def askAI(self, user_input: str, callbacks=None,) -> str:

        """ Main function that processes all agents' conversation with user.
         
        Args:

            userid (str): session id of user

            user_input (str): user question or response

        Keyword Args:

            callbacks: default is None

        Returns:

            Answer or response by AI (str)  
            
         """

        try:    
            # BELOW IS USED WITH CONVERSATIONAL RETRIEVAL AGENT (grader_agent and interviewer)
            # if (update_instruction):
            #     instruction = self.askMetaAgent()
            #     print(instruction) 
            grader_feedback = self.grader_agent({"input":user_input}).get("output", "")
            # print(f"GRADER FEEDBACK: {grader_feedback}")
            print(f"User Voice Input: {user_input}")
            response = self.interview_agent({"input":user_input})
            response = response.get("output", "sorry, something happened, try again.")        
            # response = self.interview_agent({"input":user_input})    
            # if (evaluate_result):
            #     evalagent_q = Queue()
            #     evalagent_p = Process(target = self.askEvalAgent, args=(response, evalagent_q, ))
            #     evalagent_p.start()
            #     evalagent_p.join()
            #     evaluation_result = evalagent_q.get()
            #     # add evaluation and instruction to log
            #     self.update_meta_data(evaluation_result)
            
            # convert dict to string for chat output
        # let instruct agent handle all exceptions with feedback loop
        except Exception as e:
            print(f"ERROR HAS OCCURED IN ASKAI: {e}")
            error_msg = str(e)
            # needs to get action and action input before error and add it to error message
            # if (update_instruction):
            #     query = f""""Debug the error message and provide Instruction for the AI assistant: {error_msg}
            #         """        
            #     instruction = self.askMetaAgent(query)
                # self.update_instructions(feedback)
            # if evaluate_result:
            #     self.update_meta_data(error_msg)
            self.askAI(user_input, callbacks)        

        # pickle memory (sanity check)
        # with open('conv_memory/' + userid + '.pickle', 'wb') as handle:
        #     pickle.dump(self.chat_history, handle, protocol=pickle.HIGHEST_PROTOCOL)
            # print(f"Sucessfully pickled conversation: {chat_history}")
        return response
    
    def craft_questions(self):
        if self.generated_dict:
            job_description = self.generated_dict.get("job description", "")
            company_description = self.generated_dict.get("company description", "")
            job_specification=self.generated_dict.get("job specification", "")
            questions = "\n\nQUESTIONS TO ASK THE INTERVIEWER: \n"
            questions += get_completion(f"""Based on the following job description, job specification, company description, whichever is available, 
                                   generate 5-10 strategic questions an applicant could ask the hiring manager at the end of the interview.
                                   job description: {job_description} \
                                    job specification: {job_specification} \
                                    company description: {company_description} \
                                   """)
        else:
            questions = ""
        return questions
    
    def write_followup(self):
        if self.generated_dict:
            name = self.generated_dict.get("name", "")
            job = self.generated_dict.get("job", "")
            company=self.generated_dict.get("company", "")
            followup = "\n\nFOLLOW-UP EMAIL: \n"
            followup += get_completion(f""" Applicant {name} recently interviewed for a {job} role at {company}.
                                      Can you generate  a follow-up email that {name} could send to reinterate their interest and tactifully ask the status of the hiring process?""")
        else:
            followup = ""
        return followup
    

    def retrieve_feedback(self):

        """ Retrieves feedback from conversation. """

        # conversation = str(self.interview_memory.chat_memory.messages)
        end_path = os.path.join(log_path, f"{Path(self.logfile).stem}.txt")
        convert_to_txt(self.logfile, end_path)
        conversation = read_txt(end_path)
        feedback = "MOCK INTERVIEW FEEDBACK:\n"
        feedback += get_completion(f"Extract the positive and negative feedbacks from the following conversation: {conversation}")
        return feedback
    
    def output_printout(self, response):
        with open(log_path+"./feedback.txt", "w") as f:
            f.write(response)
        print(f"Successfully retrieved interview feedback summary: {response}")
        return "./feedback.txt"

    
    
        

    
        

