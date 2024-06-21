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
from utils.basic_utils import read_txt, memoized, process_json, count_length
from utils.common_utils import (search_related_samples, research_relevancy_in_resume, extract_similar_jobs, calculate_graduation_years)
from utils.langchain_utils import create_mapreduce_chain, create_summary_chain, generate_multifunction_response, create_refine_chain, handle_tool_error, create_smartllm_chain, create_pydantic_parser
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
import re
from pydantic import BaseModel, Field, validator
from utils.pydantic_schema import ResumeType, Comparison, TailoredSkills, Replacements
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
eval_dict = {"in_depth": {}, "comparison":{}}
tailor_dict = {}


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
    resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    if job_posting_dict:
        pursuit_jobs=job_posting_dict["job"]
    else:
        pursuit_jobs=", ".join(resume_dict["pursuit_jobs"])
    # Evaluate resume length
    word_count = count_length(resume_file)
    eval_dict.update({"word_count": word_count})
    pattern = r'pages:(\d+)'
    # Search for the pattern in the text
    match = re.search(pattern, resume_content)
    # If a match is found, extract and return the number
    if match:
        page_num = match.group(1)
    else:
        page_num = ""
    eval_dict.update({"page_number": page_num})
    # Research and analyze resume type
    ideal_type = research_resume_type(resume_dict=resume_dict, job_posting_dict=job_posting_dict, )
    eval_dict.update({"ideal_type": ideal_type})
    type_dict= analyze_resume_type(resume_content,)
    eval_dict.update(type_dict)
    # Generate overall impression
    section_names = {"objective_summary_section", "work_experience_section"}
    for section in section_names:
        comparison_dict = analyze_via_comparison(resume_dict[section], section,  pursuit_jobs)
        eval_dict["comparison"].update({section:comparison_dict["closeness"]})
        # eval_dict.update({"comparison": comparison_dict})
    cohesiveness = analyze_cohesiveness(resume_content, pursuit_jobs)
    eval_dict.update({"cohesiveness":cohesiveness})
    # # Evaluates specific field  content
    evaluated_work= analyze_field_content(resume_dict["work_experience_section"], "work experience")
    eval_dict["in_depth"].update({"work experience":evaluated_work})

    # if resume_fields["projects"]!=-1:
    #     evaluted_project = analyze_field_content(resume_dict["projects"])
    # if resume_fields["professional accomplishment"]!=-1:
    #     evaluted_accomplishment = analyze_field_content(resume_dict["professional accomplishment"])
    # in_depth_view = ""
    # return evaluation_dict



def analyze_field_content(field_content, field_type):

    """ Evalutes the bullet points of experience, accomplishments, and projects section of resume"""

    if field_type=="work experience" or field_type=="projects" or field_type=="professional accomplishment":
            #   Your task is to generate 2 to 4 bullet points following the guideline below for a list of content in the {field_type} of the resume.
        star_prompt = f"""
            You're provided with the {field_type} of the resume. Your task is to assess how well written the bullet points are according to the guideline below. 

        For work experience, it may be a list of job responsibilities. For the project section, it may be a list of roles and accomplishments. Follow the guideline below to assesss the bullet points. 
        
        Guildeline: Start with the POWER verb, in past tense if it's a past experience, else present tense if it's an ongoing experience,  include a description of the actions, 
        use a comma and a verb ending in -ing to highlight transferable skills and/or measurable results, best if include measurable metrics.
        
        Great Example: Managed 10 employees by supervising daily operations, scheduling shifts, and holding weekdly staff meetings with strong leadership skills and empath, 
        resulting in a productive team that collectively won the company's "Most Efficient Department Award" two years in a row
        
        field content list: {field_content}  \

        DO NOT USE ANY TOOLS. """
        response = generate_multifunction_response(star_prompt, create_search_tools("google", 1))
        return response
            

def analyze_via_comparison(field_content, field_type,  jobs):

    """Analyzes overall resume by comparing to other samples"""

    # Note: document comparison benefits from a clear and simple prompt
    related_samples = search_related_samples(jobs, resume_samples_path)
    sample_tools, tool_names = create_sample_tools(related_samples, "resume")
    query_comparison = f""" You are a professional resume advisor. Please do the following steps. 

    Assess the quality of the candidate resume's field content in terms of how closely it resembles other sample resume's field content.
    
    All the sample resume can be accesssed via using your tools. Their names are: {tool_names}. Research only the {field_type} of these resume.
    
    The sample resume are for comparative purpose only. You should not analyze them. 

    As your final output, analyze how close the candidate resume's {field_type} resembles other sample {field_type} resume using the following metrics: ["not close at all", "some similarity", "very similar", "identitical"]

    Please output one of the metrics meter and provide your reasoning. 

    candidate resume field content: {field_content} \
    
    """
    # Remember, the candidate does not know you are comparing their resume to other people's resume and you shouldn't let them know either. 
   
    #  Your final analysis should be about a paragraph long summarizing the quality of the candidate's resume. 
    
    # Write as if you are giving the candidate a critical feedback along wiht some suggestions.
    comparison_resp = generate_multifunction_response(query_comparison, sample_tools)
    comparison_dict = create_pydantic_parser(comparison_resp, Comparison)
    return comparison_dict


