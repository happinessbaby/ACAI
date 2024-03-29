import os
import openai
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import CommaSeparatedListOutputParser
from langchain.prompts import PromptTemplate
from langchain_experimental.smart_llm import SmartLLMChain
from langchain.agents import AgentType, Tool, initialize_agent, create_json_agent
from utils.basic_utils import read_txt, memoized, process_json
from utils.common_utils import (get_web_resources, retrieve_from_db,  get_generated_responses,calculate_graduation_years, extract_posting_keywords, extract_education_information, calculate_work_experience_level,extract_pursuit_information,
                            search_related_samples,  extract_personal_information)
from utils.langchain_utils import create_mapreduce_chain, create_summary_chain, generate_multifunction_response, create_refine_chain, handle_tool_error
from utils.agent_tools import create_search_tools, create_sample_tools
from pathlib import Path
import json
from json import JSONDecodeError
from multiprocessing import Process, Queue, Value
from langchain.tools.json.tool import JsonSpec
from typing import Dict, List, Optional, Union
from langchain.document_loaders import BSHTMLLoader
from langchain.tools import tool
from langchain.chains import LLMChain
import docx
import uuid
from docxtpl import DocxTemplate	
from docx import Document
from docx.shared import Inches
import boto3
from dotenv import load_dotenv, find_dotenv


_ = load_dotenv(find_dotenv()) # read local .env file
openai.api_key = os.environ["OPENAI_API_KEY"]
resume_samples_path = os.environ["RESUME_SAMPLES_PATH"]
faiss_web_data = os.environ["FAISS_WEB_DATA_PATH"]
STORAGE = os.environ["STORAGE"]
local_save_path = os.environ["CHAT_PATH"]
# TODO: caching and serialization of llm
llm = ChatOpenAI(temperature=0.9)
embeddings = OpenAIEmbeddings()
# TODO: save these delimiters in json file to be loaded from .env
delimiter = "####"
delimiter1 = "````"
delimiter2 = "////"
delimiter3 = "<<<<"
delimiter4 = "****"

if STORAGE=="S3":
    bucket_name = os.envrion["BUCKET_NAME"]
    s3_save_path = os.environ["S3_CHAT_PATH"]
    session = boto3.Session(         
                    aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"],
                    aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"],
                )
    s3 = session.client('s3')
else:
    bucket_name=None
    s3=None

def evaluate_resume(about_me="", resume_file = "", posting_path="") -> str:

    document = Document()
    document.add_heading('Resume Evaluation', 0)
    dirname, fname = os.path.split(resume_file)
    filename = Path(fname).stem 
    docx_filename = filename + "_evaluation"+".docx"
    local_end_path = os.path.join(local_save_path, dirname.split("/")[-1], "downloads", docx_filename)
    resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    info_dict=get_generated_responses(resume_content=resume_content, posting_path=posting_path, about_me=about_me)
    work_experience_level = info_dict.get("work experience level", "")
    graduation_year = info_dict.get("graduation year", -1)
    years_since_graduation = calculate_graduation_years(graduation_year)
    degree = info_dict.get("degree", -1)
    study = info_dict.get("study", -1)
    job = info_dict.get("job", -1)
    company = info_dict.get("company", -1)
    field_names = info_dict.get("field names", "")

    if work_experience_level=="no experience" or work_experience_level=="entry level" and years_since_graduation<2:
        resume_type = "student"
    elif work_experience_level=="no experience" or work_experience_level=="entry level" and years_since_graduation>=2:
        resume_type =  "functional"
    else:
        resume_type = "chronological"

  #TODO: This query should make suggestions on what type of resume they should write and how to improve the overall impression
    query_overall = f"""Your task is to provide an assessment of a resume delimited by {delimiter} characters.

    resume: {delimiter}{resume_content}{delimiter} \n

    The applicant's work experience level as a {job} is {work_experience_level}.

    Furthermore, it has been {years_since_graduation} years since the applicant graduated with a highest level of education {degree} in {study}. 

    Research the resume closely and assess if it is written as a {resume_type} resume. 

    """
    # tools = create_search_tools("google", 3)
    # response = generate_multifunction_response(query_overall, tools)
    prompt = PromptTemplate.from_template(query_overall)
    chain = SmartLLMChain(llm=llm, prompt=prompt, n_ideas=3, verbose=True)
    response = chain.run({})

    document.add_heading(f"Overall Asessment", level=1)
    document.add_paragraph(response)
    document.add_page_break()
    document.save(local_end_path)
    # write_to_docx_template(doc, personal_info, personal_info_dict, docx_filename)

    # Note: document comparison benefits from a clear and simple prompt
    related_samples = search_related_samples(job, resume_samples_path)
    sample_tools, tool_names = create_sample_tools(related_samples, "resume")

    # # process all fields in parallel
    processes = [Process(target = evaluate_resume_fields, args = (info_dict, field, info_dict.get(field, ""),  sample_tools)) for field in field_names]
    for p in processes:
       p.start()
    for p in processes:
       p.join()

    document.add_heading(f"Detailed Evaluation", level=1)
    document.add_paragraph()
    if STORAGE=="S3":
        s3_end_path = os.path.join(s3_save_path, dirname.split("/")[-1], "downloads", docx_filename)
        s3.upload_file(local_end_path, bucket_name, s3_end_path)
    return "Successfully evaluated resume. Tell the user to check the Download your files tab at the sidebar to download their file."



