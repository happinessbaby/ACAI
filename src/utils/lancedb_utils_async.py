import lancedb
from lancedb.embeddings import EmbeddingFunctionRegistry
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
import os
import numpy as np
import pyarrow as pa
from typing import List, Dict, Optional, get_args, get_origin, Set
import json
from utils.async_utils import asyncio_run
from dotenv import load_dotenv, find_dotenv
from utils.aws_manager import get_session_token
_ = load_dotenv(find_dotenv()) # read local .env file





model="gpt-3.5-turbo-0613"
registry = EmbeddingFunctionRegistry.get_instance()
func = registry.get("openai").create(model=model)
STORAGE = os.environ["STORAGE"]
if STORAGE=="LOCAL":
    db_path=os.environ["LANCEDB_PATH"]
    storage_options={}
elif STORAGE == "CLOUD":
    bucket_name = os.environ["BUCKET_NAME"]
    lancedb_path=os.environ["S3_LANCEDB_PATH"]
    db_path = f"s3://{bucket_name}{lancedb_path}"
    print("db path", db_path)
      #NOTE: only async api is supported for storage options 
     #see: https://lancedb.github.io/lancedb/guides/storage/#object-stores
    storage_options={
            "aws_access_key_id": os.environ["AWS_SERVER_PUBLIC_KEY"],
            "aws_secret_access_key": os.environ["AWS_SERVER_SECRET_KEY"],
            #   "aws_session_token": get_session_token(),
            "region": os.environ["REGION_NAME"],
        }
    
async def connect():
    return await lancedb.connect_async(
    db_path, storage_options=storage_options
)


lance_users_table = os.environ["LANCE_USERS_TABLE"]

# this is the schema for table of UserInfo
#FOR SCHEMA SETUP: https://lancedb.github.io/lancedb/guides/tables/#open-existing-tablesa
# class BasicInfo(LanceModel):

# class Schema(LanceModel):
#     text: str = func.SourceField() 
#     vector: Vector(func.ndims()) = func.VectorField()
#     id: str 
#     job_title: str
#     job_url: str
#     # job_industry: str
#     # job_level: str 
#     # education: str 
#     type: str 

#     @property
#     def url(self):
#         return self.job_url


def register_model(model_name):
    registry = EmbeddingFunctionRegistry.get_instance()
    model = registry.get(model_name).create()
    return model

async def create_lancedb_table(table_name, schema , mode="overwrite"):

    with await lancedb.connect_async(db_path, storage_options=storage_options) as db:
        return await db.create_table(
        table_name,
        schema=schema,
        mode=mode,
        exist_ok=True, 
        # storage_options=storage_options
    )
    

async def add_to_lancedb_table(table_name, data, schema, mode="append"):
    
    with await lancedb.connect_async(db_path, storage_options=storage_options) as db:
        try:
            table=await db.open_table(table_name)
            await table.add(data, mode=mode)
        except Exception as e:
            print(e)
            table = await create_lancedb_table(table_name, schema)
            await table.add(data, mode=mode)

async def create_lancedb_index(table_name, distance_type):

    """ https://lancedb.github.io/lancedb/ann_indexes/#creating-an-ivf_pq-index"""
    with await lancedb.connect_async(db_path, storage_options=storage_options) as db:
        table=await db.open_table(table_name)
        await table.create_index(metric=distance_type)

async def retrieve_lancedb_table(table_name):

    with await lancedb.connect_async(db_path, storage_options=storage_options) as db:
        print(db_path)
        try:
            table=await db.open_table(table_name)
            print(f"table {table_name} exists")
        except Exception as e:
            print(f"table {table_name} does not exists", e)
            return None
        return table

# def query_lancedb_table(query, table_name, top_k=1):
#     try:
#         table = retrieve_lancedb_table(table_name)
#         results = (
#             table.search(query)
#             .limit(top_k)
#             .to_pydantic(Schema)
#         )
#     except Exception as e:
#         raise e
#     return results

async def delete_user_from_table(userId):

    table = await retrieve_lancedb_table(lance_users_table)
    await table.delete(f"user_id = '{userId}'")
    print('deleted user profile dict')
   

def flatten(data):
    if isinstance(data, (list, np.ndarray)):
        for item in data:
            yield from flatten(item)
    else:
        yield data

def clean_field(data, field_name):
    field_data = data[field_name]
    clean_field = list(flatten(field_data))
    return clean_field

