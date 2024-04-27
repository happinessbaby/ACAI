from langchain_community.document_loaders import AirtableLoader
import os
import json
from pyairtable import Api
from utils.lancedb_utils import add_to_lancedb_table, create_lancedb_table
import uuid
import lancedb
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


    def _init_(self):
        pass

    
    def retrieve_job(self):
        jobs = table.all(view='Myview', fields=['job_description', 'job_link', 'job_title'])
        data = []
        for job in jobs:
            job_description = str(job['fields'].get("job_description", ""))
            job_title=str(job['fields'].get("job_title", ""))
            job_id=str(uuid.uuid4())
            # add job to lanceDB table: HAS TO BE A LIST!
            if job_description:
                data.append({"text":job_description, "id":job_id, "job_title":job_title,  "type":"job"})
        print(data)
        add_to_lancedb_table(db, "Jobs3", data)

        # loader = AirtableLoader(api_key, table_id, base_id)
        # docs = loader.load()[0]
        # for doc in docs:
        #     # Replace single quotes with double quotes
        #     doc = doc.replace("'", "\"")
        #     json.loads(doc)



recommend = Recommender()
recommend.retrieve_job()