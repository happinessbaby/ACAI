import boto3
import os
from typing import List, Union
from boto3.dynamodb.conditions import Key, Attr




from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file


def init_table(session, userId):

    dynamodb = session.resource('dynamodb', region_name='us-east-2') 
    # print(session.resource("dynamodb", 'us-east-2').get_available_subresources())
    print(session.client("dynamodb",'us-east-2').list_tables())
    try:
        return dynamodb.Table(userId)
    except Exception as e:
        return create_table(dynamodb, userId)

def create_table(dynamodb, name):
    table = dynamodb.create_table(
        TableName=name,
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
    return table


def retrieve_sessions(table, userId) -> Union[List[str], List[str]]: 

    """ Returns past chat sessions associated with user"""

    human, ai= [], []
    try:
        response = table.query(
            KeyConditionExpression=Key('userId').eq(userId)),
        print(response)
        # session_info = response[0]['Items'][0]['info']
        session_info = response[0]['Items'][0]
        for item in session_info:
            human.append(item["human"])
            ai.append(item["ai"])
            # ids.append(item["sessionId"])
    except Exception:
        pass
    return human, ai


def save_current_conversation(table, userId, human, ai):

    """ Saves chat session. """

    user = table.get_item(
        Key={'userId': userId},
    )
    if 'Item' in user:
        # append session info
        # sinfo = [{"sessionId": st.session_state.sessionId, "human":chat["human"], "ai":chat["ai"]}]
        # st.session_state.dnm_table.update_item(
        #     Key={"userId": st.session_state.userId},
        #     UpdateExpression="set info = list_append(info, :n)",
        #     ExpressionAttributeValues={
        #         ":n": info,
        #     },
        #     ReturnValues="UPDATED_NEW",
        # )
        table.update_item(
            Key={"userId":userId},
            UpdateExpression="set human = list_extend(human, :n)",
            ExpressionAttributeValues={
                ":n": human,
            },
            ReturnValues="UPDATED_NEW",
        )
        table.update_item(
            Key={"userId": userId},
            UpdateExpression="set ai = list_extend(ai, :n)",
            ExpressionAttributeValues={
                ":n": ai,
            },
            ReturnValues="UPDATED_NEW",
        )
        print("APPENDING OLD USER TO TABLE")
    else:
    # except Exception:
        # put new user into table
        # info = [{"sessionId": st.session_state.sessionId, "human":chat["human"], "ai":chat["ai"]}]
        # st.session_state.dnm_table.put_item(
        #     Item = {
        #         "userId": st.session_state.userId,
        #         "info": info,
        #     },
        # )
        table.put_item(
            Item = {
                "userId": userId,
                "human": human,
                "ai" : ai,
            },
        )
        print("ADDING NEW USER TO TABLE")

def save_user_info(table, userId, key, value):

    """ Saves user's career goals and self description to table """

    user = table.get_item(
        Key={'userId': userId},
    )
    if 'Item' in user:
        table.put_item(
            Item= {
                "about user": {
                key: value,
                }
            }
        )

def check_attribute_exists(table, key, attribute):

    try:
        _ = table.query(
         KeyConditionExpression = Key("userId").eq(key),
        FilterExpression=Attr(attribute).exists())
        return True
    except Exception as e:
        return False

