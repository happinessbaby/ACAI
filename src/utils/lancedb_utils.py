import lancedb
from lancedb.embeddings import EmbeddingFunctionRegistry
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
import os


model="gpt-3.5-turbo-0613"
registry = EmbeddingFunctionRegistry.get_instance()
func = registry.get("openai").create(model=model)
db_path=os.environ["LANCEDB_PATH"]

# this is the schema for table of UserInfo
#FOR SCHEMA SETUP: https://lancedb.github.io/lancedb/guides/tables/#open-existing-tablesa
# class BasicInfo(LanceModel):

class UserInfo(LanceModel):
    name: str = func.SourceField()
    vector: Vector(func.ndims()) = func.VectorField()

def register_model(model_name):
    registry = EmbeddingFunctionRegistry.get_instance()
    model = registry.get(model_name).create()
    return model

def create_lancedb_table(db, table_name,  ):

    table = db.create_table(
        table_name,
        schema = UserInfo,
        # # ],
        # data=data,
        # mode=mode,
    )
    return table

def add_to_lancedb_table(db, table_name, data, mode="append"):

    try:
        table=db.open_table(table_name)
        table.add(data, mode=mode)
    except FileNotFoundError:
        create_lancedb_table(db, table_name)
        # add_to_lancedb_table(db, table_name, data)

def create_lancedb_index(db, table_name, distance_type):

    """ https://lancedb.github.io/lancedb/ann_indexes/#creating-an-ivf_pq-index"""

    table=db.open_table(table_name)
    table.create_index(metric=distance_type)

def lancedb_table_exists(db, table_name):

    try:
        table=db.open_table(table_name)
    except FileNotFoundError:
        return None
    return table

def query_lancedb_table(query, db, table_name, top_k=1):
    try:
        table = lancedb_table_exists(db, table_name)
        results = (
            table.search(query)
            .limit(top_k)
            .to_pydantic(UserInfo)[0]
        )
    except Exception as e:
        raise e
    return results
