import os
import openai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from utils.basic_utils import count_length
from utils.common_utils import search_related_samples,  extract_similar_jobs, readability_checker
from utils.langchain_utils import  generate_multifunction_response, create_smartllm_chain, create_pydantic_parser, create_comma_separated_list_parser
from utils.agent_tools import create_search_tools, create_sample_tools
from typing import Dict, List, Optional, Union
from docxtpl import DocxTemplate, RichText
# from operator import itemgetter
# from docx import Document
# from docx.shared import Inches
import re
from utils.pydantic_schema import ResumeType, Comparison, SkillsRelevancy, Replacements, Language, MatchResumeJob
from dotenv import load_dotenv, find_dotenv
from io import BytesIO
from utils.aws_manager import get_client
import tempfile
# import textstat as ts
from langchain_core.prompts import ChatPromptTemplate,  PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from utils.async_utils import asyncio_run, future_run_with_timeout, tenacity_run_with_timeout
# import concurrent.futures
import time as time
import jinja2
import streamlit as st


_ = load_dotenv(find_dotenv()) # read local .env file
openai.api_key = os.environ["OPENAI_API_KEY"]
faiss_web_data = os.environ["FAISS_WEB_DATA_PATH"]
STORAGE = os.environ["STORAGE"]
local_save_path = os.environ["CHAT_PATH"]
# TODO: caching and serialization of llm
llm = ChatOpenAI(model="gpt-4o-mini")
embeddings = OpenAIEmbeddings()
# TODO: save these delimiters in json file to be loaded from .env
delimiter = "####"
delimiter1 = "````"
delimiter2 = "////"
delimiter3 = "<<<<"
delimiter4 = "****"



STORAGE = os.environ["STORAGE"]
if STORAGE=="CLOUD":
    bucket_name = os.environ["BUCKET_NAME"]
    s3_save_path = os.environ["S3_CHAT_PATH"]
    s3 = get_client('s3')
    resume_samples_path = os.environ["RESUME_SAMPLES_PATH"]
else:
    bucket_name=None
    s3=None
    resume_samples_path=os.environ["S3_RESUME_SAMPLES_PATH"]


def evaluate_resume(resume_dict={},  type="general",  p=None, loading_func=None) -> Dict[str, str]:


    def insert_break_character(text, char='<br>', interval=5):

        """ Breaks display of annotation on plots into new lines to fit container width"""

        words = text.split()  # Split the text into a list of words
        for i in range(interval, len(words), interval):
            words.insert(i, char)  # Insert the special character every 5 words
        return ' '.join(words)  # Join the words back into a single string

    print("start evaluating...")
    resume_content = resume_dict["resume_content"]
    # print(resume_content)
    if type=="general":
        try:
            st.session_state["evaluation"] = {"finished":False}
            # resume_file = resume_dict["resume_path"]
            pursuit_jobs=resume_dict["pursuit_jobs"]
            industry = resume_dict["industry"]
            # Evaluate resume length
            word_count = count_length(content=resume_content)
            st.session_state.evaluation.update({"word_count": word_count})
            # pattern = r'pages:(\d+)'
            # # Search for the pattern in the text (I added page number when writing the file to txt)
            # match = re.search(pattern, resume_content)
            # # If a match is found, extract and return the number
            # if match:
            #     page_num = match.group(1)
            # else:
            #     page_num = 0
            # st.session_state.evaluation.update({"page_count": int(page_num)})
            # Research and analyze resume type
            ideal_type = research_resume_type(resume_dict=resume_dict, )
            st.session_state.evaluation.update({"ideal_type": ideal_type})
            # resume_type= analyze_resume_type(resume_content,)
            # st.session_state.evaluation.update({"resume_type": resume_type})
            # st.session_state.evaluation.update(type_dict)
            categories=["syntax", "tone", "readability"]
            for category in categories:
                # category_dict = asyncio_run(lambda: analyze_language(resume_content, category, industry), timeout=10)
                category_dict = analyze_language(resume_content, category, industry)
                if category_dict:
                    if  category=="syntax" or category=="tone":
                        category_dict=category_dict.dict()
                        if category_dict["reason"]:
                           category_dict["reason"]= insert_break_character(category_dict["reason"])
                    st.session_state.evaluation.update({category:category_dict})
            # section_names = ["objective", "work_experience", "skillsets"]
            # field_names = ["summary_objective", "work_experience", "included_skills"]
            # field_map = dict(zip(field_names, section_names))
            # related_samples = search_related_samples(pursuit_jobs, resume_samples_path)
            # sample_tools, tool_names = create_sample_tools(related_samples, "resume")
            # for field_name, section_name in field_map.items():
            #     # for category in categories:
            #     comparison_dict = analyze_via_comparison(resume_dict[field_name], section_name,  sample_tools, tool_names)
            #     st.session_state.evaluation.update({section_name:comparison_dict})
            # Generate overall impression
            # impression = generate_impression(resume_content, pursuit_jobs)
            # st.session_state.evaluation["impression"]= impression
            st.session_state.evaluation["finished"]=True
        #NOTE: sometimes user may refresh page and this abruptly ends the session so st.session_state["evaluation"] becomes a Nonetype
        except AttributeError:
            pass
    # Evaluates specific field  content
    else:
        readability_dict, evaluation ={},  None
        if resume_dict[type]:
            for _ in range(5):
                # Perform some processing (e.g., tailoring a resume)
                time.sleep(0.1)  # Simulate time-consuming task
                p.increment(10)  # Update progress in steps of 10%
                loading_func(p.progress)
            # work_experience= resume_dict["work_experience"]
            # st.session_state[f"readability_{type}_{idx}"] = readability_checker(resume_content)
            readability_dict = readability_checker(resume_content)
            p.increment(20) 
            loading_func(p.progress)
            details = resume_dict[type]
            evaluation= analyze_field_content(details, type, resume_content)
            p.increment(30)  
            loading_func(p.progress)
        return readability_dict, evaluation
        # st.session_state[f"evaluated_{type}_{idx}"]=evaluation
    # else:
    #     # st.session_state[f"evaluated_{type}"]="Please fill out the content"
    #     eval_dict="Please fill out the content"





