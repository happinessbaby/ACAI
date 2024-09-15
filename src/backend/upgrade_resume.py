import os
import openai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from utils.basic_utils import count_length
from utils.common_utils import search_related_samples,  extract_similar_jobs, suggest_transferable_skills
from utils.langchain_utils import  generate_multifunction_response, create_smartllm_chain, create_pydantic_parser, create_comma_separated_list_parser
from utils.agent_tools import create_search_tools, create_sample_tools
from typing import Dict, List, Optional, Union
from docxtpl import DocxTemplate, RichText
# from operator import itemgetter
# from docx import Document
# from docx.shared import Inches
import re
from utils.pydantic_schema import ResumeType, Comparison, SkillsRelevancy, Replacements, Language
from dotenv import load_dotenv, find_dotenv
from io import BytesIO
from utils.aws_manager import get_client
import tempfile
import textstat as ts
from langchain_core.prompts import ChatPromptTemplate,  PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from utils.async_utils import asyncio_run
import time as time
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


def evaluate_resume(resume_dict={},  type="general", idx=-1, details=None, p=None, loading_func=None) -> Dict[str, str]:


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
        if details:
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
    return response


    


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
    comparison_resp = asyncio_run(lambda:generate_multifunction_response(query_comparison, sample_tools, early_stopping=False), timeout=5)
    if comparison_resp:
        comparison_dict = asyncio_run(lambda:create_pydantic_parser(comparison_resp, Comparison), timeout=5)
    return comparison_dict

