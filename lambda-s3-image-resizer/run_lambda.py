import os
import json

# === FOR TESTING PERPOSE === #
import boto3
boto3.setup_default_session(profile_name='localstack')

import logging
logging.basicConfig(level=logging.INFO)

import lambda_function as my_lambda

def run_my_lambda():
    # To escape JSON for fixtures
    # https://www.freeformatter.com/json-escape.html
    with open('./tests/fixtures/lambda_events/s3-object-created-put-event.json') as json_file:
        data = json.load(json_file)
        response = my_lambda.handler(event=data, context={})
        print(response)


if __name__ == '__main__':    
    run_my_lambda()