def analyze_field_content(field_content, field_type, resume_content):

    """ Evalutes the bullet points sections of resume"""

    if field_type=="work_experience" or field_type=="projects" or field_type=="qualifications":
            #   Your task is to generate 2 to 4 bullet points following the guideline below for a list of content in the {field_type} of the resume.
        query = f"""
            You're provided with the {field_type} of the resume. Your task is to assess how well written the bullet points are according to the guideline below. 

        For work experience, it may be a list of job responsibilities. For the project section, it may be a list of roles and accomplishments. Follow the guideline below to assesss the bullet points. 
        
        Guildeline: Start with the POWER verb, in past tense if it's a past experience, else present tense if it's an ongoing experience,  include a description of the actions, 
        use a comma and a verb ending in -ing to highlight transferable skills and/or measurable results, best if include measurable metrics.
        
        Great Example: Managed 10 employees by supervising daily operations, scheduling shifts, and holding weekdly staff meetings with strong leadership skills and empath, 
        resulting in a productive team that collectively won the company's "Most Efficient Department Award" two years in a row
        
        field content list: {field_content}  \

        DO NOT USE ANY TOOLS. """
        # response = asyncio_run(lambda: generate_multifunction_response(star_prompt, create_search_tools("google", 1)), timeout=10)
        # response =  generate_multifunction_response(star_prompt, create_search_tools("google", 1))
    # elif field_type=="projects":
    #     """Summary of the project
    #         Where the dataset came from
    #         The questions you asked or hypotheses you theorized
    #         The types of queries you ran (including some of the code, specifically)
    #         The tools you used to do your analysis
    #         Your findings
    #         The limitations of your project
    #         Conclusions and/pr recommendations
    #         Further questions to examine in the future"""
    #     response = "Please try again later."
    elif field_type=="summary_objective":
    
        query = f"""Given the resume content and summary objective section below, please analyze the summary objective section based on the following criteria:

        1. Is it succinct and well-crafted? \
        
        2. Does it highlight the qualifications of the candidate, such as their valuable skills and experience? \
        
        3. Does it communicate the candidate's career goals effectively? \

        Your final output should be about 50-100 words long summarizing how the summary/objective section of the resume met or did not meet the criteria. Include any suggestions if needed.

        DO NOT USE ANY TOOLS!

        resume content: {resume_content}

        summary objective section: {field_content}
        
        """
        # response = asyncio_run(lambda: generate_multifunction_response(summary_query, create_search_tools("google", 1)), timeout=10)
    response = generate_multifunction_response(query, create_search_tools("google", 1))
    return response.get("output", "") if response else ""


    


