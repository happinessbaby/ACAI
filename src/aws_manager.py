import os
import boto3
import streamlit as st
from requests_aws4auth import AWS4Auth
import sagemaker
from sagemaker.session import Session
from sagemaker import get_execution_role
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file


@st.cache_resource()
def get_aws_session():
    session = boto3.Session(         
                    aws_access_key_id=os.environ["AWS_SERVER_PUBLIC_KEY"],
                    aws_secret_access_key=os.environ["AWS_SERVER_SECRET_KEY"],
                    region_name='us-east-2'
                )
    return session


def request_aws4auth(session: boto3.Session, service="aoss", region='us-east-2'):
    credentials=session.get_credentials()
    auth = AWS4Auth(credentials.access_key, credentials.secret_key, 
                region, service, session_token=credentials.token)
    print(auth)
    return auth


def get_sagemaker_session():
    role = get_execution_role()
    sage_session = sagemaker.Session()
    default_bucket = sage_session.default_bucket()
    print(default_bucket)
    return sage_session




    
