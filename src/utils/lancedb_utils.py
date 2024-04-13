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
#FOR SCHEMA SETUP: https://lancedb.github.io/lancedb/guides/tables/#open-existing-tables
class UserInfo(LanceModel):
    name: str = func.SourceField()
    vector: Vector(func.ndims()) = func.VectorField()

def register_model(model_name):
    registry = EmbeddingFunctionRegistry.get_instance()
    model = registry.get(model_name).create()
    return model

def create_lancedb_table(db, table_name, data, schema="userInfo", mode="overwrite", ):
    # if schema=="userInfo":
    #     schema=UserInfo
    table = db.create_table(
        table_name,
        # schema = schema,
        # # data=[
        # #     {
        # #         "vector": embeddings.embed_query(query),
        # #         "text": "Hello World",
        # #         "id": "1",
        # #     }
        # # ],
        data=data,
        mode=mode,
    )
    return table

def add_to_lancedb_table(db, table_name, data, mode="append"):

    try:
        table=db.open_table(table_name)
        table.add(data, mode=mode)
    except Exception:
        create_lancedb_table(db, table_name, data)

def create_lancedb_index(db, table_name, distance_type):

    """ https://lancedb.github.io/lancedb/ann_indexes/#creating-an-ivf_pq-index"""

    table=db.open_table(table_name)
    table.create_index(metric=distance_type)

def lancedb_table_exists(db, table_name):

    try:
        table=db.open_table(table_name)
    except FileNotFoundError:
        return False
    return True