def analyze_via_comparison(field_content, field_name,  sample_tools, tool_names):

    """Analyzes overall resume by comparing to other sample resume """

    # NOTE: document comparison benefits from a clear and simple prompt. 

    query_comparison = f"""
    
    Compare the candidate resume's {field_name} to other sample resume's {field_name}.
    
    All the sample resume can be accesssed using your tools. Their names are: {tool_names}. 
    
    The sample resume are for comparative purpose only. You should not analyze them. 
s
    Please search for only the {field_name} of the sample resume.

    Analyze how close the candidate resume field resembles other sample resume. 

    Please use the following metrics: ["no similarity", "some similarity", "very similar"]

    Please output one of the metrics meter and provide your reasoning. Your reasoning should be about one sentence long, and do not identify any sample resume in your reasoning.

    candidate resume's {field_name} content: {field_content} \
    
    """
    comparison_dict = {"closeness":"", "reason":""}
    comparison_resp = generate_multifunction_response(query_comparison, sample_tools, early_stopping=False)
    comparison_resp = comparison_resp.get("output", "")
    if comparison_resp:
        resp = create_pydantic_parser(comparison_resp, Comparison)
        if resp:
            comparison_dict = resp.dict()
    return comparison_dict

def analyze_language(resume_content, category, industry, timeout=20):

    """ Analyzes the resume for its language aspects including tone, diction, syntax, etc. """


    language_dict= {"rating":"", "reason":""}
    if category=="tone" or category=="syntax":
        query_language="""Assess the {category} of the resume. 

        If you're asked to assess the syntax, look for power verbs, an active voice, and word phrasing that are most appropriate for a resume. Remember complete sentences are not necessary for resume, and short and impactful statements are usually better. 

        If you're asked to assess the tone, generally there should be a formal and respectful tone, but not too stiff or distant. Slang, jargon, humor, and negativity are not good signs.
        
        Output the following metrics: ["poor", "good", "excellent"] and provide your reasoning. Your reasoning should be about a sentence long.

        resume: {resume_content}
         """
        prompt_template = ChatPromptTemplate.from_template(query_language)
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
        model_parser = prompt | llm.with_structured_output(schema=Language)
        generator =     ({"resume_content":RunnablePassthrough(), "category":RunnablePassthrough()} 
                        | prompt_template
                        | model_parser)
        
        def run_parser():
            try: 
                response =generator.invoke({"resume_content":resume_content, "category":category})
                return response
            except Exception as e:
                print(e)
                return None
        return future_run_with_timeout(run_parser, timeout=timeout)
        # try:
        #     language_dict = generator.invoke({"resume_content":resume_content, "category":category})
        # except openai.BadRequestError as e:
        #     if "string too long" in str(e):
        #         #TODO: shorten content!
        #         pass
        # language_resp = asyncio_run(lambda: create_smartllm_chain(query_language, n_ideas=1), timeout=5)
        # if language_resp:
        #     language_dict = asyncio_run(lambda:create_pydantic_parser(language_resp, Language), timeout=5)
    elif category=="readability":
        score= readability_checker(resume_content).get("flesch_kincaid_grade", None)
        readability_dict = {"advocate":20, "fitness":19.5, "public-relations":18.8, "healthcare":18.8, "arts":18.1, "digital-media":18.1, "banking":18, "information-technology":17.9, "finance":17.5, "hr":17.4, "accountant":17.3, "business-development":17.2, "bpo":17.2, "apparel":17.2, "teacher":17, "agriculture":16.5, "engineering":16.4, "consultant":16, "designer":16.3, "aviation":16.3, "automobile":15, "sales":14.8, "chef":14.7}
        avg_score = readability_dict.get(industry, 15)
        if score:
            if score<=avg_score:
                if avg_score-score<5:
                    language_dict={"rating":"excellent", "reason":""}
                elif 5<=avg_score-score<10:
                    language_dict={"rating":"good", "reason":""}
                else:
                    language_dict={"rating":"poor", "reason":"Consider lengthening your phrases <br> and adding more multi-syllable words"}
            else:
                if score-avg_score<5:
                    language_dict={"rating":"excellent", "reason":""}
                elif 5<=score-avg_score<10:
                    language_dict={"rating":"good", "reason":""}
                else:
                    language_dict={"rating":"poor", "reason":"Consider shortening your phrases <br> and simplify your word choices <br> to make your resume more readable"}
        else:
            language_dict={"rating":"", "reason":""}
        return language_dict 