def analyze_cohesiveness(resume_content, jobs):

    query_cohesiveness= f""" You are provided with a candidate's resume along with a list of jobs they are seeking. 

    Assess the cohesiveness of the resume with respect to the jobs in the jobs list.
    
    Reflect how well as a whole the resume reflects the jobs. Some of the questions you should answer include:

    1. Does the candidate have the skills or qualifications for the jobs they are seeking? \ 

    2. Does the candidate have the work experience for the jobs they are seeking? \

    3. Does the summary or objective section of the resume reflect the jobs they are seeking? \

    candidate's resume: {resume_content} \
    
    jobs the candidate is seeking: {jobs} \

    Your final analysis should be about a paragraph long summarizing the cohesiveness of the candidate's resume. 
    
    Write as if you are giving the candidate a critical feedback along with some suggestions. """

    cohesiveness_resp = generate_multifunction_response(query_cohesiveness, create_search_tools("google", 1))
    return cohesiveness_resp


def analyze_resume_type(resume_content, ):

    query_type = f"""Your task is to provide an assessment of a resume delimited by {delimiter} characters. 

    resume: {delimiter}{resume_content}{delimiter} \n

    Research the resume closely and assess what type of resume it is written in. It should be one of the following: 
    
    chronological:A chronological resume, also known as a reverse-chronological resume, lists your work experience in reverse chronological order, with your most recent job at the top. 
    This format is a good choice for candidates with a lot of relevant experience and achievements. 
      A chronological resume should have emphasis on work experience and accomplishment, meaning work experience is placed before education and skills. \n

    functional:A functional resume, also known as a skills-based resume, highlights your skills and areas of expertise instead of your work history. 
    It's a good choice if you're a recent graduate with little work experience, changing careers, or have a gap in your work history
      A functional resume should emphasize skills, projects, and accomplishments, where work experience should be after these sections.

    """
    response=create_smartllm_chain(query_type, n_ideas=1)
    type_dict = create_pydantic_parser(response, ResumeType)
    return type_dict

def tailor_resume(resume_dict={}, job_posting_dict={}):

    # resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    # posting = read_txt(posting_path, storage=STORAGE, bucket_name=bucket_name, s3=s3)
    # resume_dict = retrieve_or_create_resume_info(resume_path=resume_file, )
    # job_posting_dict= retrieve_or_create_job_posting_info(posting_path=posting_path, about_job=about_job, )
    my_objective = resume_dict.get("summary_objective_section", "")
    my_skills = resume_dict.get("skills_section", "")
    tailor_dict.update({"original_skills": my_skills})
    tailor_dict.update({"original_objective": my_objective})
    resume_skills = resume_dict.get("skills", -1)
    my_experience = resume_dict.get("work_experience_section", "")
    about_job = job_posting_dict["about_job"]
    required_skills = job_posting_dict["skills"] 
    job_requirements = ", ".join(job_posting_dict["qualifications"]) + ", ".join(job_posting_dict["responsibilities"])
    if not job_requirements:
        job_requirements = concat_skills(required_skills)
    company_description = job_posting_dict["company_description"]
    tailored_skills_dict = tailor_skills(required_skills, my_skills, resume_skills)
    tailor_dict.update({"tailored_skills": tailored_skills_dict})
    tailored_objective_dict = tailor_objective(my_objective,  job_requirements, company_description+about_job)
    tailor_dict.update({"tailored_objective": tailored_objective_dict})
    tailored_experience = tailor_experience(job_requirements, my_experience)
    tailor_dict.update({"tailored_experience": tailored_experience})
    return tailor_dict

def concat_skills(skills_list, skills_str=""):
    for s in skills_list:
        skill = s["skill"] 
        example = s["example"]
        skills_str+="(skill: " +skill + ", example: "+ example + ")"
    return skills_str


