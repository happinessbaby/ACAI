from pydantic import BaseModel, Field, validator
from typing import Any, List, Union, Dict, Optional, Set
import lancedb
from lancedb.pydantic import LanceModel, Vector
from utils.lancedb_utils import func


 #NOTE: ALL NESTED PYDANTIC FIELDS ARE IN ALPHABETIC ORDER FOR THE SCHEMA VALIDATION
class Job(BaseModel):
    company: Optional[str] = Field(
        default="", description = "the company of the job position"
    )
    description: Optional[List[str]] = Field(
      default=[], description = """bullet point description of the responsibilities and roles of the job experience, do not leave out any details"""
      )
    end_date: Optional[str] = Field(
      default="", description = "the end date of the job position if available"
      )
    job_title: Optional[str] = Field(
        default="", description="the job position"
        )
    location: Optional[str] = Field(
        default="remote", description="the location where the candidate worked for this job position"
    )
    start_date: Optional[str] = Field(
      default="", description = "the start date of the job position if available"
      )
class Jobs(BaseModel):
    """Extracted data about people."""
    # Creates a model so that we can extract multiple entities.
    work_experience: List[Job] 


class Contact(BaseModel):
    city: Optional[str]= Field(
        default="", description="city of the candidate on the resume"
        )
    email: Optional[str]=Field(
        default="", description="email of the candidate on the resume"
    )
    linkedin: Optional[str] = Field(
        default="", description="linkedin address on the resume"
        )
    name: Optional[str] = Field(
        default="", description="name of the candidate on the resume"
    )
    phone: Optional[str]=Field(
        default="", description="phone number of the candidate on the resume"
        )
    state: Optional[str] = Field(
        default="", description="state of the candidate on the resume"
        )
    website: Optional[str]=Field(
        default="", description="other website address on the resume"
        )
        
class Education(BaseModel):
    coursework: Optional[List[str]] = Field(
        default=[], description = "the courseworks studied while attending the highest degree of education. "
    )
    degree: Optional[str] = Field(
        default="", description="the highest degree of education. THIS SHOULD NOT BE A CERTIFICATION. "
    )
    gpa:Optional[str] = Field(
        default="", description="the gpa of the highest degree of graduation. THIS SHOULD NOT BE OF A CERTIFICATION."
    )
    graduation_year:Optional[str] = Field(
        default="", description="the year of graduation from the highest degree of education. THIS SHOULD NOT BE OF A CERTIFICATION."
    )
    institution: Optional[str] = Field(
        default="", description="the institution at where the highest degree of education is attained. THIS SHOULD NOT BE OF A CERTIFICATION."
    )
    study: Optional[str] = Field(
        default="", description="the area of study including any majors and minors for the highest degree of education. THIS SHOULD NOT BE OF A CERTIFICATION."
    )

class Project(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], description = "details about the project, including the roles, accomplishments, metrics, etc. Include all details."
    )
    title: Optional[str] = Field(
        default="", description="the name of the project, can be a personal or work-related project, examples include coding project, art project, construction project, etc."
    )
class Projects(BaseModel):
    projects: List[Project]

class Award(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], description = "any descriptions of the award or honor"
    )
    title: Optional[str] = Field(
        default="", description = """the award or honor listed in the resume, this should not be job-specific ceritifications or skills, but awards received at workplace or school. 
        Examples include employee of the month, certificate of achievement, etc. 
        """    
    )
class Awards(BaseModel):
    awards: List[Award]

class Certification(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], descripton = "details and description about the certification"
    )
    issue_date: Optional[str] = Field(
        default="", description="the issuing date of the certification"
    )
    issue_organization: Optional[str] = Field(
        default="", description ="the industry-specific organization or professional body that issued the certification"
    )
    title: Optional[str] = Field(
        default="", description="""the title of the certifications, these may be in the education section, 
        should be industry-specific, should not be a degree"""
    )
class Certifications(BaseModel):
    certifications: List[Certification]

class License(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], description = "any description of the license"
    )
    issue_date: Optional[str] = Field(
        default="", description="the issuing date of the license"
    )
    issue_organization: Optional[str] = Field(
        default="", description ="the government organization or professional body that issued the occupational license"
    )
    title: Optional[str] = Field(
        default="", description="""the title of the occupational license"""
    )
class Licenses(BaseModel):
    licenses: List[License]