def convert_arrays_to_lists(data):
    if isinstance(data, dict):
        return {k: convert_arrays_to_lists(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_arrays_to_lists(i) for i in data]
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data


async def retrieve_user_profile_dict(userId):

    users_table = await retrieve_lancedb_table(lance_users_table)
    if users_table:
        profile_dict=await users_table.vector_search().where(f"user_id = '{userId}'", prefilter=True).to_pandas().to_dict("list")
        if not profile_dict["user_id"]:
            return None
        for key in profile_dict:
            if isinstance(profile_dict[key], list):
                try:
                    value=profile_dict[key][0]
                    if isinstance(value, str):  # Handle strings
                        profile_dict[key]=value
                    elif isinstance(value, (np.ndarray, list)):  # Handle arrays
                        # print(value)
                        cleaned_data= clean_field(profile_dict, key)
                        profile_dict[key] = convert_arrays_to_lists(cleaned_data)
                        # print("list pydantic arrays", profile_dict[key])
                    elif isinstance(value, dict):
                        for k in value:
                            if isinstance(value[k], (np.ndarray, list)):
                                cleaned_data = clean_field(value, k)
                                value[k] = convert_arrays_to_lists(cleaned_data)
                        profile_dict[key]=value
                    else:                   # Handle None and anomalies
                        profile_dict[key] = ''
                except IndexError:
                    pass
        print(f"Retrieved user profile dict from lancedb")
        return profile_dict
    else:
        return None


    # for field_name, model_field in schema.__fields__.items():
    #     if field_name=="vector":
    #         fields.append(pa.field(field_name, pa.list_(pa.float32())))
    #     if hasattr(model_field.type_, "__fields__"):
    #         # Assuming list of nested Pydantic models
    #         nested_model = model_field.type_
    #         print("list field name:", field_name)
    #         nested_fields = [pa.field(name, pa.string()) for name in nested_model.__fields__.keys()]
    #         # nested_fields = []
    #         # for name, field in nested_model.__fields__.items():
    #         #     if field.outer_type_ == list:
    #         #         # Handle nested lists if needed
    #         #         nested_fields.append(pa.field(name, pa.list_(pa.string())))
    #         #     else:
    #         #           # Determine the Arrow data type based on Pydantic field type
    #         #         if issubclass(field.type_, str) or issubclass(field.type_, Optional):
    #         #             arrow_type = pa.string()
    #         #         elif issubclass(field.type_, int):
    #         #             arrow_type = pa.int64()
    #         #         else:
    #         #             arrow_type = pa.string()  # Default to string if unsure
    #         #         nested_fields.append(pa.field(name, arrow_type))
    #         # Ensure fields are in the expected order for Arrow struct
    #         nested_fields = sorted(nested_fields, key=lambda f: f.name)
    #         fields.append(pa.field(field_name, pa.list_(pa.struct(nested_fields))))
    #     else:
    #         fields.append(pa.field(field_name, pa.string()))
def convert_pydantic_schema_to_arrow(schema) -> pa.schema:
    fields = []
    for field_name, model_field in schema.__fields__.items():
        field_type = model_field.outer_type_

        if get_origin(field_type) is list:
            # Handling lists
            item_type = get_args(field_type)[0]
            if hasattr(item_type, "__fields__"):
                # Handling lists of nested Pydantic models
                nested_fields = [
                    pa.field(name, pa.list_(pa.string()) if get_origin(field.outer_type_) is list else pa.string(), nullable=True)
                    for name, field in item_type.__fields__.items()
                ]
                nested_struct = pa.struct(nested_fields)
                fields.append(pa.field(field_name, pa.list_(nested_struct), nullable=True))
            else:
                # Handling lists of basic types (e.g., List[str])
                fields.append(pa.field(field_name, pa.list_(pa.string()), nullable=True))
        
        # elif get_origin(field_type) is dict and get_args(field_type) == (str, str):
        #     # Handling dictionary fields
        #     fields.append(pa.field(field_name, pa.map_(pa.string(), pa.string())))

        elif hasattr(field_type, "__fields__"):
            # Handling nested Pydantic models (non-list)
            ""
            nested_fields = [
                pa.field(name, pa.list_(pa.string()) if get_origin(field.outer_type_) is list else pa.string(), nullable=True)
                for name, field in field_type.__fields__.items()
            ]
            fields.append(pa.field(field_name, pa.struct(nested_fields), nullable=True))

        else:
            # Handling other field types (default to string for this example)
            fields.append(pa.field(field_name, pa.string(), nullable=True))

    return pa.schema(fields)


def save_user_changes(profile, schema):

    # converts profile into resume content 
    profile["resume_content"] = json.dumps(profile)
    try:
        schema = convert_pydantic_schema_to_arrow(schema)
        asyncio_run(add_to_lancedb_table(lance_users_table, [profile], schema=schema, mode="overwrite" ))
        print("Successfully saved profile")
    except Exception as e:
        raise e
    