def generate_impression(resume_content, jobs):

    """ Generates an overall impression of the resume according to some qualifiable metrics. """

    #NOTE: this prompt uses self-reflective thinking by answering questions
    query_impression= f""" You are provided with a candidate's resume along with a list of jobs they are seeking. 
    
    Reflect how well as a whole the resume reflects the jobs. Some of the questions you should answer include:

    1. Does the candidate have the skills or qualifications for the jobs they are seeking? \ 

    2. Does the candidate have the work experience for the jobs they are seeking? \

    3. Does the summary or objective section of the resume reflect the jobs they are seeking? \

    candidate's resume: {resume_content} \
    
    jobs the candidate is seeking: {jobs} \

    Your final analysis should be about 50-100 words long summarizing your impression of the candidate's resume.
     
    DO NOT USE ANY TOOLS! """


    # impression_resp = asyncio_run(lambda: generate_multifunction_response(query_impression, create_search_tools("google", 1), early_stopping=False), timeout=10)
    impression_resp = generate_multifunction_response(query_impression, create_search_tools("google", 1))
    return impression_resp.get("output", "") if impression_resp else ""


def analyze_resume_type(resume_content, ):

    """Categorizes the resume as either functional or chronological"""

    query_type = f"""Your task is to provide an assessment of a resume delimited by {delimiter} characters. 

    resume: {delimiter}{resume_content}{delimiter} \n

    Research the resume closely and assess what type of resume it is written in. It should be one of the following: 
    
    chronological:A chronological resume, also known as a reverse-chronological resume, lists your work experience in reverse chronological order, with your most recent job at the top. 
    This format is a good choice for candidates with a lot of relevant experience and achievements. 
      A chronological resume should have emphasis on work experience and accomplishment, meaning work experience is placed before education and skills. \n

    functional:A functional resume, also known as a skills-based resume, highlights your skills and areas of expertise instead of your work history. 
    It's a good choice if you're a recent graduate with little work experience, changing careers, or have a gap in your work history
      A functional resume should emphasize skills, projects, and accomplishments, where work experience should be after these sections.

      Note a resume can be mix of chronological and functional type.

    """
    response= create_smartllm_chain(query_type, n_ideas=1)
    if response:
        # type_dict = asyncio_run(lambda: create_pydantic_parser(response, ResumeType), timoue=5)
        type_dict = create_pydantic_parser(response, ResumeType)
        return type_dict.dict()["type"]  if type_dict else ""
    else:
        return ""

def tailor_resume(resume_dict={}, job_posting_dict={}, field_name="general",  p=None, loading_func=None):

    print(f'start tailoring....{field_name}')
    for _ in range(5):
        time.sleep(0.1)  # Simulate time-consuming task
        p.increment(10)  # Update progress in steps of 10%
        loading_func(p.progress)

    details = resume_dict[field_name]
    about_job = job_posting_dict["about_job"]
    job_posting = job_posting_dict["content"]
    resume_content= resume_dict["resume_content"]
    job_requirements = ", ".join(job_posting_dict["qualifications"]) if job_posting_dict["qualifications"] is not None else "" + ", ".join(job_posting_dict["responsibilities"]) if job_posting_dict["responsibilities"] is not None else ""
    job_requirements = about_job if not job_requirements else job_requirements
    # company_description = job_posting_dict["company_description"]
    p.increment(10)  # Update progress 
    loading_func(p.progress)
    if field_name=="included_skills":
        # response = asyncio_run(lambda: tailor_skills(job_skills, details, job_requirements, ), timeout=30, max_try=1)
        response = tailor_skills(job_posting, details, job_requirements, )
        response_dict=response.dict() if response else {}
        p.increment(20)  # Update progress 
        loading_func(p.progress)
        # transferable_skills = asyncio_run(lambda:suggest_transferable_skills(resume_content, job_requirements), timeout=5)
        # if transferable_skills:
        #     response_dict.update({"transferable_skills":transferable_skills})
        # p.increment(10)  # Update progress 
        # loading_func(p.progress)
    elif field_name=="summary_objective":
        job_title = job_posting_dict["job"] 
        # response = asyncio_run(lambda:tailor_objective(about_job, details, resume_content, job_title,), timeout=30, max_try=1)
        response = tailor_objective(about_job, details, resume_content, job_title,)
        response_dict=response.dict() if response else {}
        p.increment(20)  # Update progress 
        loading_func(p.progress)
    elif field_name=="educations":
        response_dict={}
    else:
        # print("bullet point details", details)
        # if len(details)>1:
        if isinstance(details, list):
            try:
                details = [detail["description"] for detail in details]
            except Exception:
                pass   
        response_dict = tailor_bullet_points(field_name, details, job_requirements, )
        p.increment(30)  # Update progress 
        loading_func(p.progress)
        # else:
        #     response_dict = "please add more bullet points first"
    match = match_resume_job(resume_dict[field_name], job_posting, field_name)
    match_dict = match.dict() if match else  {"evaluation":None, "percentage":None}
    try:
        response_dict.update(match_dict)
    except Exception as e:
        pass
    p.increment(10)  # Update progress 
    loading_func(p.progress)
    return response_dict
    # if response_dict:
    #     print(f"successfully tailored {field_name}")
    #     st.session_state[f"tailored_{field_name}_{idx}"]=response_dict
    # else:
    #     print(f"failed to tailor {field_name}")
    #     st.session_state[f"tailored_{field_name}_{idx}"]="please try again"
    # return st.session_state.tailor_dict



