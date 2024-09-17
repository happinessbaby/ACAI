import lancedb
from lancedb.embeddings import EmbeddingFunctionRegistry
# from lancedb.embeddings import get_registry
# from lancedb.pydantic import LanceModel, Vector
import os
import numpy as np
import pyarrow as pa
from typing import List, Dict, Optional, get_args, get_origin, Set
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field
# from utils.aws_manager import get_session_token
# from utils.dynamodb_utils import init_dynamodb_table
# import lance

_ = load_dotenv(find_dotenv()) # read local .env file



model="gpt-4o-mini"
registry = EmbeddingFunctionRegistry.get_instance()
func = registry.get("openai").create(model=model)
STORAGE = os.environ["STORAGE"]
# if STORAGE=="LOCAL":
db_path=os.environ["LANCEDB_PATH"]
db = lancedb.connect(db_path,)
# elif STORAGE == "CLOUD":
#     bucket_name = os.environ["BUCKET_NAME"]
#     lancedb_path=os.environ["S3_LANCEDB_PATH"]
#     db_path = f"s3://{bucket_name}{lancedb_path}"
    # """By default, S3 does not support concurrent writes. Having two or more processes writing to the same table at the same time can lead to data corruption. This is because S3, unlike other object stores, does not have any atomic put or copy operation.
    # To enable concurrent writes, you can configure LanceDB to use a DynamoDB table as a commit store. This table will be used to coordinate writes between different processes."""
    # db_path =  f"""s3+ddb://{bucket_name}{lancedb_path}?ddbTableName=my-dynamodb-table"""
print("db path", db_path)
    # args_dict={}
    # args_dict["KeySchema"] = [
    # {"AttributeName": "base_uri", "KeyType": "HASH"},
    # {"AttributeName": "version", "KeyType": "RANGE"},
    # ]
    # args_dict["AttributeDefinitions"]=[
    #     {"AttributeName": "base_uri", "AttributeType": "S"},
    #     {"AttributeName": "version", "AttributeType": "N"},
    # ]
    # args_dict["ProvisionedThroughput"]={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1}
    # table = init_dynamodb_table("my-dynamodb-table", args_dict)
db = lancedb.connect(db_path)



lance_users_table = os.environ["LANCE_USERS_TABLE"]
lance_tracker_table = os.environ["LANCE_TRACKER_TABLE"]

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

# def add_lancedb_dataset():
#     ds = lance.dataset(
#         f"""s3+ddb://{bucket_name}{lancedb_path}?ddbTableName=my-dynamodb-table""",
#         storage_options={
#             "access_key_id": os.environ["AWS_SERVER_PUBLIC_KEY"],
#             "secret_access_key": os.environ["AWS_SERVER_SECRET_KEY"],
#         }
#     )
def register_model(model_name):
    registry = EmbeddingFunctionRegistry.get_instance()
    model = registry.get(model_name).create()
    return model

def create_lancedb_table(table_name, schema , mode="overwrite"):

    return db.create_table(
        table_name,
        schema=schema,
        mode=mode,
        exist_ok=True, 
    )


def add_to_lancedb_table(table_name, data, schema, mode="append"):
    
    try:
        table = db.open_table(table_name)
    except Exception as e:
        print(e)
        table = create_lancedb_table(table_name, schema)
    table.add(data, mode=mode)
    print("Sucessfully added data to table")

def create_lancedb_index(table_name, distance_type):

    """ https://lancedb.github.io/lancedb/ann_indexes/#creating-an-ivf_pq-index"""
    table=db.open_table(table_name)
    table.create_index(metric=distance_type)

def retrieve_lancedb_table(table_name):

    try:
        table= db.open_table(table_name)
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

def delete_user_from_table(userId, tablename):

    try:
        table = retrieve_lancedb_table(tablename)
        table.delete(f"user_id = '{userId}'")
        print(f'deleted user from {tablename}')
    except Exception as e:
        print(e)
        pass
    

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



def retrieve_dict_from_table(userId, tablename):

    users_table = retrieve_lancedb_table(tablename)
    if users_table:
        # table_dict= users_table.search().where(f"user_id = '{userId}'", prefilter=True).to_pandas().to_dict("list")
        table_dict= users_table.search().where(f"user_id = '{userId}'", prefilter=True).to_pandas().to_dict(orient="records")
        if not table_dict:
        # if not table_dict["user_id"]:
            return None
        for row in table_dict:
            for key in row:
                if isinstance(row[key], str):  # Handle strings
                    row[key] = row[key].strip()  # Optional: strip any extra whitespace
                elif isinstance(row[key], (np.ndarray, list)):  # Handle arrays
                    cleaned_data = clean_field(row, key)
                    row[key] = convert_arrays_to_lists(cleaned_data)
                elif isinstance(row[key], dict):  # Handle nested dictionaries
                    for k in row[key]:
                        if isinstance(row[key][k], (np.ndarray, list)):
                            cleaned_data = clean_field(row[key], k)
                            row[key][k] = convert_arrays_to_lists(cleaned_data)
                else:  # Handle None and anomalies
                    row[key] = ''
        print(f"Retrieved {tablename} dict from lancedb", )
        return table_dict if tablename==lance_tracker_table else table_dict[0]
    else:
        return None

#NOTE: below works with pydantic 1.x only
# def convert_pydantic_schema_to_arrow_v1(schema) -> pa.schema:
#     fields = []
#     for field_name, model_field in schema.__fields__.items():
#         field_type = model_field.outer_type_

