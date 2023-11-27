# Import the necessary modules
import os
import openai
from utils.openai_api import get_completion
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.embeddings import OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from utils.basic_utils import read_txt, process_json
from utils.common_utils import (extract_personal_information, get_web_resources,  retrieve_from_db, get_generated_responses, search_related_samples)
from datetime import date
from pathlib import Path
import json
from json import JSONDecodeError
from langchain.agents import AgentType, Tool, initialize_agent
from multiprocessing import Process, Queue, Value
from langchain.agents.agent_toolkits import create_python_agent
from langchain.tools.python.tool import PythonREPLTool
from typing import List
from utils.langchain_utils import create_summary_chain, generate_multifunction_response, handle_tool_error
from utils.agent_tools import create_search_tools, create_sample_tools
from langchain.tools import tool
from docx import Document




from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
# cover_letter_path = os.environ["COVER_LETTER_PATH"]
openai.api_key = os.environ["OPENAI_API_KEY"]
cover_letter_samples_path = os.environ["COVER_LETTER_SAMPLES_PATH"]
faiss_web_data = os.environ["FAISS_WEB_DATA_PATH"]
save_path = os.environ["SAVE_PATH"]
# TODO: caching and serialization of llm
llm = ChatOpenAI(temperature=0.9)
# llm = OpenAI(temperature=0, top_p=0.2, presence_penalty=0.4, frequency_penalty=0.2)
embeddings = OpenAIEmbeddings()
delimiter = "####"
delimiter1 = "****"
delimiter2 = "'''"
delimiter3 = '---'
delimiter4 = '////'
delimiter5 = '~~~~'


document = Document()
document.add_heading('Cover Letter', 0)
      