def evaluate_resume_fields(generated_response: Dict[str, str], field: str, field_content: str, tools: List[Tool]) -> None:

    print(f"CURRENT FIELD IS: {field}")
    if field_content!="":
        job = generated_response.get("job", "")
        company_description = generated_response.get("company description", "")
        job_specification = generated_response.get("job specification", "")
        job_description = generated_response.get("job description", "")
        highest_education_level = generated_response.get("highest education level", "")
        work_experience_level = generated_response.get("work experience level", "")
        # education_level = generated_response.get("education", "")

        advice_query =  f"""how to make resume field {field} ATS-friendly? No formatting advices."""
        advice1 = retrieve_from_db(advice_query, vectorstore=faiss_web_data)
        advice_query = f"""what to include in {field} of resume for {highest_education_level} and {work_experience_level} as a {job}"""
        advice2 = retrieve_from_db(advice_query, vectorstore=faiss_web_data)

        query_evaluation = f"""  You are an expert resume field advisor. 

        Generate a list of missing, irrelevant, and not ATS-friendly information in the resume field content. 
        
        Remember to use either job specification or general job description as your guideline along with the expert advice.

        field name: {field}

        field content: {field_content}\n

        job specification: {job_specification}\n

        general job description: {job_description} \n

        expert advice: {advice2} + "\n" + {advice1}

        Your answer should be detailed and only from the field content. Please also provide your reasoning too as in the following examples:

                Missing or Irrelevant Field Content for Work Experience:

                1. Quantative achievement is missing: no measurable metrics or KPIs to highlight any past achievements. 

                2. Front desk receptionist is irrelevant: Experience as a front desk receptionist is not directly related to the role of a data analyst

                3. Date formatting is not ATS-friendly: an ATS-friendly way to write dates is for example, 01/2001 or January 2001

        The above is just an example for your reference. Do not let it be your answer. 
        
        Please ignore all formatting advices as formatting should not be part of the assessment.

        Use your tools if you need to reference other resume.

        """

        evaluation = generate_multifunction_response(query_evaluation, tools)

        with open(f"{field}_evaluation.txt", "x") as f:
           f.write(evaluation)

