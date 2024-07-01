import lancedb
from lancedb.embeddings import EmbeddingFunctionRegistry
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
import streamlit as st
import os


model="gpt-3.5-turbo-0613"
registry = EmbeddingFunctionRegistry.get_instance()
func = registry.get("openai").create(model=model)
db_path=os.environ["LANCEDB_PATH"]


db = lancedb.connect(db_path)

lance_users_table = os.environ["LANCE_USERS_TABLE"]

# this is the schema for table of UserInfo
#FOR SCHEMA SETUP: https://lancedb.github.io/lancedb/guides/tables/#open-existing-tablesa
# class BasicInfo(LanceModel):

class Schema(LanceModel):
    text: str = func.SourceField() 
    vector: Vector(func.ndims()) = func.VectorField()
    id: str 
    job_title: str
    job_url: str
    # job_industry: str
    # job_level: str 
    # education: str 
    type: str 

    @property
    def url(self):
        return self.job_url


def register_model(model_name):
    registry = EmbeddingFunctionRegistry.get_instance()
    model = registry.get(model_name).create()
    return model

def create_lancedb_table(table_name, schema , mode="overwrite"):

    table = db.create_table(
        table_name,
        schema=schema,
        mode=mode,
    )
    return table

def add_to_lancedb_table(table_name, data, schema, mode="append"):

    try:
        table=db.open_table(table_name)
        table.add(data, mode=mode)
    except FileNotFoundError:
        create_lancedb_table(table_name, schema)
        add_to_lancedb_table(table_name, data,schema)

def create_lancedb_index(table_name, distance_type):

    """ https://lancedb.github.io/lancedb/ann_indexes/#creating-an-ivf_pq-index"""

    table=db.open_table(table_name)
    table.create_index(metric=distance_type)

def retrieve_lancedb_table(table_name):

    try:
        table=db.open_table(table_name)
        print(f"table {table_name} exists")
    except FileNotFoundError:
        print(f"table {table_name} does not exists")
        return None
    return table

def query_lancedb_table(query, table_name, top_k=1):
    try:
        table = retrieve_lancedb_table(table_name)
        results = (
            table.search(query)
            .limit(top_k)
            .to_pydantic(Schema)
        )
    except Exception as e:
        raise e
    return results

def delete_user_from_table(table_name, userId):
    table = retrieve_lancedb_table(table_name)
    table.delete(f"user_id = '{userId}'")



def retrieve_user_profile_dict(userId):
    users_table = retrieve_lancedb_table(lance_users_table)
    profile_dict=users_table.search().where(f"user_id = '{userId}'", prefilter=True).to_pandas().to_dict("list")
    print(f"Retrieved user profile dict from lancedb: {profile_dict}")
    if not profile_dict["user_id"]:
        profile_dict = None
    return profile_dict