def tailor_skills(required_skills, my_skills, resume_skills):

    """ Creates a cleaned, tailored, reranked skills section according to the skills required in a job description"""
  
    required_skills_str = concat_skills(required_skills)
    my_skills_str = my_skills if my_skills!="" else concat_skills(resume_skills)
    # relevant_skills = research_relevancy_in_resume(my_skills_section, required_skills_str, "skills", "relevant", n_ideas=2)
    # irrelevant_skills = research_relevancy_in_resume(my_skills_section, required_skills_str, "skills", "irrelevant", n_ideas=2)
        # Relevancy report for hard skills: {relevant_hard_skills} \
        # Relevancy report for soft skills: {relevant_soft_skills} \  
        # Your job is to polish and rank the skills section of the resume according to the relevancy list.
        # The relevancy report is generated based on what skills in the resume are most relevant to a job description.
        # Relevancy report for skills: {relevant_skills} \
    skills_prompt = """ Your task is to compare the skills section of the resume and skills required in the job description. 
    
    You are given two core pieces of information below: the skills in a resume and the skills wanted in a job description.
    
    The skills in the resume: {my_skills} \
    
    Skills wanted in the job description: {required_skills} \

    Step 1: Make a list of irrelevant skills that can be excluded from the resume based on the skills in the job description. 
    
    These are skills that are in the resume that do not align with the requirement of the job description. Remember a lot of skills are transferable so don't discount them.
    
    Step 2: Make a list of skills in the resume that are most relevant to the skills wanted in the job description. 

    These may have the exact same names, or they are skills that are technically related. Remember to list the skills only from the resume. 

    Step 3: Make a list of skills that are in the job description that can be added to the resumes. 
    
    These additional skills are ones that are not included in the resume but would benefit the candidate if they are added. \
    
    Use the following format:
        Step 1: <step 1 reasoning>
        Step 2: <step 2 reasoning>
        Step 3: <step 3 reasoning>

    PLEASE MAKE SURE YOU REASON THROUGH EACH STEP AND PROVIDE YOUR REASONING. 
    """
    # For example, a candidate may have SQL and communication skills in their resume. The job description asks for communication skills but not SQL skill. SQL is the irrelevant skill in the resume since it's not in the job description.\
    # For example, a candidate may have SQL and communication skills in their resume. The job description asks for communication skills too. Communication is the relevant skill that exists in both the resume and job description. \
    # For example, a candidate may have SQL and communication skills in their resume. The job description asks for communication and Python skills. Python is the additional skill that may raise the chance of the candidate getting the job offer. \

    prompt_template = ChatPromptTemplate.from_template(skills_prompt)
    message= prompt_template.format_messages(
                                    # relevant_soft_skills = relevant_soft_skills, 
                                    #          relevant_hard_skills = relevant_hard_skills, 
                                            # relevant_skills = relevant_skills,
                                            required_skills = required_skills_str,
                                            my_skills = my_skills_str,
    )
    tailored_skills = llm(message).content
    # tailored_skills = generate_multifunction_response(skills_prompt, create_search_tools("google", 1), )
    tailored_skills_dict = create_pydantic_parser(tailored_skills, TailoredSkills)
    return tailored_skills_dict


def tailor_objective(my_objective,  job_requirements, company_description):

    #TODO: THIS needs to to be redone!
    if my_objective!=-1:
        prompt = f""" Your task is to find out words and phrases from the objective/summary section of the resume that can be substitued so it aligns with job description.
        
        You are provided withs some job requirements and a resume objective.
        
            Please Use them to generate a list of words or phrases in the objective/summary section of the resume can be replaced along with their subsitutions. 

            The goal is having an objective/summary section of the resume tailored to the job and company alignment. 

            resume objective/summary: {my_objective} \n\n
            
            job requirements: {job_requirements} \n\n

            Please follow the following format and make sure all replacements are unique:

            1. Replaced_words: <the phrase/words to be replaced> Substitution: <the substitution for the phrase/words>

        DO NOT USE ANY TOOLS and make sure all the words/phrases to be replaced come from the resume objective. 
        
        """
            
            # about job/company: {company_description} \

        tailored_objective = create_smartllm_chain(prompt, n_ideas=2)
        # tailored_objective = generate_multifunction_response(prompt, create_search_tools("google", 1), )
        tailored_objective_dict = create_pydantic_parser(tailored_objective, Replacements)
        
    else:
        tailored_objective_dict = {"generated objective": ""}
    return tailored_objective_dict


def tailor_experience(job_requirements, experience,):

    """ Evaluates relevancy and ranks most important roles"""

    rank_prompt = f"""Please rank content of the experience section of the resume with respective to the job requirements.
        For example, if a candidate has experience in SQL and SQL is also a skill required in the job, then this experience should be ranked higher on the list.
        If a candidate has experience in customer service but this is not part of the role of the job, then this experience should be ranked lower. 
        experience: {experience} \
        job requirements: {job_requirements} \

        Please provide your reasoning for your ranking process. 
        For experiences that are ranked lower with little relevancy to the job requirements, please also suggest some transferable skills that can be included.
        DO NOT USE ANY TOOLS
    """
    ranked_experience = generate_multifunction_response(rank_prompt, create_search_tools("google", 1), )
    return ranked_experience