# def concat_skills(skills_list, skills_str=""):
#     for s in skills_list:
#         skill = s["skill"] 
#         example = s["example"]
#         skills_str+="(skill: " +skill + ", example: "+ example + ")"
#     return skills_str

def tailor_skills( my_skills, job_requirement, timeout=10):

    """ Creates a list of relevant skills, irrelevant skills, and transferable skills according to the skills required in a job description"""
  
    
    skills_prompt = """ Your task is to compare the skills section of the resume and skills required in the job description. 
    
    You are given the information below: a list of skills in a resume and job requirements
    
    skill list in the resume: {my_skills} \
    
    job requirements: {job_requirement} \

    Step 1: Make a list of irrelevant skills that can be excluded from the resume based on the skills in the job requirements.
    
    These are skills that are in the resume that do not align with the requirement of the job description. Keep in mind some skills are transferable skills and they should still be relevant.
    
    Step 2: Make a list of skills in the resume that are most relevant to the skills wanted in the job description. 

    These are usally skills that exist in both the resume and job posting. 


    Output using the following format:
        Step 1: <step 1 reasoning and answer>
        Step 2: <step 2 reasoning and answer>

    """ 
    # Step 3: Make a list of transferable skills based on the resume and job description. 

    # These are the skills that can be transferred from one job to another, and they should not already exist in the reusme. 
        # Step 3: <step 3 result>

    prompt_template = ChatPromptTemplate.from_template(skills_prompt)
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
    model_parser = prompt | llm.with_structured_output(schema=SkillsRelevancy)
    generator =     ({"my_skills":RunnablePassthrough(), "job_requirement":RunnablePassthrough()} 
                     | prompt_template
                     | model_parser)
    
    def run_parser():
        try: 
            response = generator.invoke({"my_skills":my_skills,  "job_requirement":job_requirement})
            print(response)
            return response
        except Exception as e:
            print(e)
            return None
    return future_run_with_timeout(run_parser)
    # try:
    #     response = generator.invoke({"my_skills":my_skills, "required_skills":required_skills, "job_requirement":job_requirement})
    # except openai.BadRequestError as e:
    #     if "string too long" in str(e):
    #         #TODO:shorten content!
    #         response = ""
    # # print(response)
    # return response


