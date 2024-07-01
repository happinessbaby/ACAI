from pydantic import BaseModel, Field, validator
from typing import Any, List, Union, Dict, Optional
import lancedb
from lancedb.pydantic import LanceModel, Vector
from utils.lancedb_utils import func

class Job(BaseModel):
    job_title: Optional[str] = Field(
        default="", description="the job position"
        )
    company: Optional[str] = Field(
        default="", description = "the company of the job position"
    )
    start_date: Optional[str] = Field(
      default=-1, description = "the start date of the job position if available"
      )
    end_date: Optional[str] = Field(
      default=-1, description = "the end date of the job position if available"
      )
    responsibilities: Optional[List[str]] = Field(
      default=[], description = """responsibilities or roles of the job position, do not leave out any content details"""
      )
class Jobs(BaseModel):
    """Extracted data about people."""
    # Creates a model so that we can extract multiple entities.
    jobs: List[Job] 


class Contact(BaseModel):
    name: Optional[str] = Field(
        default="", description="name of the candidate on the resume"
    )
    email: Optional[str]=Field(
        default="", description="email of the candidate on the resume"
    )
    phone: Optional[str]=Field(
default="", description="phone number of the candidate on the resume"
    )
    city: Optional[str]= Field(
default="", description="city of the candidate on the resume"
    )
    state: Optional[str] = Field(
default="", description="state of the candidate on the resume"
    )
    linkedin: Optional[str] = Field(
default="", description="linkedin address on the resume"
    )
    website: Optional[str]=Field(
default="", description="other website address on the resume"
    )
class Education(BaseModel):
    degree: Optional[str] = Field(
        default="", description="the highest degree of education, ignore any cerfications"
    )
    study: Optional[str] = Field(
        default="", description="the area of study including any majors and minors for the highest degree of education"
    )
    graduation_year:Optional[str] = Field(
        default="", description="the year of graduation from the highest degree of education"
    )
    gpa:Optional[int] = Field(
        default="", description="the gpa of the highest degree of graduation"
    )

class Project(BaseModel):
    title: Optional[str] = Field(
        default="", description="the name of the project or professional accomplishment, this should not be in the work experience section"
    )
    description: Optional[List[str]] = Field(
        default=[], description = "list of accomplishements or details about the project, this should not be in the work experience section"
    )
class Projects(BaseModel):
    projects: List[Project]

class Certification(BaseModel):
    title: Optional[str] = Field(
        default="", description="name of the certification"
    )
    issue_date: Optional[str] = Field(
        default="", description="the issuing date of the certification"
    )
    description: Optional[List[str]] = Field(
        default=[], descripton = "list of details about the certificate"
    )


class Skill(BaseModel):
    skill:Optional[str] = Field(
        default="", description="a skill listed "
    )
    example:Optional[str] = Field(
        default="", description="how the skill is demonstrated, an elaboration of the skill, or examples"
    )
    type: Optional[bool] = Field(
        default=False, description="categorize the skill, if hard skill, output True, else if soft skill, output False "
    )
class Skills(BaseModel):
    skills : List[Skill]

class ResumeFieldDetail(BaseModel):
    contact: Optional[Contact]
    work_experience:Optional[List[Job]]
    education: Optional[Education]
    projects: Optional[List[Project]]
    certifications: Optional[List[Certification]]

class ResumeFields(BaseModel):
    # contact: Optional[Contact]
    # work_experience:Optional[List[Job]]
    # education: Optional[Education]
    # projects: Optional[List[Project]]
    # certifications: Optional[List[Certification]]
    pursuit_jobs: Optional[List[str]] = Field(
        default= [], description="""the possible job(s) that the candidate is pursuing. Usually this is found in the summary or objective section of the resume"""
    )
    summary_objective_section: Optional[str] = Field(
        default = "", description="the summary of objective section of the resume"
    )
    skills_section: Optional[str] = Field(
        default="", description=" the skills section of the resume"
    )
    work_experience_section:  Optional[str] = Field(
        default="", description=" the work experience section of the resume"
    )
    accomplishments_section: Optional[str] = Field(
        default="", description="the professional accomplishment section of the resume that is not work experience"
    )
    awards_honors_section: Optional[str] = Field(
        default="", description = "the awards and honors sections of the resume"    
    )
    projects_section: Optional[str] = Field(
        default="", description = "the projects sections of the resume"    
    )