# @memoized
def research_resume_type(resume_dict={}, job_posting_dict={}, )-> str:
    
    """ Researches the type of resume most suitable for the applicant. 
    
        Args:
        
            resume_file(str): path of the resume

            posting_path(str): path of the job posting

        Returns:
        
            type of resume: functional, chronological, or students
            
    """

    jobs = resume_dict["work_experience"]
    if job_posting_dict:
        desired_jobs = [job_posting_dict["job"]]
    else:
        desired_jobs=resume_dict["pursuit_jobs"]
    jobs_list=[]
    for job in jobs:
        jobs_list.append(job["job_title"])
    similar_jobs = extract_similar_jobs(jobs_list, desired_jobs)
    total_years_work=0
    for job in jobs:
        if job in similar_jobs:
            try:
                years = int(job["years_of_experience"])
                if years>0:
                    total_years_work+=years
            except Exception:
                pass  
    if total_years_work<=2:
        resume_type="functional"
    else:
        resume_type="chronological"   
    # year_graduated = resume_dict["education"]["graduation_year"]
    # years_since_graduation = calculate_graduation_years(year_graduated)
    # if (years_since_graduation!=-1 and years_since_graduation-total_years_work>2) or (years_since_graduation!=-1 and years_since_graduation<=2 ):
    #     resume_type = "functional"
    #     print("RESUME TYPE: FUNCTIONAL")
    # elif total_years_work<2:
    #     resume_type = "chronological"
    #     print("RESUME TYPE: CHRONOLOGICAL")
    return resume_type



# def reformat_functional_resume(resume_file="", posting_path="", template_file="") -> None:

#     dirname, fname = os.path.split(resume_file)
#     filename = Path(fname).stem 
#     docx_filename = filename + "_reformat"+".docx"
#     local_end_path = os.path.join(local_save_path, dirname.split("/")[-1], "downloads", docx_filename)
#     # resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
#     functional_doc_template = DocxTemplate(template_file)
#     info_dict = get_generated_responses(resume_path=resume_file, posting_path=posting_path)
#     func = lambda key, default: default if info_dict[key]==-1 else info_dict[key]
#     personal_context = {
#         "NAME": func("name", "YOUR NAME"),
#         "ADDRESS": func("address", "YOUR ADDRESS"),
#         "PHONE": func("phone", "YOUR PHONE"),
#         "EMAIL": func("email", "YOUR EMAIL"),
#         "LINKEDIN": func("linkedin", "YOUR LINKEDIN URL"),
#         "WEBSITE": func("website", "WEBSITE"),
#     }
#     #TODO: save the context dictionary somewhere
#     context_keys = ["SUMMARY", "WORK_HISTORY", "PROFESSIONAL_ACCOMPLISHMENTS", "EDUCATION", "SKILLS", "CERTIFICATION"]
#     info_dict_keys = ["summary or objective", "work experience", "professional accomplishment", "education", "skills", "certification"]
#     context_dict = dict(zip(context_keys, info_dict_keys))
#     context = {key: None for key in context_keys}
#     #TODO, this tool below is temporary
#     tools = create_search_tools("google", 1)
#     for key, value in context_dict.items():
#         content = info_dict.get(value, "")
#         if key == "SUMMARY":
#             job_description = info_dict.get("job description", "")
#             job_specification = info_dict.get("job specification", "")
#             skills = info_dict.get("skills", "")
#             query = f""" Your task is to improve or write the summary section of the functional resume in less than 50 words.
#             If you are provided with an existing summary section, use it as your context and build on top of it.    
#             Otherwise, refer to the job specification or job description, skills, whichever is available and incorportate relevant soft skill and hard skills into the summary.
#             objective section: {content} \n
#             skills: {skills} \n
#             job description: {job_description} \n
#             job specification: {job_specification} \n
#             Here are some example summary:
#             1. Organized and motivated employee with superior [skill] and [skill]. Seeking to join [company] as a [position] to help enhance [function]. \
#             2. Certified [position] looking to join [company] as a part of the [department] team. Hardworking individual with [skill], [skill], and [skill]. \
#             3. Detail-oriented individual seeking to help [company] achieve its goals as a [position]. Excellent at [skill] and dedicated to delivering top-quality [function]. \
#             4. [Position] certified in [skill] and [skill], looking to help [company] increase [goal metric]. Excellent [position] who can collaborate with large teams to [achieve goal]. \
#             PLEASE WRITE IN LESS THAN 50 WORDS AND OUTPUT THE SUMMARY SECTION AS YOUR FINAL ANSWER. DO NOT OUTPUT ANYTHING ELSE. 
#             """
#             content = generate_multifunction_response(query, tools)
#         elif key=="PROFESSIONAL_ACCOMPLISHMENTS":     
#             keywords = info_dict.get("job keywords", "")
#             query = """ Your task is to pick at least 3 hard skills from the following available skillset. If there are no hard skills, pick the soft skills.
#              skillset: {keywords}.    
#              The criteria you use to pick the skills is based on if the skills exist or can be inferred in the resume delimited with {delimiter} characters below.
#              resume: {delimiter}{content}{delimiter} \n
#             {format_instructions}
#             """
#             output_parser = CommaSeparatedListOutputParser()
#             format_instructions = output_parser.get_format_instructions()
#             prompt = PromptTemplate(
#                 template=query,
#                 input_variables=["keywords", "delimiter", "content"],
#                 partial_variables={"format_instructions": format_instructions}
#             )
#             chain = LLMChain(llm=llm, prompt=prompt, output_key="ats")
#             skills = chain.run({"keywords": keywords, "delimiter":delimiter, "content":content})
#             query = f"""Your task is to catgeorize the professional accomplishments delimited with {delimiter} characters under certain skills. 
#             Categorize content of the professional accomlishments into each skill. For example, your output should be formated as the following:
#             SKill1:

