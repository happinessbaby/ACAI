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
from utils.openai_api import get_completion
from utils.basic_utils import read_txt, memoized, process_json, count_pages, count_length
from utils.common_utils import (get_web_resources, retrieve_from_db,calculate_graduation_years, extract_posting_keywords, extract_education_information, extract_pursuit_information,
                            search_related_samples,  extract_personal_information,retrieve_or_create_resume_info, retrieve_or_create_job_posting_info, research_relevancy_in_resume, extract_similar_jobs, research_skills)
from utils.langchain_utils import create_mapreduce_chain, create_summary_chain, generate_multifunction_response, create_refine_chain, handle_tool_error, create_smartllm_chain
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
eval_dict=None

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

# def rework_resume(about_job="", resume_file = "", posting_path="", evaluate=False, reformat=False, tailor=False, template_file=""):

#     #NOTE: STEP 1: EVALUATE, STEP 2: REFORMAT, STEP 3: TAILOR

#     if evaluate:
#         eval_dict = evaluate_resume(about_job=about_job, resume_file=resume_file, posting_path=posting_path)
#     if reformat:
#         ideal_type = eval_dict["ideal type"] if eval_dict else research_resume_type()
#         if ideal_type=="chronological":
#             reformat_chronological_resume(resume_file, template_file)
#     if tailor:
#         tailor_resume(resume_file, posting_path, about_job)


def evaluate_resume(resume_file = "", resume_dict={}, job_posting_dict={}, ) -> Dict[str, str]:

    print("start evaluating...")
    evaluation_dict = {"word_count": 0, "page_number":0, "ideal_type": "", "type_analysis": "", "overall_impression": "", "in_depth_view": ""}
    resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    if job_posting_dict:
        pursuit_job=job_posting_dict["job"]
    else:
        pursuit_job=resume_dict["pursuit_job"]
    # Evaluate resume length
    word_count = count_length(resume_file)
    evaluation_dict.update({"word_count": word_count})
    page_num = count_pages(resume_file)
    evaluation_dict.update({"page_number": page_num})
    # Research and analyze resume type
    ideal_type = research_resume_type(resume_dict=resume_dict, job_posting_dict=job_posting_dict, )
    evaluation_dict.update({"ideal_type": ideal_type})
    type_analysis= analyze_resume_type(resume_content, ideal_type)
    evaluation_dict.update({"type_analysis": type_analysis})
    # Generate overall impression
    overall_impression = analyze_resume_overall(resume_content,  pursuit_job)
    # # Evaluates specific field  content
    # resume_fields = resume_dict["resume fields"]
    # evaluation_dict.update({"overall_impression": overall_impression})
    # if resume_fields["work experience"]!=-1:
    #     evaluted_work= analyze_field_content(resume_dict["jobs"])
    # if resume_fields["projects"]!=-1:
    #     evaluted_project = analyze_field_content(resume_dict["projects"])
    # if resume_fields["professional accomplishment"]!=-1:
    #     evaluted_accomplishment = analyze_field_content(resume_dict["professional accomplishment"])
    # in_depth_view = ""
    return evaluation_dict



def analyze_field_content(field_content, field_type):

    """ Evalutes the bullet points of experience, accomplishments, and projects section of resume"""
    if field_type=="work experience" or field_type=="projects" or field_type=="professional accomplishment":
        star_prompt = f""" Your task is to check a resume field content you are provided with and assess it based on some guidelines.
        
        Guildeline: Start with the POWER verb, include a description of the actions, 
        use a comma and a verb ending in -ing to highlight transferable skills and/or measurable results, best if include measurable metrics.
        
        Example: Managed 10 employees by supervising daily operations, scheduling shifts, and holding weekdly staff meetings with strong leadership skills and empath, 
        resulting in a productive team that collectively won the company's "Most Efficient Department Award" two years in a row
         
        field_content: {field_content} """


def analyze_resume_overall(resume_content, job):

    """Analyzes overall resume by comparing to other samples"""

    # Note: document comparison benefits from a clear and simple prompt
    query_comparison = f"""Your task is to compare a candidate's resume to other sample resume and assess the quality of it in terms of how well-written it is compared to the sample resume.
    
    All the sample resume can be accesssed via using your tool "search_sample_resume".
     
    candidate resume: {resume_content} \

    Please supply your reasoning too. 
    """
    related_samples = search_related_samples(job, resume_samples_path)
    sample_tools, tool_names = create_sample_tools(related_samples, "resume")
    response = generate_multifunction_response(query_comparison, sample_tools)