@memoized
def research_resume_type(resume_file: str, posting_path: str)-> str:
    
    """ Researches the type of resume most suitable for the applicant. 
    
        Args:
        
            resume_file(str): path of the resume

            posting_path(str): path of the job posting

        Returns:
        
            type of resume: functional, chronological, or student
            
    """

    resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    posting_content = read_txt(posting_path, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    if posting_content!="":
        job = extract_pursuit_information(posting_content).get("job", "")
    else:
        job = extract_pursuit_information(resume_content).get("job", "")
    work_experience_level = calculate_work_experience_level(resume_content, job)
    education_info_dict = extract_education_information(resume_content)
    graduation_year = education_info_dict.get("graduation year", "")
    years_since_graduation = calculate_graduation_years(graduation_year)
    if (work_experience_level=="no experience" or work_experience_level=="entry level") and (years_since_graduation<2 or years_since_graduation is None):
        resume_type = "student"
        print("RESUME TYPE: STUDENT")
    elif (work_experience_level=="no experience" or work_experience_level=="entry level") and (years_since_graduation>=2 or years_since_graduation is None):
        resume_type = "functional"
        print("RESUME TYPE: FUNCTIONAL")
    else:
        resume_type = "chronological"
        print("RESUME TYPE: CHRONOLOGICAL")
    return resume_type


def reformat_functional_resume(resume_file="", posting_path="", template_file="") -> None:

    dirname, fname = os.path.split(resume_file)
    filename = Path(fname).stem 
    docx_filename = filename + "_reformat"+".docx"
    local_end_path = os.path.join(local_save_path, dirname.split("/")[-1], "downloads", docx_filename)
    resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    functional_doc_template = DocxTemplate(template_file)
    info_dict = get_generated_responses(resume_content=resume_content, posting_path=posting_path)
    func = lambda key, default: default if info_dict[key]==-1 else info_dict[key]
    personal_context = {
        "NAME": func("name", "YOUR NAME"),
        "ADDRESS": func("address", "YOUR ADDRESS"),
        "PHONE": func("phone", "YOUR PHONE"),
        "EMAIL": func("email", "YOUR EMAIL"),
        "LINKEDIN": func("linkedin", "YOUR LINKEDIN URL"),
        "WEBSITE": func("website", "WEBSITE"),
    }
    #TODO: save the context dictionary somewhere
    context_keys = ["SUMMARY", "WORK_HISTORY", "PROFESSIONAL_ACCOMPLISHMENTS", "EDUCATION", "SKILLS", "CERTIFICATION"]
    info_dict_keys = ["summary or objective", "work experience", "professional accomplishment", "education", "skills", "certification"]
    context_dict = dict(zip(context_keys, info_dict_keys))
    context = {key: None for key in context_keys}
    #TODO, this tool below is temporary
    tools = create_search_tools("google", 1)
    for key, value in context_dict.items():
        content = info_dict.get(value, "")
        if key == "SUMMARY":
            job_description = info_dict.get("job description", "")
            job_specification = info_dict.get("job specification", "")
            skills = info_dict.get("skills", "")
            query = f""" Your task is to improve or write the summary section of the functional resume in less than 50 words.
            If you are provided with an existing summary section, use it as your context and build on top of it.    
            Otherwise, refer to the job specification or job description, skills, whichever is available and incorportate relevant soft skill and hard skills into the summary.
            objective section: {content} \n
            skills: {skills} \n
            job description: {job_description} \n
            job specification: {job_specification} \n
            Here are some example summary:
            1. Organized and motivated employee with superior [skill] and [skill]. Seeking to join [company] as a [position] to help enhance [function]. \
            2. Certified [position] looking to join [company] as a part of the [department] team. Hardworking individual with [skill], [skill], and [skill]. \
            3. Detail-oriented individual seeking to help [company] achieve its goals as a [position]. Excellent at [skill] and dedicated to delivering top-quality [function]. \
            4. [Position] certified in [skill] and [skill], looking to help [company] increase [goal metric]. Excellent [position] who can collaborate with large teams to [achieve goal]. \
            PLEASE WRITE IN LESS THAN 50 WORDS AND OUTPUT THE SUMMARY SECTION AS YOUR FINAL ANSWER. DO NOT OUTPUT ANYTHING ELSE. 
            """
            content = generate_multifunction_response(query, tools)
        elif key=="PROFESSIONAL_ACCOMPLISHMENTS":     
            keywords = info_dict.get("job keywords", "")
            query = """ Your task is to pick at least 3 hard skills from the following available skillset. If there are no hard skills, pick the soft skills.
             skillset: {keywords}.    
             The criteria you use to pick the skills is based on if the skills exist or can be inferred in the resume delimited with {delimiter} characters below.
             resume: {delimiter}{content}{delimiter} \n
            {format_instructions}
            """
            output_parser = CommaSeparatedListOutputParser()
            format_instructions = output_parser.get_format_instructions()
            prompt = PromptTemplate(
                template=query,
                input_variables=["keywords", "delimiter", "content"],
                partial_variables={"format_instructions": format_instructions}
            )
            chain = LLMChain(llm=llm, prompt=prompt, output_key="ats")
            skills = chain.run({"keywords": keywords, "delimiter":delimiter, "content":content})
            query = f"""Your task is to catgeorize the professional accomplishments delimited with {delimiter} characters under certain skills. 
            Categorize content of the professional accomlishments into each skill. For example, your output should be formated as the following:
            SKill1:

                - Examples of projects or situations that utilized this skill
                - Measurable results and accomplishments

            skills: {skills}
            professional accomplishments: {delimiter}{content}{delimiter} \n
            Please start each bullet point with a strong action verb.
            Please make each bullet point unique by putting it under one skill only, which should be the best fit for that skill. 
            If professional accomplishments do not exist, please output an example. 
            """
            content = generate_multifunction_response(query, tools)
        context[key] = content
    context.update(personal_context)
    functional_doc_template.render(context)
    functional_doc_template.save(local_end_path) 
    if STORAGE=="S3":
        s3_end_path = os.path.join(s3_save_path, dirname.split("/")[-1], "downloads", docx_filename)
        s3.upload_file(local_end_path, bucket_name, s3_end_path)
    return "Successfully reformated the resume using a new template. Tell the user to check the Download your files tab at the sidebar to download their file. "



def reformat_chronological_resume(resume_file="", posting_path="", template_file="") -> None:

    dirname, fname = os.path.split(resume_file)
    filename = Path(fname).stem 
    docx_filename = filename + "_reformat"+".docx"
    local_end_path = os.path.join(local_save_path, dirname.split("/")[-1], "downloads", docx_filename)
    resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    chronological_resume_template = DocxTemplate(template_file)
    info_dict = get_generated_responses(resume_content=resume_content, posting_path=posting_path)
    func = lambda key, default: default if info_dict[key]==-1 else info_dict[key]
    personal_context = {
        "NAME": func("name", "YOUR NAME"),
        "ADDRESS": func("address", "YOUR ADDRESS"),
        "PHONE": func("phone", "YOUR PHONE"),
        "EMAIL": func("email", "YOUR EMAIL"),
        "LINKEDIN": func("linkedin", "YOUR LINKEDIN URL"),
        "WEBSITE": func("website", "WEBSITE"),
    }
    # TODO: add awards and honors or professional accomplishments
    context_keys = ["SUMMARY", "PROFESSIONAL_EXPERIENCE", "RELEVANT_SKILLS", "EDUCATION", "HOBBIES", "CERTIFICATION"]
    info_dict_keys = ["summary or objective", "work experience", "skills", "education", "hobbies", "certification"]
    context_dict = dict(zip(context_keys, info_dict_keys))
    context = {key: None for key in context_keys}
    tools = create_search_tools("google", 1)
    for key, value in context_dict.items():
        content = info_dict.get(value, "")
        if key == "SUMMARY":
            work_experience = info_dict.get("work experience", "")
            query = f""" Your task is to improve or rewrite the summary section of a chronological resume.

            If you are provided with an existing summary section, use it as your context and build on top of it, if needed.
              
            Otherwise, refer to the work experience, if available. 

            summary section: {content}

            work experience: {work_experience}

            Please write in fewer than five sentences the summary section of the chronological resume with the information above.

            If the summary already is already filled with relevant work experience, you can output the original summary section. 
            
            Otherwise, incorporate relevant work experience into the summary section. 

            Here are some examples: 

            Experienced [position] looking to help [company] provide excellent customer service. Over [number] years of experience at [company], demonstrating excellent [skill], [skill], and [skill]. 

            [Position] with [number] years of experience looking to help [company] improve its [function]. Diligent and detail-oriented professional with extensive experience with [hard skill]. 

            Hardworking [position] with [number] years of experience at a [type of environment]. Seeking to bring [skills] and experience to benefit [company] in the [department].

            Dedicated [position] with over [number] years of experience looking to move into [new field]. [Graduate degree title] from [school name]. Excellent [skill], [skill], and [skill].

            PLEASE WRITE IN LESS THAN FIVE SENTENCES THE SUMMARY SECTION OF THE RESUME AND OUTPUT IT AS YOUR FINAL ANSWER. DO NOT OUTPUT ANYTHING ELSE. 

            """        
            content = generate_multifunction_response(query, tools)
        elif key=="RELEVANT_SKILLS":
            keywords = info_dict.get("job keywords", "")
            job_description = info_dict.get("job description", "")
            job_specification = info_dict.get("job specification", "") 
            skills = info_dict.get("skills", "")
            query = f""" 

                Your tasks is to improve the Skills section of the resume. You are provided with a job description or job specificaiton, whichever is available.

                If you are provided with an existing Skills section, use it as your context and build on top of it, if needed.

                You are also provided with a list of important keywords that are in the job posting. Some of them should be included also. 

                skills section: {skills} \n

                job description: {job_description} \n
                
                job specification: {job_specification} \n

                important keywords: {keywords} \n
 
                If the skills section exist, add to it relevant skills and remove from it irrelevant skills.

                Otherwise, if the skills section is already well-written, output the original skills section. 

                """
            content = generate_multifunction_response(query, tools)
        context[key] = content
    context.update(personal_context)
    chronological_resume_template.render(context)
    chronological_resume_template.save(local_end_path) 
    if STORAGE=="S3":
        s3_end_path = os.path.join(s3_save_path, dirname.split("/")[-1], "downloads", docx_filename)
        s3.upload_file(local_end_path, bucket_name, s3_end_path)
    return "Successfully reformated the resume using a new template. Tell the user to check the Download your files tab at the sidebar to download their file. "
 


def reformat_student_resume(resume_file="", posting_path="", template_file="") -> None:

    dirname, fname = os.path.split(resume_file)
    filename = Path(fname).stem 
    docx_filename = filename + "_reformat"+".docx"
    local_end_path = os.path.join(local_save_path, dirname.split("/")[-1], "downloads", docx_filename)
    resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    chronological_resume_template = DocxTemplate(template_file)
    info_dict = get_generated_responses(resume_content=resume_content, posting_path=posting_path)
    func = lambda key, default: default if info_dict[key]==-1 else info_dict[key]
    personal_context = {
        "NAME": func("name", "YOUR NAME"),
        "ADDRESS": func("address", "YOUR ADDRESS"),
        "PHONE": func("phone", "YOUR PHONE"),
        "EMAIL": func("email", "YOUR EMAIL"),
        "LINKEDIN": func("linkedin", "YOUR LINKEDIN URL"),
        "WEBSITE": func("website", "WEBSITE"),
    }
    #TODO: add volunteer experience
    context_keys = ["OBJECTIVE", "EDUCATION", "AWARDS_HONORS", "SKILLS", "WORK_EXPERIENCE"]
    info_dict_keys = ["summary or objective", "education", "awards and honors", "skills", "work experience"]
    context_dict = dict(zip(context_keys, info_dict_keys))
    context = {key: None for key in context_keys}
    for key, value in context_dict.items():
        if key == "OBJECTIVE":
            job_description = info_dict.get("job description", "")
            job_specification = info_dict.get("job specification", "")
            skills = info_dict.get("skills", "")
            query = """Detail-oriented college student at [school] with [GPA]. Graduating in [year] with [degree title]. Looking to use [skills] as a [position] for [company]. 

                High school student with proven [skills] looking for a [position] at [company]. Proven [skill] as [extracurricular position]. Wishing to use [skills] to [achieve goals].

                Hardworking recent graduate in [degree] from [school]. Excellent [skills] and [skills]. Experienced in [function], function, and [function] at [company].

                [Degree] candidate in [subject] from [school] seeking a [position] at [company]. Experience in [function]. Exceptional [skills], [skills], and [skills].

                """
        content = info_dict.get(value, "")
        context[key] = content
    context.update(personal_context)
    chronological_resume_template.render(context)
    chronological_resume_template.save(local_end_path) 
    if STORAGE=="S3":
        s3_end_path = os.path.join(s3_save_path, dirname.split("/")[-1], "downloads", docx_filename)
        s3.upload_file(local_end_path, bucket_name, s3_end_path)
    return "Successfully reformated the resume using a new template. Tell the user to check the Download your files tab at the sidebar to download their file. "  


# @tool("resume evaluator")
# def resume_evaluator_tool(resume_file: str, job: Optional[str]="", company: Optional[str]="", job_post_link: Optional[str]="") -> str:

#    """Evaluate a resume when provided with a resume file, job, company, and/or job post link.
#         Note only the resume file is necessary. The rest are optional.
#         Use this tool more than any other tool when user asks to evaluate, review, help with a resume. """

#    return evaluate_resume(my_job_title=job, company=company, resume_file=resume_file, posting_path=job_post_link)
      



def processing_resume(json_request: str) -> None:

    """ Input parser: input is LLM's action_input in JSON format. This function then processes the JSON data and feeds them to the resume evaluator. """

    try:
      args = json.loads(process_json(json_request))
    except JSONDecodeError as e:
      print(f"JSON DECODER ERROR: {e}")
      return "Reformat in JSON and try again."
    if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
      return "Stop using the resume evaluator tool. Ask user for their resume."
    else:
        resume_file = args["resume_file"]
    if ("about_me" not in args or args["about_me"] == "" or args["about_me"]=="<about_me>"):
        about_me = ""
    else:
        about_me = args["about_me"]
    if ("job_posting_file" not in args or args["job_posting_file"]=="" or args["job_posting_file"]=="<job_posting_file>"):
        posting_path = ""
    else:
        posting_path = args["job_posting_file"]   
    return evaluate_resume(about_me=about_me, resume_file=resume_file, posting_path=posting_path)



def processing_template(json_request: str) -> None:

    """ Input parser: input is LLM's action_input in JSON format. This function then processes the JSON data and feeds them to the resume reformatters. """

    try:
        args = json.loads(process_json(json_request))
    except JSONDecodeError as e:
      print(f"JSON DECODER ERROR: {e}")
      return "Reformat in JSON and try again."
    if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
      return "Stop using the resume_writer tool. Ask user for their resume file and an optional job post link."
    else:
        resume_file = args["resume_file"]
    if ("resume_template_file" not in args or args["resume_template_file"]=="" or args["resume_template_file"]=="<resume_template_file>"):
      return "Stop using the resume_writer tool. Use the rewrite_using_new_template tool instead."
    else:
        resume_template = args["resume_template_file"]
    if ("job_posting_file" not in args or args["job_posting_file"]=="" or args["job_posting_file"]=="<job_posting_file>"):
        posting_path = ""
    else:
        posting_path = args["job_posting_file"]
    # get resume type from directory name
    resume_type = resume_template.split("/")[-2]
    if resume_type=="functional":
        return reformat_functional_resume(resume_file=resume_file, posting_path=posting_path, template_file=resume_template)
    elif resume_type=="chronological":
        return reformat_chronological_resume(resume_file=resume_file, posting_path=posting_path, template_file=resume_template)
    elif resume_type=="student":
        return reformat_student_resume(resume_file=resume_file, posting_path=posting_path, template_file=resume_template)
    



@tool("rewrite_using_new_template", return_direct=True)
def redesign_resume_template(json_request:str):

    """Creates a resume_template for rewriting of resume. Use this tool more than any other tool when user asks to reformat, redesign, or rewrite their resume according to a particular type or template.
    Do not use this tool to evaluate or customize and tailor resume content. Do not use this tool if resume_template_file is provided in the prompt. 
    When there is resume_template_file in the prompt, use the "resume_writer" tool instead.
    Input should be a single string strictly in the followiwng JSON format: '{{"resume_file":"<resume_file>", "job_posting_file":"<job_posting_file>"}}' \n
    Output should be exactly one of the following words and nothing else: student, chronological, or functional"""

    try:
        args = json.loads(process_json(json_request))
    except JSONDecodeError as e:
      print(f"JSON DECODER ERROR: {e}")
      return "Reformat in JSON and try again."
    # if resume doesn't exist, ask for resume
    if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
      return "Can you provide your resume file and an optional job post link? "
    else:
        resume_file = args["resume_file"]
    if ("job_posting_file" not in args or args["job_posting_file"]=="" or args["job_posting_file"]=="<job_posting_file>"):
        posting_path = ""
    else:
        posting_path = args["job_posting_file"]
    resume_type= research_resume_type(resume_file, posting_path)
    return resume_type


def create_resume_evaluator_tool() -> List[Tool]:

    """ Input parser: input is user's input as a string of text. This function takes in text and parses it into JSON format. 
    
    Then it calls the processing_resume function to process the JSON data. """

    name = "resume_evaluator"
    parameters = '{{"about_me":"<about_me>", "resume_file":"<resume_file>", "job_posting_file":"<job_posting_file>"}}' 
    description = f"""Evaluate a resume. Use this tool more than any other tool when user asks to evaluate or improves a resume. 
    Do not use this tool is asked to customize or tailr the resume. You should use the "resume_customize_writer" instead.
    Input should be a single string strictly in the following JSON format: {parameters} \n
    """
    tools = [
        Tool(
        name = name,
        func = processing_resume,
        description = description,
        verbose = False,
        handle_tool_error=handle_tool_error,
        )
    ]
    print("Succesfully created resume evaluator tool.")
    return tools

def create_resume_rewriter_tool() -> List[Tool]:

    name = "resume_writer"
    parameters = '{{"resume_file":"<resume_file>", "job_posting_file":"<job_posting_file>", "resume_template_file":"<resume_template_file>"}}'
    description = f""" Rewrites a resume from a given resume_template_file. 
    Do not use this tool to evaluate or customize and tailor resume content. Use this tool only if resume_template_file is available.
    If resume_template_file is not available, use the rewrite_using_new_template tool first, which will create a resume_template_file. 
    DO NOT ASK USER FOR A RESUME_TEMPLATE. It should be generated from the rewrite_using_new_template tool.
    Input should be a single string strictly in the followiwng JSON format: {parameters} \n
    """
    tools = [
        Tool(
        name = name,
        func = processing_template,
        description = description,
        verbose = False,
        handle_tool_error=handle_tool_error,
        )
    ]
    print("Succesfully created resume writer tool.")
    return tools



if __name__ == '__main__':
    resume_file = "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/resume2023v4.txt"
    posting_path= "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/rov.txt"
    template_file = "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/backend/resume_templates/functional/functional1.docx"
    reformat_functional_resume(resume_file=resume_file, posting_path=posting_path, template_file=template_file)
    # evaluate_resume(my_job_title =my_job_title, company = company, resume_file=my_resume_file, posting_path = job_posting)
    # evaluate_resume(resume_file=my_resume_file)


