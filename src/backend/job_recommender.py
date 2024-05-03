from langchain_community.document_loaders import AirtableLoader
import os
import json
from pyairtable import Api
from utils.lancedb_utils import add_to_lancedb_table, create_lancedb_table, query_lancedb_table, lancedb_table_exists, Schema
from utils.async_utils import asyncio_run
import uuid
import lancedb
import schedule
import time

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) 

api_key = os.environ['AIRTABLE_API_KEY']
base_id = os.environ['AIRTABLE_BASE_KEY']
table_id = os.environ['AIRTABLE_TABLE_NAME']
db_path="./lancetest"
api = Api(api_key)
table = api.table(base_id, table_id)
db = lancedb.connect(db_path)


class Recommender():


    def __init__(self):

        pass

    
    def retrieve_and_save_jobs(self):

        """ Retrieves jobs from Air tables and saves them to LanceDB vector tables. """

        print("retrieving jobs from air table")
        #TODO: update in batches instead of all
        jobs = table.all(view='Myview', fields=['job_description', 'job_link', 'job_title'])
        data = []
        for job in jobs:
            job_description = str(job['fields'].get("job_description", ""))
            job_title=str(job['fields'].get("job_title", ""))
            job_link=str(job["fields"].get("job_link", ""))
            job_id=str(uuid.uuid4())
            # add job to lanceDB table: HAS TO BE A LIST!
            if job_description:
                data.append({"text":job_description, "id":job_id, "job_title":job_title, "job_url":job_link, "type":"job"})
        print(data)
        add_to_lancedb_table("Jobs3", data)

        # loader = AirtableLoader(api_key, table_id, base_id)
        # docs = loader.load()[0]
        # for doc in docs:
        #     # Replace single quotes with double quotes
        #     doc = doc.replace("'", "\"")
        #     json.loads(doc)

    def run_scheduler(self):
        
        while True:
            schedule.run_pending()
            time.sleep(1)  # Sleep for 1 second to avoid high CPU usage


    async def main(self):
        # Run the scheduler asynchronously
         # Schedule the job to run every hour
        schedule.every().minute.do(self.retrieve_and_save_jobs)
        await self.run_scheduler()


    def match_job(self, query, table_name="Jobs3", top_k=2):

        """ Matches jobs according to user information and returns the matched job urls. """

        urls = []
        try:
            table = lancedb_table_exists(table_name)
            results = (
                table.search(query)
                .limit(top_k)
                .to_pydantic(Schema)
            )
            for res in results:
                urls.append(res.url)
        except Exception as e:
            raise e
        return urls

        # res = query_lancedb_table(query, "Jobs3")
        # res[0].url
        # print(res)

    def rank_job(self, jobs):
        #TODO, Job ranking requires more thought processs than retrieval. Will need some kind of RLHF or agent 
        return None




if __name__ == '__main__':

    recommender = Recommender()
    asyncio_run(recommender.main())