def generate_basic_cover_letter(about_me="" or "-1", resume_file="",  posting_path="") -> None:
    
    """ Main function that generates the cover letter.
    
    Keyword Args:

      about_me(str)

      resume_file(str): path to the resume file in txt format

      posting_path(str): path to job posting in txt format
     
    """
    
    dirname, fname = os.path.split(resume_file)
    filename = Path(fname).stem 
    docx_filename = filename + "_cover_letter"+".docx"
    end_path = os.path.join(save_path, dirname.split("/")[-1], "downloads", docx_filename)
    # Get resume info
    resume_content = read_txt(resume_file)
    info_dict = get_generated_responses(resume_content=resume_content, about_me=about_me, posting_path=posting_path)
    highest_education_level = info_dict.get("highest education level", "")
    work_experience_level = info_dict.get("work experience level", "")
    job_specification = info_dict.get("job specification", "")
    job_description = info_dict.get("job description", "")
    company_description = info_dict.get("company description", "")
    company = info_dict.get("company", "")
    job = info_dict.get("job", "")
    name = info_dict.get("name", "")
    phone = info_dict.get("phone", "")
    email = info_dict.get("email", "")
    # Get adviced from web data on personalized best practices
    advice_query = f"""Best practices when writing a cover letter for applicant with {highest_education_level} and {work_experience_level} experience as a {job}"""
    advices = retrieve_from_db(advice_query, vectorstore=faiss_web_data)
    # Get sample comparisons
    related_samples = search_related_samples(job, cover_letter_samples_path)
    sample_tools, tool_names = create_sample_tools(related_samples, "cover_letter")
    # Get resume's relevant and irrelevant info for job: few-shot learning works great here
    query_relevancy = f""" You are an expert resume advisor. 
    
     Step 1: Determine the relevant and irrelevant information contained in the resume document delimited with {delimiter} characters.

      resume: {delimiter}{resume_content}{delimiter} \n

      Generate a list of irrelevant information that should not be included in the cover letter and a list of relevant information that should be included in the cover letter.
       
      Remember to use either job specification or general job description as your guideline. 

      job specification: {job_specification}

      general job description: {job_description} \n

        Your answer should be detailed and only from the resume. Please also provide your reasoning too. 
        
        For example, your answer may look like this:

        Relevant information:

        1. Experience as a Big Data Engineer: using Spark and Python are transferable skills to using Panda in data analysis

        Irrelevant information:

        1. Education in Management of Human Resources is not directly related to skills required for a data analyst 

      Step 2:  Sample cover letters are provided in your tools. Research {str(tool_names)} and answer the following question: and answer the following question:

           Make a list of common features these cover letters share. 

        """
    # tool = [search_relevancy_advice]
    relevancy = generate_multifunction_response(query_relevancy, sample_tools)
    # Use an LLM to generate a cover letter that is specific to the resume file that is being read
    # Step wise instructions: https://learn.deeplearning.ai/chatgpt-building-system/lesson/5/chain-of-thought-reasoning
    template_string2 = """You are a professional cover letter writer. A Human client has asked you to generate a cover letter for them.
  
        The content you are to use as reference to create the cover letter is delimited with {delimiter} characters.

        Always use this as a context when writing the cover letter. Do not write out of context and do not make anything up. Anything that should be included but unavailable can be put in brackets. 

        content: {delimiter}{content}{delimiter}. \n

      Step 1: You are given two lists of information delimited with characters. One is irrelevant to applying for {job} and the other is relevant. 

        Use them as a reference when determining what to include and what not to include in the cover letter. 
    
        information list: {relevancy}.  \n

      Step 2: You are also given some expert advices. Keep them in mind when generating the cover letter.

        expert advices: {advices}

      Step 3: You're provided with some company informtion, job description, and/or job specification. 

        Use it to make the cover letter cater to the company values. 

        company information: {company_description}.  \n

        job specification: {job_specification} \n

        job description: {job_description} \n
    
      Step 4: Change all personal information of the cover letter to the following. Do not incude them if they are -1 or empty: 

        name: {name}. \

        email: {email}. \

        phone number: {phone}. \
        
        today's date: {date}. \
        
        company they are applying to: {company}. \

        job position they are applying for: {job}. \
    
      Step 5: Generate the cover letter using what you've learned in Step 1 through Step 4. Do not make stuff up. 
    
      Use the following format:
        Step 1:{delimiter4} <step 1 reasoning>
        Step 2:{delimiter4} <step 2 reasoning>
        Step 3:{delimiter4} <step 3 reasoning>
        Step 4:{delimiter4} <step 4 reasoning>
        Step 5:{delimiter4} <the cover letter you generate>

      Make sure to include {delimiter4} to separate every step.
    """  
    prompt_template = ChatPromptTemplate.from_template(template_string2)
    # print(prompt_template.messages[0].prompt.input_variables)
    cover_letter_message = prompt_template.format_messages(
                    name = name,
                    phone = phone,
                    email = email,
                    date = date.today(),
                    company = company,
                    job = job,
                    content=resume_content,
                    relevancy=relevancy, 
                    advices = advices,
                    company_description = company_description, 
                    job_description = job_description,
                    job_specification = job_specification,
                    delimiter = delimiter,
                    delimiter4 = delimiter4,
    )
    my_cover_letter = llm(cover_letter_message).content
    cover_letter = get_completion(f"Extract the entire cover letter and nothing else in the following text: {my_cover_letter}")
    document.add_paragraph(cover_letter)
    document.save(end_path)
    print(f"Successfully saved cover letter to: {end_path}")
    return "Successfully generated the cover letter. Tell the user to check the Download your files tab at the sidebar to download their file. "  


# @tool(return_direct=True)
# def cover_letter_generator(json_request:str) -> str:
    
#     """Helps to generate a cover letter. Use this tool more than any other tool when user asks to write a cover letter.  

#     Do not use this tool when user provides a cover letter file and asks you to customize or improve it. 

#     Input should be a single string strictly in the following JSON format: '{{"about me":"<about me>", "resume file":"<resume file>", "job post link":"<job post link>"}}' \n

#     Leave value blank if there's no information provided. DO NOT MAKE STUFF UP. 