def analyze_resume_type(resume_content, ideal_type):

    query_type = f"""Your task is to provide an assessment of a resume delimited by {delimiter} characters.

    resume: {delimiter}{resume_content}{delimiter} \n

    Research the resume closely and assess if it is written idealy as a {ideal_type} resume. 
    
    A chronological resume should have emphasis on work experience and accomplishment, meaning work experience should be before education and skills.
    A student resume should emphasize coursework, education, accomplishments, and skills. 
    A functional resume should emphasize skills, projects, and accomplishments, where work experience should be after these sections.

    """
    response=create_smartllm_chain(query_type, n_ideas=2)

def tailor_resume(resume_file="", posting_path="", about_job="", resume_dict={}, job_posting_dict={}):

    tailor_dict = {"tailored_skills": "", "tailored_objective":""}
    resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    # posting = read_txt(posting_path, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    # resume_dict = retrieve_or_create_resume_info(resume_path=resume_file, )
    # job_posting_dict= retrieve_or_create_job_posting_info(posting_path=posting_path, about_job=about_job, )
    my_objective = resume_dict["resume fields"].get("summary or objective", "")
    my_skills = resume_dict["resume fields"].get("skills", "")
    my_experience = resume_dict["resume fields"].get("work experience", "")
    skills = job_posting_dict["skills"]
    soft_skills_str = ""
    hard_skills_str=""
    for s in skills:
        if s["type"]=="hard skill":
            skill = s["skill"]
            example = s["example"]
            hard_skills_str+="(skill: " +skill + ", example: "+ example + " )"
        if s["type"]=="soft skill":
            skill = s["skill"]
            example = s["example"]
            soft_skills_str+="(skill: " +skill + ", example: "+ example + " )"
    frequent_words = job_posting_dict["frequent_words"]
    qualifications = job_posting_dict["qualifications"]
    relevant_hard_skills = research_relevancy_in_resume(resume_content, hard_skills_str, "hard skills", n_ideas=1)
    relevant_soft_skills = research_relevancy_in_resume(resume_content, soft_skills_str, "soft skills", n_ideas=1)
    tailored_skills = tailor_skills(my_skills, relevant_hard_skills, relevant_soft_skills, )
    tailor_dict.update({"tailored_skills": tailored_skills})
    # tailored_objective = tailor_objective(my_objective, frequent_words, qualifications)
    # tailor_dict.update({"tailored_objective": tailored_objective})
    return tailor_dict

    

def tailor_skills(skills_content, relevant_hard_skills, relevant_soft_skills):

    """ Creates a cleaned, tailored, reranked skills section according to the skills required in a job description"""

    if skills_content:
        skills_prompt = f""" Your job is to polish and rank the skills section of the resume according to the relevancy list.
        The relevancy report is generated based on what skills in the resume are most relevant to a job description.
        Relevancy report for soft skills: {relevant_soft_skills} \  
        Relevancy report for hard skills: {relevant_hard_skills} \
        The skills in the resume are following: {skills_content} \

        Step 1: Polish the skills section. If the section is too long  or has irrelevant information, please shorten it or exclude the irrelevant information.
        Include both hard skills and soft skills and output the polished skills section. 
        Step2: Rank the skills. Based off the polished skills, rank the skills in the order or relevancy. Output the ranked skills section.

        Use the following format:
            Step 1: <step 1 reasoning>
            Step 2: <step 2 reasoning>
        
        Please use the relevancy report as your primary guideline.  
        """
        prompt_template = ChatPromptTemplate.from_template(skills_prompt)
        message= prompt_template.format_messages(relevant_soft_skills = relevant_soft_skills, 
                                                 relevant_hard_skills = relevant_hard_skills, 
                                                skills_content = skills_content,
        )
        tailored_skills = llm(message).content
        print(tailored_skills)
    else:
        prompt = f"""Please generate a skills section of the resume given the following skills relevancy report:
        
        Skills relevancy report for soft skills: {relevant_soft_skills} \

        Skills relevancy report for hard skills: {relevant_hard_skills} \
        
        Step 1: Please do not use any tools. Generate a list of both hard skills and soft skills that can be included in the resume.

        Step 2: Review the list of skills generated in Step 1. Make sure if a candidate does not have a certain skill, it SHOULD NOT be included in the skills section.
        Output the final skills secition. 

        Use the following format:
            Step 1: <step 1 reasoning>
            Step 2: <step 2 reasoning>
        
        Please use the relevancy report as your primary guideline.  

        """
        tailored_skills = generate_multifunction_response(prompt, create_search_tools("google", 1), )
    return tailored_skills