def tailor_objective(job_requirements, my_objective, resume_content, job_title, timeout=20):

    """ Generates replacements for words and phrases in the summary objective section according to the job description"""


    # template_string = """ 
    
    # Your task is to research words and phrases from the objective/summary section of the resume that can be substitued so it aligns better to an open job position.

    # Please follow the below steps:

    # Step 1: find relevant information in the resume content that can be matched to the job requirements in a job posting. 

    # The most direct type of relevant information are words/phrases that the resume content and job requirements share. 

    # Other type of relevant information can be induced based on skills and work experience for example.
    
    # resume content: {resume_content} \n

    # job requirements: {job_requirements} \n

    # """
    # Step 2:  you are provided withs a resume objective and the job title, if available.

    #     job title: {job_title} \n

    #     resume objective: {my_objective} 

    #     Please follow the following format and the relevant information from Step 1 to make appropriate changes to the resume objective. When you generate your response, make sure all replacements are unique and DO NOT make changes based on arbitrary choice of wording.
        
    #     Always follow relevant information from Step 1 to make relevant changes. 

    #     1. Replaced_words: <the phrase/words in the resume objective to be replaced> ; Substitution: <the substitution for the phrase/words>

    model_parser1 = llm | StrOutputParser()
    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert extraction algorithm. "
            "Only extract relevant information from the text. "
        ),
        # Please see the how-to about improving performance with
        # reference examples.
        # MessagesPlaceholder('examples')
        ("human", "{content}"),
            ]
        )
    template_string2= """ 
        Your goal is to change the resume objective section of the resume to match the job requirements in a job posting.

        Step 1: Find relevant information in the resume content that can be matched to the job requirements. 

        For example, they can be words/phrases that the resume and job requirements share, or experiences and skills in the resume that are relevant to the job requirements.
        
        Step 2: Revise the summary objective, make it relevant to the job posting but also in context of the resume.
        
        Step 3: Propose replacements and substitions following the format below:
    
        1. Replaced_words: <the phrase/words in the resume objective to be replaced> ; Substitution: <the substitution for the phrase/words>

        Make sure the replaced words are verbatim from the resume objective and substitutions are appropriate and relevant to the job posting.

        Your final output should be:

        Step 1: <reasoning and answer>
        Step 2: <reasoning and answer>
        Step 3: <answer in the given format> 

        resume content: {resume_content} \n

        job requirements: {job_requirements} \n
        
    """
        # resume's summary objective: {my_objective}
    # print(resume_content)
    model_parser = prompt |  llm.with_structured_output(schema=Replacements)
    # prompt_template = ChatPromptTemplate.from_template(template_string)
    prompt_template2 = ChatPromptTemplate.from_template(template_string2)
    # generator =     ({"resume_content":RunnablePassthrough(), "job_requirements":RunnablePassthrough(), "job_title":RunnablePassthrough(), "my_objective":RunnablePassthrough()} 
    #                  | prompt_template
    #                  | model_parser)
    generator =     (
        # {"resume_content":RunnablePassthrough(), "job_requirements":RunnablePassthrough()} 
        #              | prompt_template
                      {"resume_content":RunnablePassthrough(), "job_requirements":RunnablePassthrough(), }
                     | prompt_template2
                     | model_parser)
    
    def run_parser():
        try: 
            response = generator.invoke({"resume_content":resume_content, "job_requirements":job_requirements,})
            print(response)
            return response
        except Exception as e:
            print(e)
            return None
    return future_run_with_timeout(run_parser, timeout=timeout)




def tailor_bullet_points(field_name, field_detail,  job_requirements, ):

    """ Ranks the bullet points according to relevancy to the job description. Outputs a dictionary of ranked section with reasoning (for display) along with a the ranked section as a comma separated list (for applying changes)."""

    rank_prompt = f"""Please rank content of the {field_name} section of the resume with respective to the job requirements.
        For example, if a candidate has experience in SQL and SQL is also a skill required in the job, then this experience should be ranked higher on the list.
        If a candidate has experience in customer service but this is not part of the role of the job, then this experience should be ranked lower. 
        Sometimes the section may contain several lists of descriptions. Please treat each description as a separate content to be ranked.
        {field_name} section: {field_detail} \
        job requirements: {job_requirements} \
 
        Output in the following format:
        Reranking suggestions: 
        - <first ranked content and your reasoning> \
        - <second reanked content and your reasoning> \
        ....so on. 
        DO NOT USE ANY TOOLS.

    """
    # ranked_dict={}
    # ranked = asyncio_run(lambda: generate_multifunction_response(rank_prompt, create_search_tools("google", 1), ), timeout=10)
    ranked = generate_multifunction_response(rank_prompt, create_search_tools("google", 1))
    # if ranked:
    #     ranked_dict.update({"ranked":ranked})
    #     template="""Look for Reranked section and list the details verbatim in the order that they appear. {ranked}"""
    #     # query_dict = {"ranked":ranked}
    #     # ranked_list = asyncio_run(lambda: create_comma_separated_list_parser(input_variables=["ranked"], base_template=template, query_dict=ranked_dict), timeout=5)
    #     ranked_list = create_comma_separated_list_parser(input_variables=["ranked"], base_template=template, query_dict=ranked_dict)
    #     if ranked_list:
    #         ranked_dict.update({"ranked_list":ranked_list})
    # ranked_dict = {"ranked":ranked, "ranked_list":ranked_list}
    return ranked.get("output", "") if ranked else ""