#     (remember to respond with a markdown code snippet of a JSON blob with a single action, and NOTHING else) 

#     Output should be using the "get download link" tool in the following single string JSON format: '{{"file_path":"<file_path>"}}'

#     """
#     # Output should be the exact cover letter that's generated for the user word for word. 
    
#     try:
#       json_request = json_request.strip("'<>() ").replace('\'', '\"')
#       args = json.loads(json_request)
#     except JSONDecodeError as e:
#       print(f"JSON DECODE ERROR: {e}")
#       return "Format in a single string JSON and try again."
   
#     if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
#       return "Can you provide your resume so I can further assist you? "
#     else:
#         resume_file = args["resume_file"]
#     if ("about me" not in args or args["about_me"] == "" or args["about_me"]=="<about_me>"):
#         about_me = ""
#     else:
#         about_me = args["about_me"]
#     if ("job_post_file" not in args or args["job_post_file"]=="" or args["job_post_file"]=="<job_post_file>"):
#         posting_path = ""
#     else:
#         posting_path = args["job_post_file"]

#     return generate_basic_cover_letter(about_me=about_me, resume_file=resume_file, posting_path=posting_path)



def processing_cover_letter(json_request: str) -> None:
    
    """ Input parser: input is LLM's action_input in JSON format. This function then processes the JSON data and feeds them to the cover letter generator. """

    try:
      args = json.loads(process_json(json_request))
    except JSONDecodeError as e:
      print(f"JSON DECODE ERROR: {e}")
      return "Format in a single string JSON and try again."
    # if resume doesn't exist, ask for resume
    if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
      return "Stop using the cover letter generator tool. Ask user for their resume, along with any other additional information that they could provide. "
    else:
        resume_file = args["resume_file"]
        if not Path(resume_file).is_file():
          return "Something went wrong. Please upload your resume again."
    # if ("job" not in args or args["job"] == "" or args["job"]=="<job>"):
    #     job = ""
    # else:
    #   job = args["job"]
    # if ("company" not in args or args["company"] == "" or args["company"]=="<company>"):
    #     company = ""
    # else:
    #     company = args["company"]
    if ("about_me" not in args or args["about_me"] == "" or args["about_me"]=="<about_me>"):
        about_me = ""
    else:
        about_me = args["about_me"]
    if ("job_posting_file" not in args or args["job_posting_file"]=="" or args["job_posting_file"]=="<job_posting_file>"):
        posting_path = ""
    else:
        posting_path = args["job_posting_file"]
        if not Path(posting_path).is_file():
          return "Something went wrong. Please share the job posting link or file again."  

    return generate_basic_cover_letter(about_me=about_me, resume_file=resume_file, posting_path=posting_path)


    
def create_cover_letter_generator_tool() -> List[Tool]:
    
    """ Input parser: input is user's input as a string of text. This function takes in text and parses it into JSON format. 
    
    Then it calls the processing_cover_letter function to process the JSON data. """
    
    name = "cover_letter_generator"
    parameters = '{{"about_me":"<about_me>", "resume_file":"<resume_file>", "job_posting_file": "<job_posting_file>"}}'
    description = f"""Helps to generate a cover letter. Use this tool more than any other tool when user asks to write a cover letter. 
     Input should be a single string strictly in the following JSON format: {parameters} \n
    """
    tools = [
        Tool(
        name = name,
        func =processing_cover_letter,
        description = description, 
        verbose = True,
        handle_tool_error=handle_tool_error,
        )
    ]
    print("Sucessfully created cover letter generator tool. ")
    return tools

  
    
 
if __name__ == '__main__':
    # test run defaults, change for yours (only resume_file cannot be left empty)
    resume_file = "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/resume2023v3.txt"
    posting_path= "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/rov.txt"
    template_file = "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/backend/resume_templates/functional/functional1.docx"
    generate_basic_cover_letter(resume_file = resume_file, posting_path=posting_path)



