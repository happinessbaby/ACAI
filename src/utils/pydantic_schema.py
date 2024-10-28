from pydantic import BaseModel, Field, model_validator
from typing import Any, List, Union, Dict, Optional, Set



 #NOTE: ALL NESTED PYDANTIC FIELDS ARE IN ALPHABETIC ORDER FOR THE SCHEMA VALIDATION
class Job(BaseModel):
    company: str = Field(
        default="", description = "the company of the job position where the person worked"
    )
    description: List[str] = Field(
      default=[], description = """description of the responsibilities and roles of the job experience, please list them verbatim"""
      )
    end_date: str = Field(
      default="", description = "the end date of this job experience if available"
      )
    location: str = Field(
        default="", description="the location where the candidate worked for this job position"
    )
    start_date: str = Field(
      default="", description = "the start date of this job experinece if available"
      )
    title: str = Field(
        default="", description="the job position, this needs to be a work experience"
        )
    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
        return values
    
class Jobs(BaseModel):
    """Extracted data about people."""
    # Creates a model so that we can extract multiple entities.
    work_experience: Optional[List[Job]] = Field(
        default=[], description=""" the content of the work experience section of the resume, most likely there's a whole section dedicated to work experience. Include everything in the section verbatim.
        Exclude anything that's not in the work experience section"""
    )