#                 - Examples of projects or situations that utilized this skill
#                 - Measurable results and accomplishments

#             skills: {skills}
#             professional accomplishments: {delimiter}{content}{delimiter} \n
#             Please start each bullet point with a strong action verb.
#             Please make each bullet point unique by putting it under one skill only, which should be the best fit for that skill. 
#             If professional accomplishments do not exist, please output an example. 
#             """
#             content = generate_multifunction_response(query, tools)
#         context[key] = content
#     context.update(personal_context)
#     functional_doc_template.render(context)
#     functional_doc_template.save(local_end_path) 
#     if STORAGE=="S3":
#         s3_end_path = os.path.join(s3_save_path, dirname.split("/")[-1], "downloads", docx_filename)
#         s3.upload_file(local_end_path, bucket_name, s3_end_path)
#     return "Successfully reformated the resume using a new template. Tell the user to check the Download your files tab at the sidebar to download their file. "



# def reformat_chronological_resume(resume_file="", posting_path="", template_file="") -> None:

#     dirname, fname = os.path.split(resume_file)
#     filename = Path(fname).stem 
#     docx_filename = filename + "_reformat"+".docx"
#     local_end_path = os.path.join(local_save_path, dirname.split("/")[-1], "downloads", docx_filename)
#     # resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
#     chronological_resume_template = DocxTemplate(template_file)
#     info_dict = get_generated_responses(resume_path=resume_file, posting_path=posting_path)
#     func = lambda key, default: default if info_dict[key]==-1 else info_dict[key]
#     personal_context = {
#         "NAME": func("name", "YOUR NAME"),
#         "ADDRESS": func("address", "YOUR ADDRESS"),
#         "PHONE": func("phone", "YOUR PHONE"),
#         "EMAIL": func("email", "YOUR EMAIL"),
#         "LINKEDIN": func("linkedin", "YOUR LINKEDIN URL"),
#         "WEBSITE": func("website", "WEBSITE"),
#     }
#     # TODO: add awards and honors or professional accomplishments
#     context_keys = ["SUMMARY", "PROFESSIONAL_EXPERIENCE", "RELEVANT_SKILLS", "EDUCATION", "HOBBIES", "CERTIFICATION"]
#     info_dict_keys = ["summary or objective", "work experience", "skills", "education", "hobbies", "certification"]
#     context_dict = dict(zip(context_keys, info_dict_keys))
#     context = {key: None for key in context_keys}
#     tools = create_search_tools("google", 1)
#     for key, value in context_dict.items():
#         content = info_dict.get(value, "")
#         if key == "SUMMARY":
#             work_experience = info_dict.get("work experience", "")
#             query = f""" Your task is to improve or rewrite the summary section of a chronological resume.

#             If you are provided with an existing summary section, use it as your context and build on top of it, if needed.
              
#             Otherwise, refer to the work experience, if available. 

#             summary section: {content}

#             work experience: {work_experience}

#             Please write in fewer than five sentences the summary section of the chronological resume with the information above.