class Keywords(BaseModel):
    """Information about a job posting."""

    # ^ Doc-string for the entity Person.
    # This doc-string is sent to the LLM as the description of the schema Keywords,
    # and it can help to improve extraction results.

    # Note that:
    # 1. Each field is an `optional` -- this allows the model to decline to extract it!
    # 2. Each field has a `description` -- this description is used by the LLM.
    # Having a good description can help improve extraction results.

    job: Optional[str] = Field(
        default="", description="job position listed in the job posintg"
    )
    about_job: Optional[str] = Field(
        default="", description = "information about the job, usually listed at the top of the job posting"
    )
    company: Optional[str] = Field(
        default="", description = "name of the company or institution that's hiring"
    )
    company_description: Optional[str] = Field(
        default = "", description="information about the company that's hiring"
    )
    qualifications: Optional[List[str]] = Field(
        default=[], description="Traits or qualifications sought in a candidate"
    )
    responsibilities: Optional[List[str]] = Field(
        default=[], description="Duties and responsibilities for the job position"
    )
    salary: Optional[str] = Field(
        default="", description = "salary or salary range offered for the job, can be annually or hourly"    
    )
    on_site: Optional[bool] = Field(
        default=None, description = "whether of not the job is on-site. If on-site, output True. If remote, output False. If it's hybrid, it should be considered on-site too"
    )


class Comparison(BaseModel):
    closeness: Optional[str] = Field(
        default="", description = """closeness concluded in the content, 
        should be one of the following only: ["not close at all", "some similarity", "very similar", "identitical"]"""
    )

class ResumeType(BaseModel):
    type: Optional[str] = Field(
        default="", description="type of resume, should be either functional or chronological "
    )

class TailoredSkills(BaseModel):
    irrelevant_skills:Optional[List[str]] = Field(
        default=[], description="irrelevant skills, usually found in Step 1, these are skills that can be excluded from the resume"
    )
    relevant_skills: Optional[List[str]] = Field(
        default=[], description="relevant skills, usually found in Step 2, these are skills in the resume that are also in the job description "
    )
    additional_skills:Optional[List[str]] = Field(
        default=[], description="usually found in Step 3, these are skills that can be added on to the resume"
    )

class Replacement(BaseModel):
    replaced_words: Optional[str] = Field(
        default="", description="word or phrases to be replaced or subsituted"
    )
    substitution: Optional[str] = Field(
        default="", description = "substitution words or phrases, can be multiple"
    )
class Replacements(BaseModel):
    replacements: List[Replacement]




class ResumeUsers(LanceModel):
    resume_content: str = func.SourceField() 
    vector: Vector(func.ndims()) = func.VectorField(default=None)
    user_id: str
    resume_path: str
    pursuit_jobs: Optional[List[str]]
    name: Optional[str] 
    email: Optional[str]
    phone: Optional[str]
    city: Optional[str]
    state: Optional[str]
    linkedin: Optional[str] 
    website: Optional[str]
    degree: Optional[str]
    study: Optional[str] 
    graduation_year:Optional[str]
    gpa:Optional[str]
    # sections: ResumeFields
    summary_objective_section: Optional[str]
    skills_section: Optional[str]
    work_experience_section:  Optional[str]
    accomplishments_section: Optional[str]
    awards_honors_section: Optional[str] 
    projects_section: Optional[str]
    # work_experience: Jobs
    # education: Education
    # projects: Projects
    # certifications: Certification
    # skills: Skills
