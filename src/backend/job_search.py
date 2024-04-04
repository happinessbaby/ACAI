import os
import openai
from langchain.agents import load_tools
from langchain.utilities import TextRequestsWrapper
from langchain_core.documents import Document
from langchain.indexes import VectorstoreIndexCreator
from langchain_community.utilities import ApifyWrapper
from langchain_community.document_loaders import ApifyDatasetLoader

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) 
openai.api_key = os.environ["OPENAI_API_KEY"]

### This module should be ran in the background continuously fetching most recent jobs and saving them to job metadata store

class JobSearch():

    def __init__(self):
        self.apify = ApifyWrapper()

    def get_request(self, url):
        requests_tools = load_tools(["requests_all"])
        # Each tool wrapps a requests wrapper
        requests_tools[0].requests_wrapper
        TextRequestsWrapper(headers=None, aiosession=None)
        requests = TextRequestsWrapper()
        requests.get(url)
    
    def start_apify_search(self, starting_url:str, query:str) :

        loader = self.apify.call_actor(
        actor_id="apify/website-content-crawler",
        run_input={"startUrls": [{"url": starting_url}]},
        dataset_mapping_function=lambda item: Document(
            page_content=item["text"] or "", metadata={"source": item["url"]}
        ),
        )
        index = VectorstoreIndexCreator().from_loaders([loader])
        result = index.query_with_sources(query)
        print(result["answer"])
        print(result["sources"])

        
    def load_apify_dataset(self, dataset_id: str, ):
        loader = ApifyDatasetLoader(
            dataset_id=dataset_id,
            dataset_mapping_function=lambda item: Document(
                page_content=item["text"] or "", metadata={"source": item["url"]}
            ),
        )
        data = loader.load()
        print(data[1].page_content)
        return data
        # index = VectorstoreIndexCreator().from_loaders([loader])
        # result = index.query_with_sources(query)
        # return result



if __name__ == '__main__':
    search = JobSearch()
    # search.start_apify_search("https://www.indeed.com/", "find one software engineer jobs in birmingham, alabama")
    search.load_apify_dataset(dataset_id="CII7CKZMlhjjKbzQg")