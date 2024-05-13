# import requests
import os
import fitz
from pathlib import Path
import pypandoc
import uuid
import markdown
import csv
import bs4
import urllib.request
from urllib.request import Request, urlopen
import uuid
from pptx import Presentation
from langchain.document_loaders import UnstructuredURLLoader
from typing import Any, List, Union, Dict
from docxtpl import DocxTemplate
from langchain.document_transformers import Html2TextTransformer
from langchain.document_loaders import AsyncHtmlLoader, S3FileLoader
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import collections.abc, functools
from functools import wraps
from time import time
import errno
import os
import signal
import functools
import codecs
import json
import decimal
import requests
from docx import Document
from odf import text, teletype
from odf.opendocument import load
from io import BytesIO
    
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"]
aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"]

def convert_to_txt(file, output_path, storage="LOCAL", bucket_name=None, s3=None) -> bool:

    """ Converts file to TXT file and move it to destination location. """
    try:
        file_ext = Path(file).suffix
        if storage=="LOCAL":
            if (file_ext)=='.txt' and file!=output_path:
                os.rename(file, output_path)
            elif (file_ext=='.pdf'): 
                convert_pdf_to_txt(file, output_path)
            elif (file_ext=='.docx'):
                convert_doc_to_txt(file, output_path)
            elif (file_ext=='.odt' ):
                convert_odt_to_txt(file, output_path)
            elif (file_ext==".log"):
                convert_log_to_txt(file, output_path)
            elif (file_ext==".pptx"):
                convert_pptx_to_txt(file, output_path)
        elif storage=="CLOUD":
            loader = S3FileLoader(bucket_name, file, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
            text = loader.load()[0].page_content
            s3.put_object(Body=text, Bucket=bucket_name, Key=output_path)
            print("Successfully converted file in S3 to TXT")
        return True 
    except Exception as e:
        print(e)
        return False


def convert_log_to_txt(file, output_path):
    with open(file, "r") as f:
        content = f.read()
        with open(output_path, "w") as f:
            f.write(content)
            f.close()
      

def convert_pptx_to_txt(pptx_file, output_path):
    prs = Presentation(pptx_file)
    text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text+=shape.text+'\n'
    with open(output_path, 'w') as f:
        f.write(text)
        f.close()
 
#TODO: needs to find the best pdf to txt converter that takes care of special characters best (such as the dash between dates)
def convert_pdf_to_txt(pdf_file, output_path):
    pdf = fitz.open(pdf_file)
    text = ""
    for page in pdf:
        text+=page.get_text() + '\n'
    with open(output_path, 'w') as f:
        f.write(text)
        f.close()

#TODO: needs to find the best docx to txt converter that takes care of special characters best
def convert_doc_to_txt(doc_file, output_path):
    doc = Document(doc_file)
    # text= pypandoc.convert_file(doc_file, to="plain", format=file_ext, outputfile=output_path)
    # print(text)
    with open(output_path, "w") as f:
        for paragraph in doc.paragraphs:
            f.write(paragraph.text + '\n')
        
def convert_odt_to_txt(odt_file, txt_file):
    doc = load(odt_file)
    text_content = []
    for paragraph in doc.getElementsByType(text.P):
        text_content.append(teletype.extractText(paragraph))
    
    with open(txt_file, 'w', encoding='utf-8') as f:
        for line in text_content:
            f.write(line + '\n')

def convert_txt_to_doc(txt_file, output_path, storage="LOCAL", s3=None, bucket_name=None):
    doc = Document()
    with open(txt_file, 'r', encoding='utf-8') as f:
        for line in f:
            doc.add_paragraph(line.strip())
    if storage=="LOCAL":
        doc.save(output_path)
    elif storage=="CLOUD":
         # Save DOCX to memory
        docx_bytes = BytesIO()
        doc.save(docx_bytes)
        # Upload DOCX to S3
        s3.put_object(Body=docx_bytes.getvalue(), Bucket=bucket_name, Key=output_path)

def read_txt(file: str, storage="LOCAL", bucket_name=None, s3=None) -> str:

    """ Reads TXT file into string. """

    try:
        if storage=="LOCAL":
            with open(file, 'r', errors='ignore') as f:
                text = f.read()
                return text
        elif storage=="CLOUD":
            data = s3.get_object(Bucket=bucket_name, Key=file)
            contents = data['Body'].read()
            text = contents.decode("utf-8")
            return text
    except Exception as e:
        return ""
    
def delete_file(file, storage="LOCAL", bucket_name=None, s3=None) -> bool:
    
    """ Deletes file. """
    
    try:
        if storage=="LOCAL":
            os.remove(file)
        elif storage=="CLOUD":
            s3.delete_object(Bucket=bucket_name, Key=file)
        return True
    except Exception as e:
        return False
    
def mk_dirs(paths: List[str], storage="LOCAL", bucket_name=None, s3=None):

    """ Creates directories given a list of paths"""

    if storage=="LOCAL":
        for path in paths:
            try: 
                os.mkdir(path)
                print("Successfully made directories")
            except FileExistsError:
                pass
    elif storage=="CLOUD":
        for path in paths:
            try:
                s3.put_object(Bucket=bucket_name,Body='', Key=path)
            except Exception as e:
                raise e
            

def write_file(file_content:Any, end_path: str, mode="wb", storage="LOCAL", bucket_name=None, s3=None,):

    """ Writes content to file. """

    if storage=="LOCAL":
        try:
            with open(end_path, mode) as f:
                f.write(file_content)
                return True
        except Exception as e:
            print(e)
            return False
    elif storage=="CLOUD":
        try:
            s3.put_object(Body=file_content, Bucket=bucket_name, Key=end_path,)
        except Exception:
            return False


def read_file(file_path:str, mode="rb", storage="LOCAL", bucket_name=None, s3=None):
    
    if storage=="LOCAL":
        try:
            with open(file_path, mode) as f:
                data = f.read()
        except Exception as e:
            raise e
    elif storage=="CLOUD":
        try:
            object = s3.get_object(Bucket=bucket_name, Key=file_path)
            data = object['Body'].read()
        except Exception as e:
            raise e
    return data

def move_file(source_file:str, dest_dir:str, storage="LOCAL", bucket_name=None, s3=None,):

    if storage=="LOCAL":
        os.rename(source_file, dest_dir)
    elif storage=="CLOUD":
        s3.copy_object(
            Bucket=bucket_name,
            Key=dest_dir,
            CopySource={'Bucket': bucket_name, 'Key': source_file}
        )



    
def markdown_table_to_dict(markdown_table):
    # Convert Markdown to HTML
    html = markdown.markdown(markdown_table)
    print(html)

    # Parse HTML table using csv module
    rows = csv.reader(html.split('\n'), delimiter='|')

    # Extract header and data rows
    header = next(rows)
    data = [row for row in rows if len(row) > 1]

    # Convert rows to dictionary
    result = []
    for row in data:
        item = {}
        for i, value in enumerate(row):
            key = header[i].strip()
            item[key] = value.strip()
        result.append(item)

    return result

class AppURLopener(urllib.request.FancyURLopener):
    version = "Mozilla/5.0"

def retrieve_web_content(link, save_path="test.txt"):

    req = Request(
        url=link, 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    try: 
        webpage=str(urllib.request.urlopen(link).read())
    except Exception: 
        # webpage = urlopen(req).read()
        opener = AppURLopener()
        webpage = opener.open(link)
    soup = bs4.BeautifulSoup(webpage, features="lxml")

    content = soup.get_text()
    print(content)
    # if content:
    #     with open(save_path, 'w') as file:
    #         file.write(content)
    #         file.close()
    #         print('Content retrieved and written to file.')
    #         return True
    # else:
    #     print('Failed to retrieve content from the URL.')
    #     return False
    
# this one is better than the above function 
def html_to_text(urls:List[str], save_path, storage="LOCAL", bucket_name=None, s3=None):

    """Writes a list of urls' content to txt file. """
    
    try:
        loader = AsyncHtmlLoader(urls)
        docs = loader.load()
        html2text = Html2TextTransformer()
        docs_transformed = html2text.transform_documents(docs)
        content = docs_transformed[0].page_content  
        print(content)
        if storage=="LOCAL":            
            with open(save_path, 'w') as file:
                file.write(content)
                file.close()
                print('Content retrieved and written to file.')
        elif storage=="S3":
            s3.put_object(Body=content, Bucket=bucket_name, Key=save_path)
        return True
    except Exception as e:
        print(e)
        return False
    
def save_website_as_html(url, filename):
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(response.text)
            print(f"Website saved as {filename} successfully.")
        else:
            print(f"Failed to retrieve the website. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")




# def write_to_docx_template(doc: Any, field_name: List[str], field_content: Dict[str, str], res_path) -> None:
#     context = {key: None for key in field_name}
#     for field in field_name:
#         if field_content[field] != -1:
#             context[field] = field_content[field]
#     doc.render(context)
#     doc.save(res_path)
#     print(f"Succesfully written {field_name} to {res_path}.")

# source code: https://github.com/trancethehuman/entities-extraction-web-scraper/blob/main/scrape.py
async def ascrape_playwright(url, tags: list[str] = ["h1", "h2", "h3"]) -> str:
    """
    An asynchronous Python function that uses Playwright to scrape
    content from a given URL, extracting specified HTML tags and removing unwanted tags and unnecessary
    lines.
    """
    print("Started scraping...")
    results = ""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url)
            page_source = await page.content()

            # results = remove_unessesary_lines(extract_tags(remove_unwanted_tags(
            #     page_source), tags))
            text = remove_unwanted_tags(
                page_source).get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            results = "\n".join(chunk for chunk in chunks if chunk)
            print(results)
            print("Content scraped")
        except Exception as e:
            results = f"Error: {e}"
        await browser.close()
    # return page_source
    return results 

def remove_unwanted_tags(html_content, unwanted_tags=["script", "style"]) -> BeautifulSoup:
    """
    This removes unwanted HTML tags from the given HTML content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()

    return soup


def extract_tags(html_content, tags: list[str]):
    """
    This takes in HTML content and a list of tags, and returns a string
    containing the text content of all elements with those tags, along with their href attribute if the
    tag is an "a" tag.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    text_parts = []

    for tag in tags:
        elements = soup.find_all(tag)
        for element in elements:
            # If the tag is a link (a tag), append its href as well
            if tag == "a":
                href = element.get('href')
                if href:
                    text_parts.append(f"{element.get_text()} ({href})")
                else:
                    text_parts.append(element.get_text())
            else:
                text_parts.append(element.get_text())

    return ' '.join(text_parts)


def remove_unessesary_lines(content):
    # Split content into lines
    lines = content.split("\n")

    # Strip whitespace for each line
    stripped_lines = [line.strip() for line in lines]

    # Filter out empty lines
    non_empty_lines = [line for line in stripped_lines if line]

    # Remove duplicated lines (while preserving order)
    seen = set()
    deduped_lines = [line for line in non_empty_lines if not (
        line in seen or seen.add(line))]

    # Join the cleaned lines without any separators (remove newlines)
    cleaned_content = " ".join(deduped_lines)

    return cleaned_content  

def process_json(json_str: str) -> str:

    """ Processes str into valid json string """

    return json_str.strip("'<>() ").replace(" ", "").__str__().replace("'", '"')

class memoized(object):

    '''Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    '''
    def __init__(self, func):
       self.func = func
       self.cache = {}
    def __call__(self, *args):
       if not isinstance(args, collections.abc.Hashable):
          # uncacheable. a list, for instance.
          # better to not cache than blow up.
          return self.func(*args)
       if args in self.cache:
          return self.cache[args]
       else:
          value = self.func(*args)
          self.cache[args] = value
          return value
    def __repr__(self):
       '''Return the function's docstring.'''
       return self.func.__doc__
    def __get__(self, obj, objtype):
       '''Support instance methods.'''
       return functools.partial(self.__call__, obj)
    


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print('func:%r args:[%r, %r] took: %2.4f sec' % \
          (f.__name__, args, kw, te-ts))
        return result
    return wrap

class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wrapper

    return decorator

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

if __name__=="__main__":
    # retrieve_web_content("https://python.langchain.com/docs/use_cases/summarization/",)
    # html_to_text(
    #     "https://algs4.cs.princeton.edu/41graph/",
    #     save_path =f"./test.txt")
        # save_path = f"./web_data/{str(uuid.uuid4())}.txt")
    # convert_to_txt("/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/resume2023v4.docx","/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/resume2023v4.txt")
    convert_doc_to_txt("./test_cover_letter.docx", "docx", "./test.txt")




    

    




