import lancedb
from lancedb.embeddings import EmbeddingFunctionRegistry
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
import streamlit as st
import os
import numpy as np
import pyarrow as pa

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

def clean_field(data, field_name):

    clean_field = []
    for item in data[field_name]:
        for dict_item in item:  # Remove the array wrapper
            clean_field.append(dict_item)
    # print("clean field", clean_field)
    return clean_field

def retrieve_user_profile_dict(userId):
    users_table = retrieve_lancedb_table(lance_users_table)
    if users_table:
        profile_dict=users_table.search().where(f"user_id = '{userId}'", prefilter=True).to_pandas().to_dict("list")
        if not profile_dict["user_id"]:
            return None
        for key in profile_dict:
            if isinstance(profile_dict[key], list):
                value=profile_dict[key][0]
                if isinstance(value, str):  # Handle strings
                    profile_dict[key]=value
                    # print(profile_dict[key])
                elif isinstance(value, (np.ndarray, list)):  # Handle arrays
                    profile_dict[key]= clean_field(profile_dict, key)
                    # print(profile_dict[key])
                else:                   # Handle None and anomalies
                    profile_dict[key] = ''
        print(f"Retrieved user profile dict from lancedb")
        return profile_dict
    else:
        return None


def convert_pydantic_schema_to_arrow(schema) -> pa.schema:
    fields = []
    for field_name, model_field in schema.__fields__.items():
        if field_name=="vector":
            fields.append(pa.field(field_name, pa.list_(pa.float32())))
        if hasattr(model_field.type_, "__fields__"):
            # Assuming list of nested Pydantic models
            nested_model = model_field.type_
            print("list field name:", field_name)
            nested_fields = [pa.field(name, pa.string()) for name in nested_model.__fields__.keys()]
            # nested_fields = []
            # for name, field in nested_model.__fields__.items():
            #     if field.outer_type_ == list:
            #         # Handle nested lists if needed
            #         nested_fields.append(pa.field(name, pa.list_(pa.string())))
            #     else:
            #           # Determine the Arrow data type based on Pydantic field type
            #         if issubclass(field.type_, str) or issubclass(field.type_, Optional):
            #             arrow_type = pa.string()
            #         elif issubclass(field.type_, int):
            #             arrow_type = pa.int64()
            #         else:
            #             arrow_type = pa.string()  # Default to string if unsure
            #         nested_fields.append(pa.field(name, arrow_type))
            # Ensure fields are in the expected order for Arrow struct
            nested_fields = sorted(nested_fields, key=lambda f: f.name)
            fields.append(pa.field(field_name, pa.list_(pa.struct(nested_fields))))
        else:
            fields.append(pa.field(field_name, pa.string()))

    return pa.schema(fields)

def save_user_changes(userId, schema):

    try:
        delete_user_from_table(lance_users_table, userId)
        schema = convert_pydantic_schema_to_arrow(schema)
        add_to_lancedb_table(lance_users_table, [st.session_state["profile"]], schema=schema, mode="overwrite" )
        st.toast("Successfully updated profile")
        del st.session_state["profile"]
    except Exception as e:
        raise e
    