def tailor_objective(resume_content, job_description):

    prompt = f"""Your job is to tailor or write the objective/summary section of the resume to a job description.  

   job description: {job_description} \
    resume content: {resume_content} \
    
    Output the revised version of the objective/summary only.

    """
    tailored_skills = create_smartllm_chain(prompt, n_ideas=3)
    print(tailored_skills)






# @memoized
def research_resume_type(resume_dict={}, job_posting_dict={}, )-> str:
    
    """ Researches the type of resume most suitable for the applicant. 
    
        Args:
        
            resume_file(str): path of the resume

            posting_path(str): path of the job posting

        Returns:
        
            type of resume: functional, chronological, or students
            
    """
    print(resume_dict)
    jobs = resume_dict["work experience"]
    if job_posting_dict:
        desired_job = job_posting_dict["job"]
    else:
        desired_job=resume_dict["pursuit_job"]
    jobs_list=[]
    for job in jobs:
        jobs_list.append(job["job_title"])
    similar_jobs = extract_similar_jobs(jobs_list, desired_job)
    total_years_work=0
    for job in jobs:
        if job in similar_jobs:
            try:
                years = int(job["years of experience"])
                if years>0:
                    total_years_work+=years
            except Exception:
                pass     
    years_since_graduation = resume_dict["education"]["years since graduation"]
    if (total_years_work<=2 ) and (years_since_graduation<2 ):
        resume_type = "student"
        print("RESUME TYPE: STUDENT")
    elif (years_since_graduation - total_years_work>2):
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
    # resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    functional_doc_template = DocxTemplate(template_file)
    info_dict = get_generated_responses(resume_path=resume_file, posting_path=posting_path)
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
    # resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    chronological_resume_template = DocxTemplate(template_file)
    info_dict = get_generated_responses(resume_path=resume_file, posting_path=posting_path)
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
    # resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    chronological_resume_template = DocxTemplate(template_file)
    info_dict = get_generated_responses(resume_path=resume_file, posting_path=posting_path)
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
      

def create_resume_customize_writer_tool() -> List[Tool]:

    """ Agent tool that calls the function that customizes resume. """

    name = "resume_customize_writer"
    parameters = '{{"job_post_file":"<job_post_file>", "resume_file":"<resume_file>"}}'
    description = f""" Customizes and tailors resume to a job position. 
    Input should be a single string strictly in the following JSON format: {parameters} """
    tools = [
        Tool(
        name = name,
        func = process_resume,
        description = description, 
        verbose = False,
        handle_tool_error=handle_tool_error,
        )
    ]
    print("Succesfully created resume customize wrtier tool.")
    return tools

def process_resume(json_request: str) -> str:

    try:
        args = json.loads(process_json(json_request))
    except JSONDecodeError as e:
        print(f"JSON DECODER ERROR: {e}")
        return "Format in JSON and try again."
    if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
        return """ Ask user to upload their resume. """
    else:
        resume = args["resume_file"]
    if ("about_me" not in args or args["about_me"] == "" or args["about_me"]=="<about_me>") and ("job_post_file" not in args or args["job_post_file"]=="" or args["job_post_file"]=="<job_post_file>"):
        return """ASk user to provide job positing or describe which position to tailor their cover letter to."""
    else:
        if ("about_me" not in args or args["about_me"] == "" or args["about_me"]=="<about_me>"):
            about_me = ""
        else:
            about_me = args["about_me"]
        if ("job_post_file" not in args or args["job_post_file"]=="" or args["job_post_file"]=="<job_post_file>"):
            posting_path = ""
        else:
            posting_path = args["job_post_file"]
    return tailor_resume(resume=resume,  posting_path=posting_path, about_me=about_me)


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
    Input should be a single string strictly in the followiwng JSON format: '{{"resume_file":"<resume_file>"}}' \n
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
    resume_type= research_resume_type(resume_file)
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
    # template_file = "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/backend/resume_templates/functional/functional1.docx"
    # reformat_functional_resume(resume_file=resume_file, posting_path=posting_path, template_file=template_file)
    tailor_resume(resume_file=resume_file, posting_path=posting_path)
    # evaluate_resume(my_job_title =my_job_title, company = company, resume_file=my_resume_file, posting_path = job_posting)
    # evaluate_resume(resume_file=my_resume_file)


