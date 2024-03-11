import lancedb
from lancedb.embeddings import EmbeddingFunctionRegistry
from lancedb.pydantic import LanceModel, Vector


model="gpt-3.5-turbo-0613"
registry = EmbeddingFunctionRegistry.get_instance()
func = registry.get("openai").create(model=model)
db_path="/temp"

# this is the schema for table of UserInfo
class UserInfo(LanceModel):
    text: str = func.SourceField()
    vector: Vector(func.ndims()) = func.VectorField()

def create_table(table_name, schema="userInfo", mode="overwrite", ):
    if schema=="userInfo":
        schema=UserInfo
    db = lancedb.connect(db_path)
    table = db.create_table(
        table_name,
        schema = schema,
        # data=[
        #     {
        #         "vector": embeddings.embed_query(query),
        #         "text": "Hello World",
        #         "id": "1",
        #     }
        # ],
        mode=mode,
    )
    return table

def add_to_table(table_name="", field_name="", field_value="", table=None):
    if table==None:
        db = lancedb.connect(db_path)
        table = db.open_table(table_name)
        table.add({field_name: field_value})
    else:
        table.add({field_name: field_value})


