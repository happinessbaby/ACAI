import openai
from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.cache import InMemoryCache
import langchain
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
import os
from pathlib import Path
from typing import Any, Union
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.embeddings import OpenAIEmbeddings
from utils.common_utils import  check_content
from utils.langchain_utils import retrieve_vectorstore, CustomOutputParser, CustomPromptTemplate
# from langchain.prompts import BaseChatPromptTemplate
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.memory import ConversationBufferMemory, ReadOnlySharedMemory, ChatMessageHistory
from langchain.docstore import InMemoryDocstore
from langchain.agents import AgentExecutor, ZeroShotAgent, create_openai_tools_agent, create_openai_functions_agent, create_tool_calling_agent
from langchain.callbacks import get_openai_callback, StdOutCallbackHandler, FileCallbackHandler
from langchain.agents.openai_functions_agent.agent_token_buffer_memory import AgentTokenBufferMemory
from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage
from langchain.prompts import MessagesPlaceholder, PromptTemplate, ChatPromptTemplate
import langchain
import faiss
from loguru import logger
from langchain.evaluation import load_evaluator
from utils.basic_utils import convert_to_txt, read_txt
from utils.openai_api import get_completion
from langchain.schema import OutputParserException
from tenacity import retry, wait_exponential, stop_after_attempt
from langchain.tools.file_management.read import ReadFileTool
from langchain.globals import set_llm_cache
from utils.agent_tools import create_vs_retriever_tools, generateQATool
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import messages_from_dict, messages_to_dict
from utils.aws_manager import session
from langchain_core.runnables.history import RunnableWithMessageHistory

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file


memory_key="chat_history"
memory_max_token = 500
openai.api_key = os.environ["OPENAI_API_KEY"]
log_path = os.environ["LOG_PATH"]
save_path = os.environ["INTERVIEW_PATH"]
faiss_interview_data_path= os.environ["FAISS_INTERVIEW_DATA_PATH"]
user_vs_name = os.environ["USER_INTERVIEW_VS_NAME"]
# set recording parameters
duration = 5 # duration of each recording in seconds
fs = 44100 # sample rate
channels = 1 # number of channel
update_instructions=False
# Code for audio part: https://github.com/VRSEN/langchain-agents-tutorial/blob/main/main.py