class HyperLink(BaseModel):
    display: str = Field(
        default="", description="display name of the url"
    )
    url: str = Field(
        default="", description="url"
    )
    @model_validator(mode="before")
    def replace_none_with_empty_list(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
        return values

class Contact(BaseModel):
    city: str= Field(
        default="", description="city of the candidate on the resume"
        )
    email: str=Field(
        default="", description="email of the candidate on the resume"
    )
    # linkedin: str = Field(
    #     default="", description="linkedin address on the resume"
    #     )
    # linkedin: HyperLink = Field(
    #     default={}, description="linkedin address on the resume"
    #     )
    links: List[HyperLink] = Field(
        default=[], description="links in the resume's contact section, can be linkedin, github, etc."
        )
    name: str = Field(
        default="", description="name of the candidate on the resume"
    )
    phone: str=Field(
        default="", description="phone number of the candidate on the resume"
        )
    state: str = Field(
        default="", description="state of the candidate on the resume"
        )
    # websites: str=Field(
    #     default="", description="other website addresses besides linkedin on the resume"
    #     )
    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
                # elif field_type==dict:
                #     values[field] = {}
        return values
        
class Education(BaseModel):
    coursework: List[str] = Field(
        default=[], description = "the courseworks studied while attending the highest degree of education. "
    )
    degree: str = Field(
        default="", description="the highest degree of education. THIS SHOULD NOT BE A CERTIFICATION. "
    )
    gpa: str = Field(
        default="", description="the gpa of the highest degree of graduation. THIS SHOULD NOT BE OF A CERTIFICATION."
    )
    graduation_year: str = Field(
        default="", description="the year of graduation from the highest degree of education. THIS SHOULD NOT BE OF A CERTIFICATION."
    )
    institution: str = Field(
        default="", description="the institution at where the highest degree of education is attained. THIS SHOULD NOT BE OF A CERTIFICATION."
    )
    study: str = Field(
        default="", description="the area of study including any majors and minors for the highest degree of education. THIS SHOULD NOT BE OF A CERTIFICATION."
    )
    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
        return values

class Project(BaseModel):
    company: str = Field(
        default="", description = "the company under which the project took place in"
    )
    description: List[str] = Field(
        default=[], description = "details about the project, including the roles, accomplishments, metrics, etc. Include all details."
    )
    end_date: str = Field(
      default="", description = "the end date of the project, if available"
      )
    # link:str = Field(
    #     default="", description = "an external link to the project"
    # )
    links: List[HyperLink] = Field(
        default=[], description = "link to the project"
    )
    location: str = Field(
        default="", description="the location where the took place in"
    )
    start_date: str = Field(
      default="", description = "the start date of the project, if available"
      )
    title: str = Field(
        default="", description="the name of the project, can be a personal or work-related project, examples include coding project, art project, construction project, etc."
    )
    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
                # elif field_type==dict:
                #     values[field] = {}
        return values

class Projects(BaseModel):
    projects: Optional[List[Project]] = Field(
        default=[], description="""content from the projects section of the resume.
    Projects include personal projects or work-related projects. This should not be a section about qualifications or skills. Include everything verbatim """    ""                                  
    )

class Award(BaseModel):
    description: List[str] = Field(
        default=[], description = "any description of the award or honor"
    )
    title: str = Field(
        default="", description = """the title of the award or honor
        """    
    )
    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
        return values
    
class Awards(BaseModel):
    awards: Optional[List[Award]] = Field(
        default=[], description = """the content of the award or honor, such as received at workplace or school. 
        Examples include employee of the month, certificate of achievement, etc. Content should not be about certifications or education
        """    
    )

class Certification(BaseModel):
    description: List[str] = Field(
        default=[], descripton = "description of the certification,  excluding issue date and issue organization, usually listed after title, issue date, and/or issue organization"
    )
    issue_date: str = Field(
        default="", description="the issuing date of the certification"
    )
    issue_organization: str = Field(
        default="", description ="the industry-specific organization or professional body that issued the certification"
    )
    title: str = Field(
        default="", description="""title of the certification """
    )
    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
        return values
    
class Certifications(BaseModel):
    certifications: Optional[List[Certification]] = Field(
        default=[], description = """the content of the award or honor, such as received at workplace or school. 
        Examples include employee of the month, certificate of achievement, etc. Content should not be about certifications or education
        """    
    )

class License(BaseModel):
    description: List[str] = Field(
        default=[], description = "description of the license, excluding issue date and issue organization, usually listed after title, issue date, and/or issue organization"
    )
    issue_date: str = Field(
        default="", description="the issuing date of the license"
    )
    issue_organization: str = Field(
        default="", description ="the government organization or professional body that issued the occupational license"
    )
    title: str = Field(
        default="", description="""the title of the occupational license"""
    )
    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
        return values
    
class Licenses(BaseModel):
    licenses: Optional[List[License]]=Field(
        default=[], description="""the content of occupational licenses, examples include those of teachers, nurses, doctors, lawyers, contractors. etc"""
    )

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
    description: List[str] = Field(
        default=[], description = """description of the qualification, such as details of accomplishments, skills that may include responsibilities, metrics, etc.
        Include all details. """
    )
    title: str = Field(
        default="", description = "The name of the skill or qualification"
    )
    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
        return values
    
class Qualifications(BaseModel):
    qualifications: List[Qualification] = Field(
        default=[], description="""the accomplishment/qualification section of the resume that is not work experience or projects, 
        should have detailed description of each accomplishment, qualification, and/or skill. Include everything verbatim. """
    )

class Hobbies(BaseModel):
    description: List[str] = Field(
        default=[], description = "a list of hobbies"
    )
    
    # @model_validator(mode="before")
    # def replace_none_with_empty_list(cls, values):
    #     if values.get("description") is None:
    #         values["description"] = []
    #     return values

class CustomField(BaseModel):
    description: Optional[List[str]]
    title: Optional[str]
    date: Optional[str]

# class CustomFields(BaseModel):
#     fields: List[CustomField]




class Skill(BaseModel):
    example:str = Field(
        default="", description="how the skill is demonstrated, an elaboration of the skill, or examples"
    )
    skill:str = Field(
        default="", description="a skill"
    )
    type:str = Field(
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
    # hobbies: Optional[List[str]] = Field(
    #     default=[], description = "a list of hobbies in the resume"
    # )


    # ^ Doc-string for the entity Person.
    # This doc-string is sent to the LLM as the description of the schema Keywords,
    # and it can help to improve extraction results.

    # Note that:
    # 1. Each field is an `optional` -- this allows the model to decline to extract it!
    # 2. Each field has a `description` -- this description is used by the LLM.
    # Having a good description can help improve extraction results.

class Keywords(BaseModel):
    """Information about a job posting."""

    job: str = Field(
        default="", description="job position listed in the job posintg"
    )
    about_job: str = Field(
        default="", description = "information about the job, usually listed at the top of the job posting"
    )
    company: str = Field(
        default="", description = "name of the company or institution that's hiring"
    )
    company_description: str = Field(
        default = "", description="information about the company that's hiring"
    )
    qualifications: List[str] = Field(
        default=[], description="Traits or qualifications sought in a candidate"
    )
    responsibilities: List[str] = Field(
        default=[], description="Duties and responsibilities for the job position"
    )
    salary: str = Field(
        default="", description = "salary or salary range offered for the job, can be annually or hourly"    
    )
    location: str = Field(
        default="", description = "job location, can be remote, hybrid, or somewhere specific"
    )

    @model_validator(mode="before")
    def replace_none_with_empty_values(cls, values):
        for field, value in values.items():
            if value is None:
                field_type = cls.model_fields[field].annotation
                if field_type == str:
                    values[field] = ""
                elif field_type == list:
                    values[field] = []
        return values


class Comparison(BaseModel):
    closeness: str = Field(
        default="", description = """closeness classified in the text, 
        should be one of the following metrics only: ["no similarity", "some similarity", "very similar"]"""
    )
    reason: str = Field(
        default="", description = "the reason provided for the classification in the text"
    )

class Language(BaseModel):
    rating: str = Field(
        default="", description="""rating identified in the text, should be one of the following metrics: ["poor", "good", "excellent"]"""
    )
    reason: str = Field(
        default="", description = "the reason provided for the rating in the text"
    )

class ResumeType(BaseModel):
    type: str = Field(
        default="", description="type of resume, should be functional, chronological, or mixed "
    )

class SkillsRelevancy(BaseModel):
    irrelevant_skills:List[str] = Field(
        default=[], description="irrelevant skills, found in content labeled in Step 1, these are skills that can be excluded from the resume"
    )
    relevant_skills: List[str] = Field(
        default=[], description="relevant skills, found in content labeled in Step 2, these are skills in the resume that are also in the job description "
    )
    # transferable_skills: List[str] = Field(
    #     default=[], description="additiaonl skills, found in content labeled in Step 3, these are skills that can be added to the resume "
    # )
 

class Replacement(BaseModel):
    replaced_words: str = Field(
        default="", description="word or phrases to be replaced or subsituted"
    )
    substitution: str = Field(
        default="", description = "the substitution"
    )
class Replacements(BaseModel):
    replacements: List[Replacement] = Field(
        default=[], description="the content will be a list made up of words that are to be replaced and their subtitutions"
    )

class MatchResumeJob(BaseModel):
    evaluation: str = Field(
        default="", description= "found in Step 1, this is an evaluation of how a resume field compares to a job description"
    )
    percentage: int = Field(
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
    certifications: Optional[List[Certification]]
    contact: Contact
    education: Education
    # hobbies: Optional[List[str]]
    hobbies: Optional[Hobbies]
    included_skills: Optional[List[str]]
    industry: Optional[str]
    licenses: Optional[List[License]]
    projects: Optional[List[Project]]
    pursuit_jobs: Optional[str]
    qualifications: Optional[List[Qualification]]
    resume_content: str
    resume_path: str 
    suggested_skills: Optional[List[str]]
    summary_objective: Optional[str]
    user_id: str # primary key
    work_experience: Optional[List[Job]] 
    # included_skills: Optional[List[Skill]] = Field(..., description="List of skills included in the resume")
    # custom_fields: Optional[List[CustomField]]


class JobTrackingUsers(BaseModel):

    user_id: str # primary keys
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
    skills_keywords: Optional[List[str]]
    experience_keywords: Optional[List[str]]
    salary: Optional[str] 
    location: Optional[str] 
    cover_letter_path: Optional[str]
    applied: Optional[bool]
    time: str # time, secondary key
    last_edit_time: str # time of the last edit
    match: Optional[int] # percent match between job posting and user profile
    color: Optional[str] # color for the job posting, used to distinguish when tailoring
    profile: Optional[ResumeUsers] # tailored version of the profile