import os
import boto3
import streamlit as st
from requests_aws4auth import AWS4Auth
# import sagemaker
# from sagemaker.session import Session
# from sagemaker import get_execution_role
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

region_name=os.environ["REGION_NAME"]
@st.cache_resource()
def get_aws_session():

    return boto3.Session(         
                    aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"],
                    aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"],
                    region_name=region_name
                )
def get_session_token(duration=3600):
    # Create a new STS client
    sts_client = get_client('sts')
    
    # Request temporary credentials
    response = sts_client.get_session_token(DurationSeconds=duration)
    
    # Extract credentials
    credentials = response['Credentials']['SessionToken']
    return credentials

def get_client(type, config=None):
    
    if type=="s3":
        return get_aws_session().client('s3')
    elif type=="lambda":
        return get_aws_session().client('lambda')
    elif type=="dynamodb":
        return get_aws_session().client('dynamodb', region_name) 
    elif type=="sts":
        return get_aws_session().client('sts')
    
def get_resource(type):
    if type=="dynamodb":
        return get_aws_session().resource(type, region_name)
    if type=="s3":
        return get_aws_session().resource(type, )


def request_aws4auth(service="aoss", region='us-east-2'):
    credentials=get_aws_session().get_credentials()
    auth = AWS4Auth(credentials.access_key, credentials.secret_key, 
                region, service, session_token=credentials.token)
    print(auth)
    return auth


# def get_sagemaker_session():
#     role = get_execution_role()
#     sage_session = sagemaker.Session()
#     default_bucket = sage_session.default_bucket()
#     print(default_bucket)
#     return sage_session




    