class InterviewController():

    # chat_memory = ReadOnlySharedMemory(memory=chat_memory)
    # initialize new memory (shared betweeen interviewer and grader_agent)


    def __init__(self, userId, sessionId, about_interview, interview_industry, generated_dict, learning_material, message_history=None):
        self.userId = userId
        self.sessionId=sessionId
        # self.llm = ChatOpenAI(streaming=True,  callbacks=[StreamingStdOutCallbackHandler()], temperature=0)
        self.llm = ChatOpenAI(temperature=0)
        # set_llm_cache(InMemoryCache())
        # embeddings = OpenAIEmbeddings()
        if self.userId:
            chat_memory = DynamoDBChatMessageHistory(self.userId, self.sessionId, boto3_session=session)
            self.interview_memory = AgentTokenBufferMemory(chat_memory=chat_memory, memory_key=memory_key, llm=self.llm, input_key="input", max_token_limit=memory_max_token)
        else:
            # self.interview_memory = AgentTokenBufferMemory(memory_key=memory_key, llm=self.llm, input_key="input", max_token_limit=memory_max_token)
            self.interview_memory = ChatMessageHistory(session_id=self.sessionId)
        self.about_interview = about_interview
        self.interview_industry = interview_industry
        self.generated_dict = generated_dict
        self.learning_material=learning_material
        self.interviewer_assessment='none'
        self._initialize_log()
        self._initialize_interview_agent()
        self._initialize_interview_grader()
        # self._initialize_meta_agent()



    def _initialize_log(self) -> None:
         
        """ Initializes log: https://python.langchain.com/docs/modules/callbacks/filecallbackhandler """

         # initialize file callback logging
        filename=self.userId if self.userId else "temp"
        self.logfile = log_path + f"{filename}.log"
        self.handler = FileCallbackHandler(self.logfile)
        logger.add(self.logfile,  enqueue=True)
        # Upon start, all the .log files will be deleted and changed to .txt files
        for path in  Path(log_path).glob('**/*.log'):
            file = str(path)
            file_name = path.stem
            if file_name != filename: 
                # convert all non-empty log from previous sessions to txt and delete the log
                if os.stat(file).st_size != 0:  
                    convert_to_txt(file, log_path+f"{file_name}.txt")
                os.remove(file)


    def _initialize_interview_agent(self) -> None:


        """ Initialize interviewer agent, a Conversational Retrieval Agent: https://python.langchain.com/docs/use_cases/question_answering/how_to/conversational_retrieval_agents

        Args: 

            json_request (str): input argument from human's question, in this case the interview topic that may be contained in the Human input.

        """

        #TODO: get industry specific vector store path using a python map/json
        # NOTE:Interviewer uses QA generation tool to generate interview questions
        # vs = retrieve_vectorstore("faiss", faiss_interview_data_path)
        # self.retriever = vs.retriever()
        # general_tool_description = """Use this tool to generate general interview questions and answer.
        # Prioritize other tools over this tool. """
        # # general_tool= create_retriever_tools(retriever, "search_interview_database", general_tool_description)
        # general_tool = create_vs_retriever_tools(
        #     vs.as_retriever(),
        #     "search_general_database",
        #     general_tool_description,
        # )
        # self.interview_tools = general_tool
        if not self.learning_material:
            # self.interview_tools=[generate_interview_QA]
            self.learning_material = "./interview_data/"
        else:
            #TODO: combine user uploaded material with industry speicifc interview_data
            pass
        self.interview_tools=[generateQATool()]
        print("Successfully added search interview material tool")

        template = f"""
            You are a job interviewer. The following, if available, are things pertaining to the interview that you are conducting:  {self.about_interview} \

            The main interview questions and answers should be generated using the tool "generate_interview_QA", if available. Generate your interview questions from this tool using the following inputs.

           interview_material_path:{self.learning_material} \

            As an interviewer, you should not provide the interviewee with answers, and you do not need to assess interviewee's response to your questions. 
            
            The correct answer and the interviewee's response will be sent to a professional grader for assessment.       

            Always remember your role as an interviewer. Unless you're told to stop interviewing, you should not stop asking interview questions.

            If the Human is asking about other things instead of answering an interview question, please steer them back to the interview process.

            You do not need to provide any sort of feedbacks. Please always keep your rold as a job interviewer in mind. You should not act otherwise. 

            Remember to ask one interview question at a time and do not repeat the same type of questions. 


           """
            # There will be an interview assessor that provides you with live feedbacks on the quality of your interview questions and smoothness of the interview session. Please use it to improve your next interview questions.

            # Interview assessor's feedback: {self.interviewer_assessment}

            # Please ask your interview question now:
        
        extra_prompt="""  There will be an interview assessor that provides you with live feedbacks on the quality of your interview questions and smoothness of the interview session. Please use it to improve your next interview questions.

            Interview assessor's feedback: {interviewer_assessment}

            When the interview assessor asks you to end the interview, please compose a message to end the interview. 

            Please ask your interview question now:
            """
            # Sometimes you will be provided with the professional grader's feedback. They will be handed out to the Human at the end of the session. You should ignore them. 
            # If you have other tools, use them as well to generate interview questions. Please don't skip using the tools if you have any. 
        
        
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    template,
                ),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
                )

        # Construct the Tools agent
        agent = create_tool_calling_agent(self.llm, self.interview_tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=self.interview_tools, verbose=True)
        self.interview_agent = RunnableWithMessageHistory(
                agent_executor,
                # This is needed because in most real world scenarios, a session id is needed
                # It isn't really used here because we are using a simple in memory ChatMessageHistory
                lambda session_id: self.interview_memory,
                input_messages_key="input",
                history_messages_key="chat_history",
            )
        # extra_prompt = ChatPromptTemplate.from_template(template = extra_prompt)
        # extra_prompt.format_messages(interviewer_assessment=self.interviewer_assessment)

        # system_message = SystemMessage(
        #     content=(
        #     template
        #     )
        # )
        # prompt = OpenAIFunctionsAgent.create_prompt(
        #     system_message=system_message,
        #     extra_prompt_messages=[MessagesPlaceholder(variable_name="chat_history"), extra_prompt]
        #     )

        # # prompt = ChatPromptTemplate.from_messages(
        # #     [
        # #         ("system", template),
        # #         MessagesPlaceholder("chat_history", optional=True),
        # #         # ("human", "{input}"),
        # #         MessagesPlaceholder("agent_scratchpad"),
        # #     ]
        # # )

        # # prompt.format_messages(about_interview=self.about_interview, learning_material=self.learning_material)
 
        # # agent = OpenAIFunctionsAgent(llm=self.llm, tools=self.interview_tools, prompt=prompt)
        # agent = create_openai_functions_agent(llm=self.llm, tools = self.interview_tools, prompt=prompt)
        # # agent = create_openai_tools_agent(llm=self.llm, tools = self.interview_tools, prompt=prompt)

        # # messages = chat_prompt.format_messages(
        # #           grader_feedback = self.grader_feedback,
        # #         instructions = self.instructions
        # # )

        # # prompt = OpenAIFunctionsAgent.create_prompt(
        # #         # system_message=system_msg,
        # #         extra_prompt_messages=messages,
        # #     )
        # # agent = OpenAIFunctionsAgent(llm=llm, tools=study_tools, prompt=prompt)

        # self.interview_agent = AgentExecutor(agent=agent,
        #                             tools=self.interview_tools, 
        #                             memory=self.interview_memory, 
        #                             # verbose=True,
        #                             return_intermediate_steps=True,
        #                             handle_parsing_errors=True,
        #                             callbacks = [self.handler])
        




    def _initialize_interview_grader(self) -> None:


        """ Initialize interview grader agent, a Conversational Retrieval Agent: https://python.langchain.com/docs/use_cases/question_answering/how_to/conversational_retrieval_agents """

        vs = retrieve_vectorstore("faiss", faiss_interview_data_path)
        self.retriever = vs.as_retriever()
        # system_message = SystemMessage(
        # content=(

        #   f"""You are a professional interview grader who grades the quality of responses to interview questions. 
          
        #   Access your memory and retrieve the very last piece of the conversation, if available.

        #   Determine if the AI has asked an interview question. If it has, check if there's an answer associated with the question.
          
        #   Your job is to grade the Human input based on how well it answers the question.


        #   If there's no question or answer, respond with the phrase "skip" only.

        #   The following, if available, are things pertaining to the interview.
            
        #    {self.about_interview}

        #   Remember, the Human may not know the answer or may have answered the question incorrectly. Therefore it is important that you provide an informative feedback to the Human's response in the format:

        #   Positive Feedback: <in which ways the Human answered the question well>

        #   Negative Feedback: <in which ways the Human failed to answer the question>
        
        #     """
        # #   Your feedback should take both the correct answer and the Human's response into consideration. When the Human's response implies that they don't know the answer, provide the correct answer in your feedback.
        # )
        # )
        
        # Grader uses vector store retrieval to assess the interviewee's response
        # Get the last n messages
        # n = 2
        # last_n_messages = self.interview_memory.chat_memory.messages[-n:]
        # prompt = OpenAIFunctionsAgent.create_prompt(
        # system_message=system_message,
        # extra_prompt_messages=[MessagesPlaceholder(variable_name="chat_history", messages=last_n_messages)]
        # )
        # # agent = OpenAIFunctionsAgent(llm=self.llm, tools=self.interview_tools, prompt=prompt)
        # agent = create_openai_functions_agent(llm=self.llm, tools = self.interview_tools, prompt=prompt)
        # # agent = create_openai_tools_agent(llm=self.llm, tools = self.interview_tools, prompt=system_message)
        # self.grader_agent = AgentExecutor(agent=agent, 
        #                                 tools=self.interview_tools, 
        #                                 memory= ReadOnlySharedMemory(memory=self.interview_memory),
        #                                 # verbose=True,
        #                                 return_intermediate_steps=True, 
        #                                 handle_parsing_errors=True,
        #    
        #                              callbacks = [self.handler])
        system_msg = """
            Please assess the interviewee's answer to the interviewer's question based on the content below, which include best practices of answering interview questions:
            
            {context}

            Q&A: {QA}

            Please be critical and constructive of the interviewee's answer. 
            
            Assessment:
            
            """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    system_msg
                ),
            ]
        )
        # model = ChatOpenAI(temperature=0)
        self.grader_runnable = (
               {"context": self.retriever, "QA": RunnablePassthrough()} | prompt | self.llm.bind(stop="Assessment") | StrOutputParser()
        )
        


    def _initialize_meta_agent(self) -> None:

        """ Initializes meta agent that will try to resolve any miscommunication between AI and Humn by providing Instruction for AI to follow.  """
 

        memory = ReadOnlySharedMemory(memory=self.interview_memory)

        # Whenver there's an error message, please use the "debug_error" tool.
        system_msg = """You are an instruction AI whose job is to assess the interview process and interviewer's questions.

        You are provided with their Current Conversation. If the current interview conversation is going well, you don't need to provide any Instruction. 
        
        If the current interview conversation can be improved, please help the interviewer improve the conversation by providing an Instruction. 
        
        If based on the length of conversation and number of questions asked, it's time to end the conversation, please tell interviewer to end the interview. """


        # template = system_msg + """Complete the objective as best you can. You have access to the following tools:

        # {tools}

        # Use the following format:

        # Question: Is the interview going well? Is it time to end the interview? Should the interviewer ask another type of question?
        # Thought: you should always think about what to do
        # Action: the action to take, should be based on Chat History below. If necessary, can be one of [{tool_names}] 
        # Action Input: the input to the action
        # Observation: the result of the action
        # ... (this Thought/Action/Action Input/Observation can repeat N times)
        # Thought: I now know the final answer
        # Final Answer: the final answer to the original input question

        # Begin!

        # Current Conversation: {chat_history}

        # Input: {input}
        # {agent_scratchpad}
        # """


        # prompt = CustomPromptTemplate(
        #     template=template,
        #     tools=self.interview_tools,
        #     # system_msg=system_msg,
        #     # This omits the `agent_scratchpad`, `tools`, and `tool_names` variables because those are generated dynamically
        #     # This includes the `intermediate_steps` variable because that is needed
        #     input_variables=["chat_history", "input", "intermediate_steps"],
        # )
        # output_parser = CustomOutputParser()
        # # LLM chain consisting of the LLM and a prompt
        # llm_chain = LLMChain(llm=self.llm, prompt=prompt)
        # tool_names = [tool.name for tool in self.interview_tools]

        # agent = LLMSingleActionAgent(
        #     llm_chain=llm_chain, 
        #     output_parser=output_parser,
        #     stop=["\nObservation:"], 
        #     allowed_tools=tool_names
        # )
        # self.meta_agent = AgentExecutor.from_agent_and_tools(agent=agent, tools=self.interview_tools, memory=memory, verbose=True)




    @retry(wait=wait_exponential(multiplier=1, min=2, max=6))
    def askInterviewer(self, user_input: str, callbacks=None,) -> str:

        """ Main function that processes all agents' conversation with user.
         
        Args:

            user_input (str): user question or response

        Keyword Args:

            callbacks: default is None

        Returns:

            response from AI interviewer and AI grader  
            
         """

        try:    
            # BELOW IS USED WITH CONVERSATIONAL RETRIEVAL AGENT (grader_agent and interviewer)
            # if (update_instruction):
            #     instruction = self.askMetaAgent()
            #     print(instruction) 
            # print(f"GRADER FEEDBACK: {grader_feedback}")
            # interviewer_response = self.interview_agent({"input":user_input}).get("output", "sorry, something happened, try again.")     
            if update_instructions:
                self.interviewer_assessment = self.askMetaAgent()
            print("INPUT",  user_input)
            print("ASSESSMENT", self.interviewer_assessment)
            # interviewer_response = self.interview_agent.invoke({"input":user_input, "interviewer_assessment":self.interviewer_assessment}).get("output", "sorry, something happened, try again.") 
            interviewer_response = self.interview_agent.invoke(
                    {"input": user_input},
                    config={"configurable": {"session_id": self.sessionId}},
                ).get("output", "Sorry, something happened, please try again.")
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
            print(f"ERROR HAS OCCURED IN ASKInterviewer: {e}")
            error_msg = str(e)
            # needs to get action and action input before error and add it to error message
            # if (update_instruction):
            #     query = f""""Debug the error message and provide Instruction for the AI assistant: {error_msg}
            #         """        
            #     instruction = self.askMetaAgent(query)
                # self.update_instructions(feedback)
            # if evaluate_result:
            #     self.update_meta_data(error_msg)
            raise e       

        # pickle memory (sanity check)
        # with open('conv_memory/' + userid + '.pickle', 'wb') as handle:
        #     pickle.dump(self.chat_history, handle, protocol=pickle.HIGHEST_PROTOCOL)
            # print(f"Sucessfully pickled conversation: {chat_history}")
        return interviewer_response
    

    
    @retry(wait=wait_exponential(multiplier=1, min=2, max=6))
    def askGrader(self, user_input:str, callbacks=None) -> str:

        try:    
            # BELOW IS USED WITH CONVERSATIONAL RETRIEVAL AGENT (grader_agent and interviewer)
            # if (update_instruction):
            #     instruction = self.askMetaAgent()
            #     print(instruction) 
            # grader_feedback = self.grader_agent({"input":user_input}).get("output", "")

            
            print("last_qa", last_qa)
            if last_qa:
                last_qa="interviewer question: {last_qa} / interviewee answer:I like dancing. "
                grader_feedback = self.grader_runnable.invoke(last_qa)
                print("GRADER FEEDBACK:", grader_feedback)
            # grader_feedback = await self.grader_agent.acall({"input":user_input}).get("output", "")
            # print(f"GRADER FEEDBACK: {grader_feedback}")       
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
            print(f"ERROR HAS OCCURED IN ASKGrader: {e}")
            error_msg = str(e)
            # needs to get action and action input before error and add it to error message
            # if (update_instruction):
            #     query = f""""Debug the error message and provide Instruction for the AI assistant: {error_msg}
            #         """        
            #     instruction = self.askMetaAgent(query)
                # self.update_instructions(feedback)
            # if evaluate_result:
            #     self.update_meta_data(error_msg)
            raise e       

        # pickle memory (sanity check)
        # with open('conv_memory/' + userid + '.pickle', 'wb') as handle:
        #     pickle.dump(self.chat_history, handle, protocol=pickle.HIGHEST_PROTOCOL)
            # print(f"Sucessfully pickled conversation: {chat_history}")
        return grader_feedback
    


    @retry(wait=wait_exponential(multiplier=1, min=2, max=6))
    def askMetaAgent(self, query="Update the Instruction please.") -> None:    

        """ Evaluates conversation's effectiveness between AI and Human. Outputs instructions for AI to follow. 
        
        Keyword Args:
        
            query (str): default is empty string
        
        """

        try: 
            feedback = self.meta_agent({"input":query}).get("output", "")
        except Exception as e:
            if type(e) == OutputParserException or type(e)==ValueError:
                feedback = str(e)
                feedback = feedback.removeprefix("Could not parse LLM output: `").removesuffix("`")
            else:
                feedback = ""
        return feedback

    # async def askAI_async(self, user_input: str, callbacks=None,) -> str:

    #     """ Main function that processes all agents' conversation with user.
         
    #     Args:

    #         userid (str): session id of user

    #         user_input (str): user question or response

    #     Keyword Args:

    #         callbacks: default is None

    #     Returns:

    #         Answer or response by AI (str)  
            
    #      """

    #     try:    
    #         # BELOW IS USED WITH CONVERSATIONAL RETRIEVAL AGENT (grader_agent and interviewer)
    #         grader_feedback = await self.grader_agent.acall({"input":user_input}).get("output", "")
    #         # print(f"GRADER FEEDBACK: {grader_feedback}")
    #         print(f"User Voice Input: {user_input}")
    #         response = await self.interview_agent.acall({"input":user_input})
    #         response = response.get("output", "sorry, something happened, try again.")        
    #     except Exception as e:
    #         print(f"ERROR HAS OCCURED IN ASKAI: {e}")
    #         error_msg = str(e)
    #         raise e       
    #     return response
    
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
    
    # def write_followup(self):
    #     if self.generated_dict:
    #         name = self.generated_dict.get("name", "")
    #         job = self.generated_dict.get("job", "")
    #         company=self.generated_dict.get("company", "")
    #         followup = "\n\nFOLLOW-UP EMAIL: \n"
    #         followup += get_completion(f""" Applicant {name} recently interviewed for a {job} role at {company}.
    #                                   Can you generate  a follow-up email that {name} could send to reinterate their interest and tactifully ask the status of the hiring process?""")
    #     else:
    #         followup = ""
    #     return followup
    

    def retrieve_feedback(self):

        """ Retrieves feedback from conversation. """

        # conversation = str(self.interview_memory.chat_memory.messages)
        end_path = os.path.join(log_path, f"{Path(self.logfile).stem}.txt")
        convert_to_txt(self.logfile, end_path)
        conversation = read_txt(end_path)
        feedback = "MOCK INTERVIEW FEEDBACK:\n"
        feedback += get_completion(f"Extract the positive and negative feedbacks from the following conversation and summarize the feedbacks into a few sentences: {conversation}")
        return feedback
    
    def output_printout(self, response):
        with open(log_path+"./feedback.txt", "w") as f:
            f.write(response)
        print(f"Successfully retrieved interview feedback summary: {response}")
        return "./feedback.txt"
    
    def generate_greeting(self, host):

        name = self.generated_dict.get("name", "")
        job = self.generated_dict.get("job", "")
        company=self.generated_dict.get("company", "")
        self.greeting = get_completion(f"""Your name is {host} and you are a job interviewer. Generate a greeting to an interviewee who's coming for a job interview, given the following information, if available:
                                    interviewee name: {name} /n
                                employer's company: {company} /n
                                interview job position: {job} /n
                                Please make your greeting about 2-3 sentences long. Remember to introduce yourself and an interview supervisor/grader named Ali.
                                YOu and Ali will be partnering together to help conduct the interview. 
                                If any part of the provided information is missing, skip it. 
                                    """)
        print(f"Successfully generated greeting: {self.greeting}")
        return self.greeting



    
    
        

    
        