#         if get_origin(field_type) is list:
#             # Handling lists
#             item_type = get_args(field_type)[0]
#             if hasattr(item_type, "__fields__"):
#                 # Handling lists of nested Pydantic models
#                 nested_fields = [
#                     pa.field(name, pa.list_(pa.string()) if get_origin(field.outer_type_) is list else pa.string(), nullable=True)
#                     for name, field in item_type.__fields__.items()
#                 ]
#                 nested_struct = pa.struct(nested_fields)
#                 fields.append(pa.field(field_name, pa.list_(nested_struct), nullable=True))
#             else:
#                 # Handling lists of basic types (e.g., List[str])
#                 fields.append(pa.field(field_name, pa.list_(pa.string()), nullable=True))
        
#         # elif get_origin(field_type) is dict and get_args(field_type) == (str, str):
#         #     # Handling dictionary fields
#         #     fields.append(pa.field(field_name, pa.map_(pa.string(), pa.string())))

#         elif hasattr(field_type, "__fields__"):
#             # Handling nested Pydantic models (non-list)
#             ""
#             nested_fields = [
#                 pa.field(name, pa.list_(pa.string()) if get_origin(field.outer_type_) is list else pa.string(), nullable=True)
#                 for name, field in field_type.__fields__.items()
#             ]
#             fields.append(pa.field(field_name, pa.struct(nested_fields), nullable=True))

#         else:
#             # Handling other field types (default to string for this example)
#             fields.append(pa.field(field_name, pa.string(), nullable=True))

#     return pa.schema(fields)
    
# Note: below works for pydantic V2
def convert_pydantic_schema_to_arrow(schema: BaseModel) -> pa.Schema:
    fields = []
    for field_name, model_field in schema.model_fields.items():  # Pydantic v2 uses model_fields
        field_type = model_field.annotation  # Use annotation for field type

        if get_origin(field_type) is list:
            # Handling lists
            item_type = get_args(field_type)[0]
            if hasattr(item_type, "model_fields"):
                # Handling lists of nested Pydantic models
                nested_fields = [
                    pa.field(
                        name,
                        pa.list_(pa.string()) if get_origin(field.annotation) is list else pa.string(),
                        nullable=True
                    )
                    for name, field in item_type.model_fields.items()  # Pydantic v2: model_fields
                ]
                nested_struct = pa.struct(nested_fields)
                fields.append(pa.field(field_name, pa.list_(nested_struct), nullable=True))
            else:
                # Handling lists of basic types (e.g., List[str])
                # fields.append(pa.field(field_name, pa.list_(pa.string()), nullable=True))
                # Handling lists of basic types (e.g., List[str])
                if pa.types.is_string(item_type):
                    fields.append(pa.field(field_name, pa.list_(pa.string()), nullable=True))
                # else:
                #     # Use a default type if item_type is not string
                #     fields.append(pa.field(field_name, pa.list_(pa.null()), nullable=True))
        
        # elif get_origin(field_type) is dict and get_args(field_type) == (str, str):
        #     # Handling dictionary fields (uncomment if needed)
        #     fields.append(pa.field(field_name, pa.map_(pa.string(), pa.string())))

        elif hasattr(field_type, "model_fields"):
            # Handling nested Pydantic models (non-list)
            nested_fields = [
                pa.field(
                    name,
                    pa.list_(pa.string()) if get_origin(field.annotation) is list else pa.string(),
                    nullable=True
                )
                for name, field in field_type.model_fields.items()  # Pydantic v2: model_fields
            ]
            fields.append(pa.field(field_name, pa.struct(nested_fields), nullable=True))

        else:
            # Handling other field types (default to string for this example)
            fields.append(pa.field(field_name, pa.string(), nullable=True))

    return pa.schema(fields)


def save_user_changes(userId, data, schema, tablename, convert_content=False):

    """Saves user and job information into lancedb tables 
    
    Args:
        userId: primary key, unique identifier for the entry
        data: a python dictionary
        schema: a pydantic class
        tablename: name of the table

    Keyword Args:
        convert_content: only for users table, converts profile dictionary into resume content string
        
    Returns: None
    
    """

    if convert_content:
        data = convert_profile_to_resume(data)
        # print(data)
    try:
    #   NOTE: currently does not support nested colunmn update, so need to delete the row and append it again
        delete_user_from_table(userId, tablename)
        # schema = convert_pydantic_schema_to_arrow(schema)
        #NOTE: the data added has to be a LIST!
        add_to_lancedb_table(tablename, [data], schema=schema)
        print(f"Successsfully saved {tablename}")
    except Exception as e:
        raise e
    
def convert_profile_to_resume(profile):

    """ Converts a profile dictionary to resume-like text and save as resume content """

    output = [] 
    for section, content in profile.items():
        if section!="resume_content" and section!="resume_path" and section!="user_id":
            if content:
                # Add the section title
                output.append(f"{section}:\n")        
                # Check if the content is a dictionary
                if isinstance(content, dict):
                    # Flatten the nested content, keeping only the values
                    values = content.values()
                    output.append(" ".join(map(str, values)) + "\n")
                else:
                    # If not a dictionary, add the content directly
                    output.append(str(content) + "\n")
    # Join the output list into a single string and return
    profile["resume_content"]= "\n".join(output)
    # print(profile["resume_content"])
    return profile


    

    