# @memoized
def research_resume_type(resume_dict={}, job_posting_dict={}, )-> str:
    
    """ Researches the type of resume most suitable for the applicant. 
    
        Args:
        
            resume_file(str): path of the resume

            posting_path(str): path of the job posting

        Returns:
        
            type of resume: functional or chronological
            
    """

    jobs = resume_dict["work_experience"]
    if job_posting_dict:
        desired_jobs = [job_posting_dict["job"]]
    else:
        desired_jobs=resume_dict["pursuit_jobs"]
    jobs_list=[]
    for job in jobs:
        jobs_list.append(job["title"])
    # similar_jobs = asyncio_run(lambda: extract_similar_jobs(jobs_list, desired_jobs))
    similar_jobs = extract_similar_jobs(jobs_list, desired_jobs)
    if similar_jobs:
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
    else:
        resume_type=""  
    # year_graduated = resume_dict["education"]["graduation_year"]
    # years_since_graduation = calculate_graduation_years(year_graduated)
    # if (years_since_graduation!=-1 and years_since_graduation-total_years_work>2) or (years_since_graduation!=-1 and years_since_graduation<=2 ):
    #     resume_type = "functional"
    #     print("RESUME TYPE: FUNCTIONAL")
    # elif total_years_work<2:
    #     resume_type = "chronological"
    #     print("RESUME TYPE: CHRONOLOGICAL")
    return resume_type


def reformat_resume(template_path, ):

    """"Reformats user profile information with a resume template"""
    def split_at_letter_number(s):
    # Use a regular expression to split at the point where a letter is followed by a digit
        match = re.match(r"([a-zA-Z]+)(\d+)", s)
        if match:
            return match.groups()  # Returns a tuple of the split parts
        return s  # If no match is found, return the original string

    print("reformatting resume")
    selected_fields = st.session_state["selected_fields"]
    info_dict = st.session_state["profile"]
    filename = os.path.basename(template_path)
    templatex = split_at_letter_number(filename)
    template_type, template_num = templatex[0], templatex[1]
    # print(template_type, template_num)
    # output_dir = st.session_state["users_download_path"]
    # end_path = os.path.join(output_dir, filename)
    if STORAGE=="CLOUD":
        # Download the file content from S3 into memory
        s3_object = s3.get_object(Bucket=bucket_name, Key=template_path)
        template_path = BytesIO(s3_object['Body'].read())
    jinja_env = jinja2.Environment()
    jinja_env.trim_blocks = True
    jinja_env.lstrip_blocks = True
    doc_template = DocxTemplate(template_path)
    context={}
    if "Contact" in selected_fields and info_dict["contact"] is not None:      
        func = lambda key, default: default if info_dict["contact"][key]==None or info_dict["contact"][key]=="" else info_dict["contact"][key]
        rich_text = RichText()
        personal_context = {
            "NAME": func("name", ""),
            "CITY": func("city", ""),
            "STATE": func("state", ""),
            "PHONE": func("phone", ""),
            "EMAIL": func("email", ""),
            # "WEBSITES": func("links", ""),
        }
        context.update(personal_context)
        WEBSITES = info_dict["contact"].get("links", [])
        for website in WEBSITES:
            display_text = website["display"] if website["display"] else website["url"]
            rich_text.add(display_text, url_id=doc_template.build_url_id(website["url"]))
        context.update({"WEBSITES": rich_text})
    func = lambda key, default: default if info_dict[key]=="" or info_dict[key]==[] or info_dict[key]==None else info_dict[key]
    if "Summary Objective" in selected_fields and info_dict["summary_objective"] is not None:
        context.update({"show_summary":True, "SUMMARY": func("summary_objective", ""), 
                         "PURSUIT_JOB": func("pursuit_jobs", ""),})      
    if "Education" in selected_fields and info_dict["educations"] is not None:
        context.update({"show_education":True, "EDUCATIONS": func("educations", "")})
    if "Work Experience" in selected_fields and info_dict["work_experience"] is not None:
         context.update({"show_work_experience":True,"WORK_EXPERIENCE": func("work_experience", "")})
    if "Skills" in selected_fields and info_dict["included_skills"] is not None:
        context.update({"show_skills":True,"SKILLS": func("included_skills", ""),})
    if "Professional Accomplishment" in selected_fields and info_dict["qualifications"] is not None:
        context.update({"show_pa":True, "PA": func("qualifications", ""),})
    if "Certifications" in selected_fields and info_dict["certifications"] is not None:
        context.update({"show_certifications":True,"CERTIFICATIONS": func("certifications", ""),})
    if "Projects" in selected_fields and info_dict["projects"] is not None:
        # context.update({"show_projects":True,"PROJECTS":func("projects", "")})
        # Create RichText objects for each project link
        PROJECTS = info_dict["projects"]
        if PROJECTS:
            for project in PROJECTS:
                LINKS = project["links"]
                rich_text = RichText()
                for link in LINKS:
                    display_text = link["display"] if link["display"] else link["url"]
                    rich_text.add(display_text, url_id=doc_template.build_url_id(link["url"]))
                project["rich_link"] = rich_text
            print(PROJECTS)
            context.update({"show_projects":True, "PROJECTS": PROJECTS})
    if "Awards & Honors" in selected_fields and info_dict["awards"] is not None:
        context.update({"show_awards":True,"AWARDS": func("awards", "")})
    # text_box_contents = read_text_boxes(template_path)
    #  # Render each text box template with the context
    # rendered_contents = [render_template(content, context) for content in text_box_contents]
    # # Save the rendered content into a new .docx file
    # save_rendered_content(rendered_contents, end_path)
    doc_template.render(context)
    # if STORAGE=="LOCAL":
    #     doc_template.save(end_path) 
    # elif STORAGE=="CLOUD":
    # Save the rendered template to a BytesIO object
    output_stream = BytesIO()
    doc_template.save(output_stream)
    output_stream.seek(0)    
    # # Upload the BytesIO object to S3
    # s3.put_object(Bucket=bucket_name, Key=end_path, Body=output_stream.getvalue())
    # Write to a temporary file
    # Create a temporary file with a custom prefix and suffix
    fd, end_path = tempfile.mkstemp(prefix=f"{template_type}_{template_num}_", suffix=".docx",)
    # Write to the temporary file
    with os.fdopen(fd, 'wb') as temp_file:
    # with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
        temp_file.write(output_stream.getvalue())
        temp_file.seek(0)  # Reset stream position to the beginning if needed
        # end_path = temp_file.name
        print(f"Temporary file created at: {end_path}")
    return end_path
    