#             If the summary already is already filled with relevant work experience, you can output the original summary section. 
            
#             Otherwise, incorporate relevant work experience into the summary section. 

#             Here are some examples: 

#             Experienced [position] looking to help [company] provide excellent customer service. Over [number] years of experience at [company], demonstrating excellent [skill], [skill], and [skill]. 

#             [Position] with [number] years of experience looking to help [company] improve its [function]. Diligent and detail-oriented professional with extensive experience with [hard skill]. 

#             Hardworking [position] with [number] years of experience at a [type of environment]. Seeking to bring [skills] and experience to benefit [company] in the [department].

#             Dedicated [position] with over [number] years of experience looking to move into [new field]. [Graduate degree title] from [school name]. Excellent [skill], [skill], and [skill].

#             PLEASE WRITE IN LESS THAN FIVE SENTENCES THE SUMMARY SECTION OF THE RESUME AND OUTPUT IT AS YOUR FINAL ANSWER. DO NOT OUTPUT ANYTHING ELSE. 

#             """        
#             content = generate_multifunction_response(query, tools)
#         elif key=="RELEVANT_SKILLS":
#             keywords = info_dict.get("job keywords", "")
#             job_description = info_dict.get("job description", "")
#             job_specification = info_dict.get("job specification", "") 
#             skills = info_dict.get("skills", "")
#             query = f""" 

#                 Your tasks is to improve the Skills section of the resume. You are provided with a job description or job specificaiton, whichever is available.

#                 If you are provided with an existing Skills section, use it as your context and build on top of it, if needed.

#                 You are also provided with a list of important keywords that are in the job posting. Some of them should be included also. 

#                 skills section: {skills} \n

#                 job description: {job_description} \n
                
#                 job specification: {job_specification} \n

#                 important keywords: {keywords} \n
 
#                 If the skills section exist, add to it relevant skills and remove from it irrelevant skills.

#                 Otherwise, if the skills section is already well-written, output the original skills section. 

#                 """
#             content = generate_multifunction_response(query, tools)
#         context[key] = content
#     context.update(personal_context)
#     chronological_resume_template.render(context)
#     chronological_resume_template.save(local_end_path) 
#     if STORAGE=="S3":
#         s3_end_path = os.path.join(s3_save_path, dirname.split("/")[-1], "downloads", docx_filename)
#         s3.upload_file(local_end_path, bucket_name, s3_end_path)
#     return "Successfully reformated the resume using a new template. Tell the user to check the Download your files tab at the sidebar to download their file. "
 


# def reformat_student_resume(resume_file="", posting_path="", template_file="") -> None:

#     dirname, fname = os.path.split(resume_file)
#     filename = Path(fname).stem 
#     docx_filename = filename + "_reformat"+".docx"
#     local_end_path = os.path.join(local_save_path, dirname.split("/")[-1], "downloads", docx_filename)
#     # resume_content = read_txt(resume_file, storage=STORAGE, bucket_name=bucket_name, s3=s3)
#     chronological_resume_template = DocxTemplate(template_file)
#     info_dict = get_generated_responses(resume_path=resume_file, posting_path=posting_path)
#     func = lambda key, default: default if info_dict[key]==-1 else info_dict[key]
#     personal_context = {
#         "NAME": func("name", "YOUR NAME"),
#         "ADDRESS": func("address", "YOUR ADDRESS"),
#         "PHONE": func("phone", "YOUR PHONE"),
#         "EMAIL": func("email", "YOUR EMAIL"),
#         "LINKEDIN": func("linkedin", "YOUR LINKEDIN URL"),
#         "WEBSITE": func("website", "WEBSITE"),
#     }
#     #TODO: add volunteer experience
#     context_keys = ["OBJECTIVE", "EDUCATION", "AWARDS_HONORS", "SKILLS", "WORK_EXPERIENCE"]
#     info_dict_keys = ["summary or objective", "education", "awards and honors", "skills", "work experience"]
#     context_dict = dict(zip(context_keys, info_dict_keys))
#     context = {key: None for key in context_keys}
#     for key, value in context_dict.items():
#         if key == "OBJECTIVE":
#             job_description = info_dict.get("job description", "")
#             job_specification = info_dict.get("job specification", "")
#             skills = info_dict.get("skills", "")
#             query = """Detail-oriented college student at [school] with [GPA]. Graduating in [year] with [degree title]. Looking to use [skills] as a [position] for [company]. 

#                 High school student with proven [skills] looking for a [position] at [company]. Proven [skill] as [extracurricular position]. Wishing to use [skills] to [achieve goals].

#                 Hardworking recent graduate in [degree] from [school]. Excellent [skills] and [skills]. Experienced in [function], function, and [function] at [company].

