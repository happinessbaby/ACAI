import boto3
import os



from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
session = boto3.Session(         
                aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"],
                aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"],
            )
dynamodb = session.resource('dynamodb', region_name='us-east-2')

table = dynamodb.create_table(
    TableName='chatSession2',
    KeySchema=[
        {
            'AttributeName': 'userId',
            'KeyType': 'HASH'  #Partition_key
        },
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'userId',
            'AttributeType': 'S'
        },

    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    }
)

print("Table status:", table.table_status)