# def readability_checker(content):

#     """ Checks the content readability"""

#     stats = dict(
#             # flesch_reading_ease=ts.flesch_reading_ease(w),
#             # smog_index = ts.smog_index(w),
#             flesch_kincaid_grade=ts.flesch_kincaid_grade(content),
#             # automated_readability_index=ts.automated_readability_index(w),
#             # coleman_liau_index=ts.coleman_liau_index(w),
#             # dale_chall_readability_score=ts.dale_chall_readability_score(w),
#             # linsear_write_formula=ts.linsear_write_formula(w),
#             # gunning_fog=ts.gunning_fog(w),
#             # word_count=ts.lexicon_count(w),
#             # difficult_words=ts.difficult_words(w),
#             # text_standard=ts.text_standard(w),
#             # sentence_count=ts.sentence_count(w),
#             # syllable_count=ts.syllable_count(w),
#             # reading_time=ts.reading_time(w)
#     )
#     return stats
    
def match_resume_job(resume_content:str, job_posting_content:str, field_name:str):

    """ Generates a resume job comparison, including percentage comparison"""
    # field_names=["included_skills", "summary_objective", "education"]
    # resume_content = resume_dict[field_name]
    # job_posting = job_posting_dict["content"]
    # if "matching" not in st.session_state:
    #     st.session_state["matching" ]= {}
    #     st.session_state.matching.update({f"{field_name}_eval": "" for field_name in field_names})
    prompt = """Act as a Application Tracking System.
    
    Step 1: compare the candidate resume {field_name} to a job role description.
    
    resume {field_name} content: {resume_content} \n

    job role description: {job_posting} \n

    Step 2: generate a percentage comparison of resume {field_name}.

    Use the following format:
        Step 1: <step 1 answer>
        Step 2: <step 2 answer>

    """
    prompt_template = ChatPromptTemplate.from_template(prompt)
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
        # MessagesPlaceholder('examples')
        ("human", "{content}"),
            ]
        )
    model_parser =prompt | llm.with_structured_output(schema=MatchResumeJob)
    generator =   (
        {"resume_content":RunnablePassthrough(), "job_posting":RunnablePassthrough(), "field_name":RunnablePassthrough()} 
                     | prompt_template
                     | model_parser)
    try:
        # Call the run_parser_with_timeout function with tenacity
        response = tenacity_run_with_timeout({"resume_content":resume_content, "job_posting":job_posting_content, "field_name":field_name}, generator)
        print(response)
        # response = response.dict()
        return response
        # st.session_state.matching.update({f"{field_name}_eval":response["evaluation"]})
        # st.session_state.matching.update({f"{field_name}_percentage":response["percentage"]})
    except Exception as e:
        print(f"Error or Timeout occurred: {e}")
        return None
        # st.session_state.matching.update({f"{field_name}_eval": None})
        # st.session_state.matching.update({f"{field_name}_percentage":None})


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