def analyze_language(resume_content, category, industry):

    """ Analyzes the resume for its language aspects including tone, diction, syntax, etc. """


    language_dict= {"rating":"", "reason":""}
    if category=="tone" or category=="syntax":
        query_language="""Assess the {category} of the resume. 

        If you're asked to assess the syntax, look for power verbs, an active voice, and word phrasing that are most appropriate for a resume. Remember complete sentences are not necessary for resume, and short and impactful statements are usually better. 

        If you're asked to assess the tone, generally there should be a formal and respectful tone, but not too stiff or distant. Slang, jargon, humor, and negativity are not good signs.
        
        Output the following metrics: ["bad", "good", "great"] and provide your reasoning. Your reasoning should be about a sentence long.

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
        try:
            language_dict = generator.invoke({"resume_content":resume_content, "category":category})
        except openai.BadRequestError as e:
            if "string too long" in str(e):
                #TODO: shorten content!
                pass
        # language_resp = asyncio_run(lambda: create_smartllm_chain(query_language, n_ideas=1), timeout=5)
        # if language_resp:
        #     language_dict = asyncio_run(lambda:create_pydantic_parser(language_resp, Language), timeout=5)
    elif category=="readability":
        score= readability_checker(resume_content).get("flesch_kincaid_grade", None)
        readability_dict = {"advocate":20, "fitness":19.5, "public-relations":18.8, "healthcare":18.8, "arts":18.1, "digital-media":18.1, "banking":18, "information-technology":17.9, "finance":17.5, "hr":17.4, "accountant":17.3, "business-development":17.2, "bpo":17.2, "apparel":17.2, "teacher":17, "agriculture":16.5, "engineering":16.4, "consultant":16, "designer":16.3, "aviation":16.3, "automobile":15, "sales":14.8, "chef":14.7}
        avg_score = readability_dict.get(industry, 17)
        if score:
            if score<=avg_score:
                if avg_score-score<5:
                    language_dict={"rating":"great", "reason":""}
                elif 5<=avg_score-score<10:
                    language_dict={"rating":"good", "reason":""}
                else:
                    language_dict={"rating":"bad", "reason":"Consider lengthening your phrases <br> and adding more multi-syllable words"}
            else:
                if score-avg_score<5:
                    language_dict={"rating":"great", "reason":""}
                elif 5<=score-avg_score<10:
                    language_dict={"rating":"good", "reason":""}
                else:
                    language_dict={"rating":"bad", "reason":"Consider shortening your phrases <br> and simplify your word choices <br> to make your resume more readable"}
        else:
            language_dict={"rating":"", "reason":""}
    return language_dict if isinstance(language_dict, dict) else language_dict.dict()


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
    return impression_resp if impression_resp else ""


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
    response=asyncio_run(lambda: create_smartllm_chain(query_type, n_ideas=1), timeout=10)
    if response:
        # type_dict = asyncio_run(lambda: create_pydantic_parser(response, ResumeType), timoue=5)
        type_dict = create_pydantic_parser(response, ResumeType)
        return type_dict["type"]
    else:
        return ""

def tailor_resume(resume_dict={}, job_posting_dict={}, type=None, field_name="general", idx=-1, details=None, p=None, loading_func=None):

    print(f'start tailoring....{field_name}')
    for _ in range(5):
        time.sleep(0.1)  # Simulate time-consuming task
        p.increment(10)  # Update progress in steps of 10%
        loading_func(p.progress)

    about_job = job_posting_dict["about_job"]
    job_skills = job_posting_dict["skills"] 
    resume_content= resume_dict["resume_content"]
    job_requirements = ", ".join(job_posting_dict["qualifications"]) if job_posting_dict["qualifications"] is not None else "" + ", ".join(job_posting_dict["responsibilities"]) if job_posting_dict["responsibilities"] is not None else ""
    job_requirements = about_job if not job_requirements else job_requirements
    # company_description = job_posting_dict["company_description"]
    p.increment(10)  # Update progress 
    loading_func(p.progress)
    if field_name=="included_skills":
        # response = asyncio_run(lambda: tailor_skills(job_skills, details, job_requirements, ), timeout=30, max_try=1)
        response = tailor_skills(job_skills, details, job_requirements, )
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
        p.increment(30)  # Update progress 
        loading_func(p.progress)
    if type=="bullet_points":
        # print("bullet point details", details)
        if len(details)>1:
            response_dict = tailor_bullet_points(field_name, details, job_requirements, )
            p.increment(30)  # Update progress 
            loading_func(p.progress)
        else:
            response_dict = "please add more bullet points first"
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

def tailor_skills(required_skills, my_skills, job_requirement, ):

    """ Creates a list of relevant skills, irrelevant skills, and transferable skills according to the skills required in a job description"""
  
    
    skills_prompt = """ Your task is to compare the skills section of the resume and skills required in the job description. 
    
    You are given several core pieces of information below: a list of skills in a resume, a list of skills wanted in a job posting, and job requirements
    
    skill list in the resume: {my_skills} \
    
    skill list in the job description: {required_skills} \
    
    job requirements: {job_requirement} \

    Step 1: Make a list of irrelevant skills that can be excluded from the resume based on the skills in the job description and job requirements.
    
    These are skills that are in the resume that do not align with the requirement of the job description. 
    
    Step 2: Make a list of skills in the resume that are most relevant to the skills wanted in the job description. 

    These are usally skills that exist in both the resume and job posting. 

    Step 3: Make a list of skills that are in the job description that can be added to the resumes. These are usually transferable skills, but can also be other technical skills. 

    Use the following format:
        Step 1: <step 1 reasoning>
        Step 2: <step 2 reasoning>
        Step 3: <step 3 reasoning>

    Make sure lists from both steps include only skills from the resume, and provide your reasoning.

    """
    # These additional skills are ones that are not included in the resume but would benefit the candidate if they are added. \
    # For example, a candidate may have SQL and communication skills in their resume. The job description asks for communication skills but not SQL skill. SQL is the irrelevant skill in the resume since it's not in the job description.\
    # For example, a candidate may have SQL and communication skills in their resume. The job description asks for communication skills too. Communication is the relevant skill that exists in both the resume and job description. \
    # For example, a candidate may have SQL and communication skills in their resume. The job description asks for communication and Python skills. Python is the additional skill that may raise the chance of the candidate getting the job offer. \

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
    generator =     ({"my_skills":RunnablePassthrough(), "required_skills":RunnablePassthrough(), "job_requirement":RunnablePassthrough()} 
                     | prompt_template
                     | model_parser)
    try:
        response = generator.invoke({"my_skills":my_skills, "required_skills":required_skills, "job_requirement":job_requirement})
    except openai.BadRequestError as e:
        if "string too long" in str(e):
            #TODO:shorten content!
            response = ""
    # print(response)
    return response


def tailor_objective(job_requirements, my_objective, resume_content, job_title):

    """ Generates replacements for words and phrases in the summary objective section according to the job description"""


    template_string = """ 
    
    Your task is to research words and phrases from the objective/summary section of the resume that can be substitued so it aligns better to an open job position.

    Please follow the below steps:

    Step 1: find relevant information in the resume content that can be matched to the job requirements in a job posting. 

    The most direct type of relevant information are words/phrases that the resume content and job requirements share. 

    Other type of relevant information can be induced based on skills and work experience for example.
    
    resume content: {resume_content} \n

    job requirements: {job_requirements} \n



    """
    # Step 2:  you are provided withs a resume objective and the job title, if available.

    #     job title: {job_title} \n

    #     resume objective: {my_objective} 

    #     Please follow the following format and the relevant information from Step 1 to make appropriate changes to the resume objective. When you generate your response, make sure all replacements are unique and DO NOT make changes based on arbitrary choice of wording.
        
    #     Always follow relevant information from Step 1 to make relevant changes. 

    #     1. Replaced_words: <the phrase/words in the resume objective to be replaced> ; Substitution: <the substitution for the phrase/words>

    template_string2= """ You are provided withs a resume objective and the job title, if available.

        job title: {job_title} \n

        resume objective: {my_objective} 

        relevant information from a job posting: {relevant_information}

        Please follow the following format and the relevant information from a job posting with to make appropriate changes to the resume objective. When you generate your response, make sure all replacements are unique and DO NOT make changes based on arbitrary choice of wording.
        
        Always follow relevant information you're provided to make relevant changes and make sure the replaced words are verbatim from the resume objective.

        1. Replaced_words: <the phrase/words in the resume objective to be replaced> ; Substitution: <the substitution for the phrase/words>

    """
    model_parser1 = llm | StrOutputParser()
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
    print(resume_content)
    model_parser = prompt |  llm.with_structured_output(schema=Replacements)
    prompt_template = ChatPromptTemplate.from_template(template_string)
    prompt_template2 = ChatPromptTemplate.from_template(template_string2)
    # generator =     ({"resume_content":RunnablePassthrough(), "job_requirements":RunnablePassthrough(), "job_title":RunnablePassthrough(), "my_objective":RunnablePassthrough()} 
    #                  | prompt_template
    #                  | model_parser)
    generator =     ({"resume_content":RunnablePassthrough(), "job_requirements":RunnablePassthrough()} 
                     | prompt_template
                     | {"relevant_information":model_parser1, "job_title":RunnablePassthrough(), "my_objective":RunnablePassthrough()}
                     | prompt_template2
                     | model_parser)
    try:
        response = generator.invoke({"resume_content":resume_content, "job_requirements":job_requirements, "job_title":job_title, "my_objective":my_objective})
    except openai.BadRequestError as e:
        if "string too long" in str(e):
            #TODO:shorten content!
            response = ""
    print(response)
    # response = asyncio_run(lambda:create_pydantic_parser(content={"resume_content":resume_content, "job_requirements":job_requirements, "job_title":job_title, "my_objective":my_objective}, schema=Replacements, previous_chain=generator), timeout=20)
    # print(response)
    # print(prompt_template.messages[0].prompt.input_variables)
    # message = prompt_template.format_messages(resume_content=resume_content, job_requirements=job_requirements, job_title=job_title, my_objective=my_objective)
    # response = await llm.ainvoke(message)
    # print(response)
    return response



def tailor_bullet_points(field_name, field_detail,  job_requirements, ):

    """ Ranks the bullet points according to relevancy to the job description. Outputs a dictionary of ranked section with reasoning (for display) along with a the ranked section as a comma separated list (for applying changes)."""

    rank_prompt = f"""Please rank content of the {field_name} section of the resume with respective to the job requirements.
        For example, if a candidate has experience in SQL and SQL is also a skill required in the job, then this experience should be ranked higher on the list.
        If a candidate has experience in customer service but this is not part of the role of the job, then this experience should be ranked lower. 
        {field_name} section: {field_detail} \
        job requirements: {job_requirements} \

        Please provide your reasoning for your ranking process.  
        Output in the following format:
        Reranked section: - <reranked section verbatim without reasoning> \n
        reason: <your reasoning>
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
    return ranked



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
        jobs_list.append(job["job_title"])
    # similar_jobs = asyncio_run(lambda: extract_similar_jobs(jobs_list, desired_jobs))
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