class SpecialFieldGroup1(BaseModel):
    licenses: List[License]
    awards: List[Award]
    certifications: List[Certification]

class Qualification(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], description = """description of the qualification, such as details of accomplishments, skills that may include responsibilities, metrics, etc.
        Include all details. """
    )
    title: Optional[str] = Field(
        default="", description = "The name of the skill or qualification"
    )
class Qualifications(BaseModel):
    qualifications: List[Qualification]

class Skill(BaseModel):
    example:Optional[str] = Field(
        default="", description="how the skill is demonstrated, an elaboration of the skill, or examples"
    )
    skill:Optional[str] = Field(
        default="", description="a skill listed "
    )
    type: Optional[str] = Field(
        default="", description="categorize the skill into 'hard skill' or 'soft skill' "
    )

    # def __hash__(self):
    #     return hash(self.skill)

    # def __eq__(self, other):
    #     if isinstance(other, Skill):
    #         return self.skill == other.skill
    #     return False
    
class Skills(BaseModel):
    skills : List[Skill]

# class ResumeFieldDetail(BaseModel):
#     contact: Contact
#     work_experience:List[Job]
#     education: Education
#     projects: List[Project]
#     certifications: List[Certification]
    

class BasicResumeFields(BaseModel):
    contact: Optional[Contact] = Field(
        default="", description = "The contact section of the resume, usually includes name, address, personal websites, etc."
    )
    education: Optional[Education] = Field(
        default="", description = "the education part of the resume where some degree is obtained"
    )
    work_experience_section:  Optional[str] = Field(
        default="", description=" the work experience section of the resume"
    )

class SpecialResumeFields(BaseModel):
    pursuit_jobs: Optional[str] = Field(
        default= "", description="""the possible job(s) that the candidate is pursuing. Usually this is found in the summary or objective section of the resume. 
        If there are many, separate each by a comma."""
    )
    summary_objective_section: Optional[str] = Field(
        default = "", description="the summary or objective section of the resume"
    )
    included_skills: Optional[List[str]] = Field(
        default=[], description=" all the skills and skillsets listed in the resume "
    )
    qualifications_section: Optional[str] = Field(
        default="", description="""the accomplishment/qualification section of the resume that is not work experience, 
        should have detailed description of each accomplishment,  qualification, skill. If there's no description, do not include it here. """
    )
    projects_section: Optional[str] = Field(
        default="", description = """the projects sections of the resume. This should not be a section about qualifications or skills. 
        Projects include personal projects or work-related projects. Please include the whole section. """    
    )
    hobbies_section: Optional[List[str]] = Field(
        default=[], description = "a list of hobbies in the resume"
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




class ResumeUsers(BaseModel):
    # resume_content: str = func.SourceField() 
    # vector: Vector(func.ndims()) = func.VectorField(default=None)
    user_id: str = Field(..., description="ID of user")
    resume_path: str = Field(..., description="path to the resume")
    resume_content: str
    contact: Contact
    education: Education
    # name: Optional[str] 
    # email: Optional[str]
    # phone: Optional[str]
    # city: Optional[str]
    # state: Optional[str]
    # linkedin: Optional[str] 
    # website: Optional[str]
    # institution: Optional[str]
    # degree: Optional[str]
    # study: Optional[str] 
    # graduation_year:Optional[str]
    # gpa:Optional[str]
    # coursework: Optional[List[str]]
    pursuit_jobs: Optional[str]
    summary_objective: Optional[str]
    included_skills: Optional[List[str]]
    # skills_section: Optional[str]
    # work_experience_section:  Optional[str]
    # qualifications_section: Optional[str]
    # awards_honors_section: Optional[str] 
    # projects_section: Optional[str]
    work_experience: Optional[List[Job]] = Field(..., description="List of jobs")
    projects: Optional[List[Project]] = Field(..., description="List of projects")
    certifications: Optional[List[Certification]] = Field(..., description="List of certifications")
    # included_skills: Optional[List[Skill]] = Field(..., description="List of skills included in the resume")
    suggested_skills: Optional[List[Skill]] = Field(..., description="List of skills not in resume but suggested by AI to include")
    qualifications: Optional[List[Qualification]]
    awards: Optional[List[Award]]
    licenses: Optional[List[License]]
    hobbies: Optional[List[str]]


