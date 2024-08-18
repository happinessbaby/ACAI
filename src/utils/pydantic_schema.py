from pydantic import BaseModel, Field, validator
from typing import Any, List, Union, Dict, Optional, Set



 #NOTE: ALL NESTED PYDANTIC FIELDS ARE IN ALPHABETIC ORDER FOR THE SCHEMA VALIDATION
class Job(BaseModel):
    company: Optional[str] = Field(
        default="", description = "the company of the job position where the person worked"
    )
    description: Optional[List[str]] = Field(
      default=[], description = """description of the responsibilities and roles of the job experience, please list them verbatim"""
      )
    end_date: Optional[str] = Field(
      default="", description = "the end date of this job experience if available"
      )
    job_title: Optional[str] = Field(
        default="", description="the job position, this needs to be a work experience"
        )
    location: Optional[str] = Field(
        default="remote", description="the location where the candidate worked for this job position"
    )
    start_date: Optional[str] = Field(
      default="", description = "the start date of this job experinece if available"
      )
class Jobs(BaseModel):
    """Extracted data about people."""
    # Creates a model so that we can extract multiple entities.
    work_experience: List[Job] = Field(
        default=[], description=""" the content of the work experience section of the resume, most likely there's a whole section dedicated to work experience. Include everything in the section verbatim.
        Exclude anything that's not in the work experience section"""
    )


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
    websites: Optional[str]=Field(
        default="", description="other website addresses besides linkedin on the resume"
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
    projects: List[Project] = Field(
        default=[], description="""content from the projects section of the resume.
    Projects include personal projects or work-related projects. This should not be a section about qualifications or skills. Include everything verbatim """    ""                                  
    )

class Award(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], description = "any description of the award or honor"
    )
    title: Optional[str] = Field(
        default="", description = """the title of the award or honor
        """    
    )
class Awards(BaseModel):
    awards: List[Award]

class Certification(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], descripton = "description of the certification,  excluding issue date and issue organization, usually listed after title, issue date, and/or issue organization"
    )
    issue_date: Optional[str] = Field(
        default="", description="the issuing date of the certification"
    )
    issue_organization: Optional[str] = Field(
        default="", description ="the industry-specific organization or professional body that issued the certification"
    )
    title: Optional[str] = Field(
        default="", description="""title of the certification """
    )
class Certifications(BaseModel):
    certifications: List[Certification]

class License(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], description = "description of the license, excluding issue date and issue organization, usually listed after title, issue date, and/or issue organization"
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
    licenses: Optional[List[License]]  = Field(
        default=[], description="""the content of occupational licenses, examples include those of teachers, nurses, doctors, lawyers, contractors. etc"""
    )
    awards: Optional[List[Award]]  = Field(
        default=[], description = """the content of the award or honor, such as received at workplace or school. 
        Examples include employee of the month, certificate of achievement, etc. Content should not be about certifications or education
        """    
    )
    certifications: Optional[List[Certification]] = Field(
        default=[], description="""the content of the certification, may be in the education section, 
        should be industry-specific and should not be a degree, usually awarded for gaining new skillsets"""
    )

class Qualification(BaseModel):
    description: Optional[List[str]] = Field(
        default=[], description = """description of the qualification, such as details of accomplishments, skills that may include responsibilities, metrics, etc.
        Include all details. """
    )
    title: Optional[str] = Field(
        default="", description = "The name of the skill or qualification"
    )
class Qualifications(BaseModel):
    qualifications: List[Qualification] = Field(
        default=[], description="""the accomplishment/qualification section of the resume that is not work experience or projects, 
        should have detailed description of each accomplishment, qualification, and/or skill. Include everything verbatim. """
    )

class Skill(BaseModel):
    example:Optional[str] = Field(
        default="", description="how the skill is demonstrated, an elaboration of the skill, or examples"
    )
    skill:Optional[str] = Field(
        default="", description="a skill"
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
        default=None, description = "The contact section of the resume, usually includes name, address, personal websites, etc."
    )
    education: Optional[Education] = Field(
        default=None, description = "the education part of the resume where some degree is obtained"
    )
    work_experience_section:  Optional[str] = Field(
        default="", description=" the work experience section of the resume"
    )

class SpecialResumeFields(BaseModel):
    pursuit_jobs: Optional[str] = Field(
        default= "", description="""the possible job(s) that the candidate is pursuing. Usually this is found in the summary or objective section of the resume. 
        If there are many, separate each by a comma."""
    )
    summary_objective: Optional[str] = Field(
        default = "", description="the summary or objective section of the resume"
    )
    included_skills: Optional[List[str]] = Field(
        default=[], description=" all the skills and skillsets listed in the resume, most like there's a section dedicated to this"
    )
    # qualifications_section: Optional[str] = Field(
    #     default="", description="""the accomplishment/qualification section of the resume that is not work experience, 
    #     should have detailed description of each accomplishment, qualification, skill. This should not be about projects. Include everything verbatim. """
    # )
    # projects_section: Optional[str] = Field(
    #     default="", description = """the projects sections of the resume.
    #     Projects include personal projects or work-related projects. This should not be a section about qualifications or skills. Include everything verbatim """    
    # )
    hobbies: Optional[List[str]] = Field(
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
        default="", description = """closeness classified in the text, 
        should be one of the following metrics only: ["no similarity", "some similarity", "very similar"]"""
    )
    reason: Optional[str] = Field(
        default="", description = "the reason provided for the classification in the text"
    )

class Language(BaseModel):
    rating: Optional[str] = Field(
        default="", description="""rating identified in the text, should be one of the following metrics: ["bad", "good", "great"]"""
    )
    reason: Optional[str] = Field(
        default="", description = "the reason provided for the rating in the text"
    )

class ResumeType(BaseModel):
    type: Optional[str] = Field(
        default="", description="type of resume, should be functional, chronological, or mixed "
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


class GeneralEvaluation(BaseModel):
    user_id : str
    word_count: Optional[int]
    page_count: Optional[int]
    ideal_type: Optional[str]
    resume_type: Optional[str]
    impression: Optional[str]
    syntax: Language
    diction: Language
    tone: Language
    coherence: Language
    objective: Comparison
    work_experience: Comparison
    skillsets: Comparison
    finished: bool


class JobTrackingUsers(BaseModel):

    user_id: str
    posting_path: Optional[str]
    link: Optional[str]
    content: Optional[str]
    skills:Optional[List[Skill]]
    job: Optional[str] 
    about_job: Optional[str]
    company: Optional[str] 
    company_description: Optional[str]
    qualifications: Optional[List[str]]
    responsibilities: Optional[List[str]] 
    salary: Optional[str] 
    on_site: Optional[bool] 
    resume_path: Optional[str]
    cover_letter_path: Optional[str]
    status: Optional[str]


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