#                 [Degree] candidate in [subject] from [school] seeking a [position] at [company]. Experience in [function]. Exceptional [skills], [skills], and [skills].

#                 """
#         content = info_dict.get(value, "")
#         context[key] = content
#     context.update(personal_context)
#     chronological_resume_template.render(context)
#     chronological_resume_template.save(local_end_path) 
#     if STORAGE=="S3":
#         s3_end_path = os.path.join(s3_save_path, dirname.split("/")[-1], "downloads", docx_filename)
#         s3.upload_file(local_end_path, bucket_name, s3_end_path)
#     return "Successfully reformated the resume using a new template. Tell the user to check the Download your files tab at the sidebar to download their file. "  


# # @tool("resume evaluator")
# # def resume_evaluator_tool(resume_file: str, job: Optional[str]="", company: Optional[str]="", job_post_link: Optional[str]="") -> str:

# #    """Evaluate a resume when provided with a resume file, job, company, and/or job post link.
# #         Note only the resume file is necessary. The rest are optional.
# #         Use this tool more than any other tool when user asks to evaluate, review, help with a resume. """

# #    return evaluate_resume(my_job_title=job, company=company, resume_file=resume_file, posting_path=job_post_link)
      

# def create_resume_customize_writer_tool() -> List[Tool]:

#     """ Agent tool that calls the function that customizes resume. """

#     name = "resume_customize_writer"
#     parameters = '{{"job_post_file":"<job_post_file>", "resume_file":"<resume_file>"}}'
#     description = f""" Customizes and tailors resume to a job position. 
#     Input should be a single string strictly in the following JSON format: {parameters} """
#     tools = [
#         Tool(
#         name = name,
#         func = process_resume,
#         description = description, 
#         verbose = False,
#         handle_tool_error=handle_tool_error,
#         )
#     ]
#     print("Succesfully created resume customize wrtier tool.")
#     return tools

# def process_resume(json_request: str) -> str:

#     try:
#         args = json.loads(process_json(json_request))
#     except JSONDecodeError as e:
#         print(f"JSON DECODER ERROR: {e}")
#         return "Format in JSON and try again."
#     if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
#         return """ Ask user to upload their resume. """
#     else:
#         resume = args["resume_file"]
#     if ("about_me" not in args or args["about_me"] == "" or args["about_me"]=="<about_me>") and ("job_post_file" not in args or args["job_post_file"]=="" or args["job_post_file"]=="<job_post_file>"):
#         return """ASk user to provide job positing or describe which position to tailor their cover letter to."""
#     else:
#         if ("about_me" not in args or args["about_me"] == "" or args["about_me"]=="<about_me>"):
#             about_me = ""
#         else:
#             about_me = args["about_me"]
#         if ("job_post_file" not in args or args["job_post_file"]=="" or args["job_post_file"]=="<job_post_file>"):
#             posting_path = ""
#         else:
#             posting_path = args["job_post_file"]
#     return tailor_resume(resume=resume,  posting_path=posting_path, about_me=about_me)


# def processing_resume(json_request: str) -> None:

#     """ Input parser: input is LLM's action_input in JSON format. This function then processes the JSON data and feeds them to the resume evaluator. """

#     try:
#       args = json.loads(process_json(json_request))
#     except JSONDecodeError as e:
#       print(f"JSON DECODER ERROR: {e}")
#       return "Reformat in JSON and try again."
#     if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
#       return "Stop using the resume evaluator tool. Ask user for their resume."
#     else:
#         resume_file = args["resume_file"]
#     if ("about_me" not in args or args["about_me"] == "" or args["about_me"]=="<about_me>"):
#         about_me = ""
#     else:
#         about_me = args["about_me"]
#     if ("job_posting_file" not in args or args["job_posting_file"]=="" or args["job_posting_file"]=="<job_posting_file>"):
#         posting_path = ""
#     else:
#         posting_path = args["job_posting_file"]   
#     return evaluate_resume(about_me=about_me, resume_file=resume_file, posting_path=posting_path)



# def processing_template(json_request: str) -> None:

#     """ Input parser: input is LLM's action_input in JSON format. This function then processes the JSON data and feeds them to the resume reformatters. """