def reformat_resume(template_path, ):

    """"Reformats user profile information with a resume template"""
    def split_at_letter_number(s):
    # Use a regular expression to split at the point where a letter is followed by a digit
        match = re.match(r"([a-zA-Z]+)(\d+)", s)
        if match:
            return match.groups()  # Returns a tuple of the split parts
        return s  # If no match is found, return the original string

    print("reformatting resume")
    try:
        selected_fields = st.session_state["selected_fields"]
        print(selected_fields)
        info_dict = st.session_state["profile"]
        filename = os.path.basename(template_path)
        templatex = split_at_letter_number(filename)
        template_type, template_num = templatex[0], templatex[1]
        print(template_type, template_num)
        output_dir = st.session_state["users_download_path"]
        end_path = os.path.join(output_dir, filename)
    except Exception:
        return ""
    if STORAGE=="CLOUD":
        # Download the file content from S3 into memory
        s3_object = s3.get_object(Bucket=bucket_name, Key=template_path)
        template_path = BytesIO(s3_object['Body'].read())
    doc_template = DocxTemplate(template_path)
    context={}
    if "Contact" in selected_fields:      
        func = lambda key, default: default if info_dict["contact"][key]==None or info_dict["contact"][key]=="" else info_dict["contact"][key]
        personal_context = {
            "NAME": func("name", ""),
            "CITY": func("city", ""),
            "STATE": func("state", ""),
            "PHONE": func("phone", ""),
            "EMAIL": func("email", ""),
            "LINKEDIN": func("linkedin", ""),
            "WEBSITE": func("websites", ""),
        }
        context.update(personal_context)
    if "Education" in selected_fields:
        func = lambda key, default: default if info_dict["education"][key]=="" or info_dict["education"][key]==[] or info_dict["education"][key]==None else info_dict["education"][key]
        education_context = {
            "show_education":True,
            "INSTITUTION": func("institution", ""),
            "DEGREE": func("degree", ""),
            "STUDY": func("study", ""),
            "GRAD_YEAR": func("graduation_year", ""),
            "GPA": func("gpa", ""), 
            "COURSEWORKS": func("coursework", ""),
        }
        context.update(education_context)
    func = lambda key, default: default if info_dict[key]=="" or info_dict[key]==[] or info_dict[key]==None else info_dict[key]
    if "Summary Objective" in selected_fields:
        context.update({"show_summary":True, "SUMMARY": func("summary_objective", ""), 
                         "PURSUIT_JOB": func("pursuit_jobs", ""),})      
    if "Work Experience" in selected_fields:
         context.update({"show_work_experience":True,"WORK_EXPERIENCE": func("work_experience", "")})
    if "Skills" in selected_fields:
        context.update({"show_skills":True,"SKILLS": func("included_skills", ""),})
    if "Professional Accomplishment" in selected_fields:
        context.update({"show_pa":True, "PA": func("qualifications", ""),})
    if "Certifications" in selected_fields:
        context.update({"show_certifications":True,"CERTIFICATIONS": func("certifications", ""),})
    if "Projects" in selected_fields:
        # context.update({"show_projects":True,"PROJECTS":func("projects", "")})
        # Create RichText objects for each project link
        PROJECTS = info_dict.get("projects", "")
        if PROJECTS:
            for project in PROJECTS:
                if project["link"]:
                    rt = RichText()
                    rt.add(project['link'], url_id=doc_template.build_url_id(project['link']))
                    project['link'] = rt  # Add this to the context as 'rich_link'
            context.update({"show_projects":True,
                'PROJECTS': PROJECTS,
            })
    if "Awards & Honors" in selected_fields:
        context.update({"show_awards":True,"AWARDS": func("awards", "")})
    # text_box_contents = read_text_boxes(template_path)
    #  # Render each text box template with the context
    # rendered_contents = [render_template(content, context) for content in text_box_contents]
    # # Save the rendered content into a new .docx file
    # save_rendered_content(rendered_contents, end_path)
    doc_template.render(context)
    if STORAGE=="LOCAL":
        doc_template.save(end_path) 
    elif STORAGE=="CLOUD":
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
    

def readability_checker(content):

    """ Checks the content readability"""

    stats = dict(
            # flesch_reading_ease=ts.flesch_reading_ease(w),
            # smog_index = ts.smog_index(w),
            flesch_kincaid_grade=ts.flesch_kincaid_grade(content),
            # automated_readability_index=ts.automated_readability_index(w),
            # coleman_liau_index=ts.coleman_liau_index(w),
            # dale_chall_readability_score=ts.dale_chall_readability_score(w),
            # linsear_write_formula=ts.linsear_write_formula(w),
            # gunning_fog=ts.gunning_fog(w),
            # word_count=ts.lexicon_count(w),
            # difficult_words=ts.difficult_words(w),
            # text_standard=ts.text_standard(w),
            # sentence_count=ts.sentence_count(w),
            # syllable_count=ts.syllable_count(w),
            # reading_time=ts.reading_time(w)
    )
    return stats
    


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


