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
    location: Optional[str] = Field(
        default="", description="the location where the candidate worked for this job position"
    )
    start_date: Optional[str] = Field(
      default="", description = "the start date of this job experinece if available"
      )
    title: Optional[str] = Field(
        default="", description="the job position, this needs to be a work experience"
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
    company: Optional[str] = Field(
        default="", description = "the company under which the project took place in"
    )
    description: Optional[List[str]] = Field(
        default=[], description = "details about the project, including the roles, accomplishments, metrics, etc. Include all details."
    )
    end_date: Optional[str] = Field(
      default="", description = "the end date of the project, if available"
      )
    link: Optional[str] = Field(
        default="", description = "an external link to the project"
    )
    location: Optional[str] = Field(
        default="", description="the location where the took place in"
    )
    start_date: Optional[str] = Field(
      default="", description = "the start date of the project, if available"
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
    industry: Optional[str] = Field(
        default="", description="""the industry the candidate wants to work in, 
        it should be one of the following: hr, designer, information-technology,teacher, advocate, business-development,healthcare,fitness, agriculture, bpo, sales, consultant, public-relations, healthcare, arts,digital-media, banking, finance, accountant,apparel, engineering, chef, aviation, automobile"""
    )
    summary_objective: Optional[str] = Field(
        default = "", description="the summary or objective section of the resume, please include the entire section"
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
    location: Optional[str] = Field(
        default="", description = "job location, can be remote, hybrid, or somewhere specific"
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
        default="", description="""rating identified in the text, should be one of the following metrics: ["poor", "good", "excellent"]"""
    )
    reason: Optional[str] = Field(
        default="", description = "the reason provided for the rating in the text"
    )

class ResumeType(BaseModel):
    type: Optional[str] = Field(
        default="", description="type of resume, should be functional, chronological, or mixed "
    )

class SkillsRelevancy(BaseModel):
    irrelevant_skills:Optional[List[str]] = Field(
        default=[], description="irrelevant skills, found in content labeled in Step 1, these are skills that can be excluded from the resume"
    )
    relevant_skills: Optional[List[str]] = Field(
        default=[], description="relevant skills, found in content labeled in Step 2, these are skills in the resume that are also in the job description "
    )
    transferable_skills: Optional[List[str]] = Field(
        default=[], description="additiaonl skills, found in content labeled in Step 3, these are skills that can be added to the resume "
    )
 

class Replacement(BaseModel):
    replaced_words: Optional[str] = Field(
        default="", description="word or phrases to be replaced or subsituted"
    )
    substitution: Optional[str] = Field(
        default="", description = "the substitution"
    )
class Replacements(BaseModel):
    replacements: List[Replacement] = Field(
        default=[], description="the content will be a list made up of words that are to be replaced and their subtitutions"
    )

class MatchResumeJob(BaseModel):
    evaluation: Optional[str] = Field(
        default="", description= "found in Step 1, this is an evaluation of how a resume field compares to a job description"
    )
    percentage: Optional[int] = Field(
        default=0, description = "found in Step 2, this is a percentage comparison, output the number without percentage sign, for example, if it's 80%, output 80"
    )
    
class GeneralEvaluation(BaseModel):
    user_id : str
    word_count: Optional[int]
    # page_count: Optional[int]
    ideal_type: Optional[str]
    # resume_type: Optional[str]
    # impression: Optional[str]
    syntax: Optional[Language]
    # diction: Language
    tone: Optional[Language]
    readability:Optional[Language]
    # coherence: Language
    # objective: Comparison
    # work_experience: Comparison
    # skillsets: Comparison
    finished: bool




class ResumeUsers(BaseModel):
    # resume_content: str = func.SourceField() 
    # vector: Vector(func.ndims()) = func.VectorField(default=None)
    awards: Optional[List[Award]]
    certifications: Optional[List[Certification]] = Field(..., description="List of certifications")
    contact: Contact
    education: Education
    hobbies: Optional[List[str]]
    included_skills: Optional[List[str]]
    industry: Optional[str]
    licenses: Optional[List[License]]
    projects: Optional[List[Project]] = Field(..., description="List of projects")
    pursuit_jobs: Optional[str]
    qualifications: Optional[List[Qualification]]
    resume_content: str
    resume_path: str = Field(..., description="path to the resume")
    suggested_skills: Optional[List[str]] = Field(..., description="List of skills not in resume but suggested by AI to include")
    summary_objective: Optional[str]
    user_id: str = Field(..., description="ID of user")
    work_experience: Optional[List[Job]] = Field(..., description="List of jobs")
    # included_skills: Optional[List[Skill]] = Field(..., description="List of skills included in the resume")
    


class JobTrackingUsers(BaseModel):

    user_id: str
    # posting_path: Optional[str]
    link: Optional[str]
    content: Optional[str]
    skills:Optional[List[str]]
    job: Optional[str] 
    about_job: Optional[str]
    company: Optional[str] 
    company_description: Optional[str]
    qualifications: Optional[List[str]]
    responsibilities: Optional[List[str]] 
    keywords: Optional[List[str]]
    salary: Optional[str] 
    location: Optional[str] 
    cover_letter_path: Optional[str]
    applied: Optional[bool]
    time: str
    match: Optional[int]
    color: Optional[str]
    profile: Optional[ResumeUsers]