#     try:
#         args = json.loads(process_json(json_request))
#     except JSONDecodeError as e:
#       print(f"JSON DECODER ERROR: {e}")
#       return "Reformat in JSON and try again."
#     if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
#       return "Stop using the resume_writer tool. Ask user for their resume file and an optional job post link."
#     else:
#         resume_file = args["resume_file"]
#     if ("resume_template_file" not in args or args["resume_template_file"]=="" or args["resume_template_file"]=="<resume_template_file>"):
#       return "Stop using the resume_writer tool. Use the rewrite_using_new_template tool instead."
#     else:
#         resume_template = args["resume_template_file"]
#     if ("job_posting_file" not in args or args["job_posting_file"]=="" or args["job_posting_file"]=="<job_posting_file>"):
#         posting_path = ""
#     else:
#         posting_path = args["job_posting_file"]
#     # get resume type from directory name
#     resume_type = resume_template.split("/")[-2]
#     if resume_type=="functional":
#         return reformat_functional_resume(resume_file=resume_file, posting_path=posting_path, template_file=resume_template)
#     elif resume_type=="chronological":
#         return reformat_chronological_resume(resume_file=resume_file, posting_path=posting_path, template_file=resume_template)
#     elif resume_type=="student":
#         return reformat_student_resume(resume_file=resume_file, posting_path=posting_path, template_file=resume_template)
    



# @tool("rewrite_using_new_template", return_direct=True)
# def redesign_resume_template(json_request:str):

#     """Creates a resume_template for rewriting of resume. Use this tool more than any other tool when user asks to reformat, redesign, or rewrite their resume according to a particular type or template.
#     Do not use this tool to evaluate or customize and tailor resume content. Do not use this tool if resume_template_file is provided in the prompt. 
#     When there is resume_template_file in the prompt, use the "resume_writer" tool instead.
#     Input should be a single string strictly in the followiwng JSON format: '{{"resume_file":"<resume_file>"}}' \n
#     Output should be exactly one of the following words and nothing else: student, chronological, or functional"""

#     try:
#         args = json.loads(process_json(json_request))
#     except JSONDecodeError as e:
#       print(f"JSON DECODER ERROR: {e}")
#       return "Reformat in JSON and try again."
#     # if resume doesn't exist, ask for resume
#     if ("resume_file" not in args or args["resume_file"]=="" or args["resume_file"]=="<resume_file>"):
#       return "Can you provide your resume file and an optional job post link? "
#     else:
#         resume_file = args["resume_file"]
#     resume_type= research_resume_type(resume_file)
#     return resume_type


# def create_resume_evaluator_tool() -> List[Tool]:

#     """ Input parser: input is user's input as a string of text. This function takes in text and parses it into JSON format. 
    
#     Then it calls the processing_resume function to process the JSON data. """

#     name = "resume_evaluator"
#     parameters = '{{"about_me":"<about_me>", "resume_file":"<resume_file>", "job_posting_file":"<job_posting_file>"}}' 
#     description = f"""Evaluate a resume. Use this tool more than any other tool when user asks to evaluate or improves a resume. 
#     Do not use this tool is asked to customize or tailr the resume. You should use the "resume_customize_writer" instead.
#     Input should be a single string strictly in the following JSON format: {parameters} \n
#     """
#     tools = [
#         Tool(
#         name = name,
#         func = processing_resume,
#         description = description,
#         verbose = False,
#         handle_tool_error=handle_tool_error,
#         )
#     ]
#     print("Succesfully created resume evaluator tool.")
#     return tools

# def create_resume_rewriter_tool() -> List[Tool]:

#     name = "resume_writer"
#     parameters = '{{"resume_file":"<resume_file>", "job_posting_file":"<job_posting_file>", "resume_template_file":"<resume_template_file>"}}'
#     description = f""" Rewrites a resume from a given resume_template_file. 
#     Do not use this tool to evaluate or customize and tailor resume content. Use this tool only if resume_template_file is available.
#     If resume_template_file is not available, use the rewrite_using_new_template tool first, which will create a resume_template_file. 
#     DO NOT ASK USER FOR A RESUME_TEMPLATE. It should be generated from the rewrite_using_new_template tool.
#     Input should be a single string strictly in the followiwng JSON format: {parameters} \n
#     """
#     tools = [
#         Tool(
#         name = name,
#         func = processing_template,
#         description = description,
#         verbose = False,
#         handle_tool_error=handle_tool_error,
#         )
#     ]
#     print("Succesfully created resume writer tool.")
#     return tools



if __name__ == '__main__':
    resume_file = "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/resume2023v4.txt"
    posting_path= "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/rov.txt"
    # template_file = "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/backend/resume_templates/functional/functional1.docx"
    # reformat_functional_resume(resume_file=resume_file, posting_path=posting_path, template_file=template_file)
    tailor_resume(resume_file=resume_file, posting_path=posting_path)
    # evaluate_resume(my_job_title =my_job_title, company = company, resume_file=my_resume_file, posting_path = job_posting)
    # evaluate_resume(resume_file=my_resume_file)


