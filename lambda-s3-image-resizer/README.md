# Using Python and AWS Lambda to Resize Images

![lambda_image_resizer](./images/lambda-image-resizer.webp)

# Verify using Python 3.10

In our example, it requires to use Python 3.10. By using [PYENV for managing Python versions](https://github.com/pyenv/pyenv), we can easy to switch multiple Python versions. Follow this [How to Install Pyenv on Ubuntu 22.04](https://tuts.heomi.net/how-to-install-pyenv-on-ubuntu-22-04/).


Check installed python versions
```sh
$ pyenv versions
  system
  3.7.17
* 3.9.19 (set by /home/tvt/.pyenv/version)
  3.12.4
```

Check current Python version
```sh
$ python --version
Python 3.9.19
```

Check available python versions
```sh
$ pyenv install -l
```

Install the latest verions of Python 3.10 series
```sh
$ pyenv install 3.10.14
Downloading Python-3.10.14.tar.xz...
-> https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tar.xz
Installing Python-3.10.14...
Installed Python-3.10.14 to /home/tvt/.pyenv/versions/3.10.14
```

Switch to use the Python 3.10.14
```sh
$ pyenv global 3.10.14
$ pyenv versions
  system
  3.7.17
  3.9.19
* 3.10.14 (set by /home/tvt/.pyenv/version)
  3.12.4
```

Verify correct version 3.10.14
```sh
$ python --version
Python 3.10.14
$ python3 --version
Python 3.10.14
```

If you are using VS Code, you have to [select the environment](https://code.visualstudio.com/docs/python/environments) using the `Python: Select interpreter` command to select the correct interpreter path:

![vs_python_interpreter](./images/aws-lambda-resizer-vscode-python-interpreter.png)

Then you need to re-open the terminal and verify Python version again

![vs_verify_python](./images/aws-lambda-resizer-vscode-verify-python.png)


# Setting up the AWS environment

## Create an S3 bucket

Let's create the bucket that will be used to upload user images

The following command creates a bucket named `awslambda-imageresizer-test-002` in the `us-west-2` region. Regions outside of `us-east-1` require the appropriate `LocationConstraint` to be specified in order to create the bucket in the desired region.

```bash
$ aws s3api --profile tvt_admin create-bucket \
    --bucket awslambda-imageresizer-test-002 \
    --region us-west-2 \
    --create-bucket-configuration "LocationConstraint=us-west-2"

{
    "Location": "http://awslambda-imageresizer-test-002.s3.amazonaws.com/"
}
```

To verify the bucket created
```bash
$ aws s3api head-bucket --bucket "awslambda-imageresizer-test-002" --profile tvt_admin
{
    "BucketRegion": "us-west-2",
    "AccessPointAlias": false
}
```

Or can use the list command with query by bucket name
```bash
$ aws s3api list-buckets --query 'Buckets[?Name==`awslambda-imageresizer-test-002`]' --output text --profile tvt_admin

2024-07-24T04:05:49+00:00       awslambda-imageresizer-test-002
```

![s3_bucket](./images/aws-lambda-resizer-s3-bucket.png)

## Create an IAM role

Creating a role and providing permission to the Lambda service assume this role
```sh
$ aws iam create-role --profile tvt_admin \
    --role-name awslambda-imageresizer-role \
    --assume-role-policy-document \
'{
  "Version": "2012-10-17",
  "Statement": [
  {
    "Effect": "Allow", 
    "Principal": {
      "Service": "lambda.amazonaws.com"
     }, 
     "Action": "sts:AssumeRole"
   }
  ]
}'


{
    "Role": {
        "Path": "/",
        "RoleName": "awslambda-imageresizer-role",
        "RoleId": "AROAW5R5WNQHPIUROBQUX",
        "Arn": "arn:aws:iam::475797023758:role/awslambda-imageresizer-role",
        "CreateDate": "2024-07-24T04:22:24+00:00",
        "AssumeRolePolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
    }
}
```

Let's add the [AWSLambdaBasicExecutionRole](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSLambdaBasicExecutionRole.html) policy. It provides write permissions to CloudWatch Logs.
```sh
$ aws iam attach-role-policy --profile tvt_admin \
    --role-name awslambda-imageresizer-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

To check created role information
```bash
$ aws iam get-role --profile tvt_admin \
    --role-name awslambda-imageresizer-role
{
    "Role": {
        "Path": "/",
        "RoleName": "awslambda-imageresizer-role",
        "RoleId": "AROAW5R5WNQHPIUROBQUX",
        "Arn": "arn:aws:iam::475797023758:role/awslambda-imageresizer-role",
        "CreateDate": "2024-07-24T04:22:24+00:00",
        "AssumeRolePolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        },
        "MaxSessionDuration": 3600,
        "RoleLastUsed": {}
    }
}
```


To check all policies of specific role
```bash
$ aws iam list-role-policies --profile tvt_admin \
    --role-name awslambda-imageresizer-role
```
To get all attached policies
```bash
$ aws iam list-attached-role-policies --profile tvt_admin \
    --role-name awslambda-imageresizer-role
{
    "AttachedPolicies": [
        {
            "PolicyName": "AWSLambdaBasicExecutionRole",
            "PolicyArn": "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        }
    ]
}
```

![iam_role_attached_policies](./images/aws-lambda-resizer-iam-role.png)


# Setting up the Environment

Create `requirements.txt` contains the libraries
* `boto3`: connect to S3, open image from S3 bucket, upload the resized image to S3 bucket
* `Pillow`:  resize image
```sh
$ cat requirements.txt 

boto3
Pillow
```

Create a new virtual environment (https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
```sh
$ python3 -m venv .venv

[notice] A new release of pip is available: 23.0.1 -> 24.1.2
[notice] To update, run: pip install --upgrade pip
```

Activate a virtual environment
```sh
$ source .venv/bin/activate
```

To confirm the virtual environment is activated, check the location of your Python interpreter:
```sh
$ which python
...
.venv/bin/python
```

Deactivate a virtual environment
```sh
$ deactivate
```

Prepare pip: You can make sure that pip is up-to-date by running:
```sh
$ python3 -m pip install --upgrade pip
$ python3 -m pip --version
pip 24.1.2 from /home/tvt/techspace/aws/aws-best-practices/lambda-s3-image-resizer/.venv/lib/python3.10/site-packages/pip (python 3.10)
```

You can Install packages using pip
```sh
$ python3 -m pip install boto3
$ python3 -m pip install Pillow
```

Or if you already declare all dependencies in a `requirements.txt` file, you can install all of the packages in this file using `-r` flag:
```sh
$ python3 -m pip install -r requirements.txt
```

Freezing dependencies: Pip can export a list of all installed packages and their versions using the freeze command:
```sh
$ python3 -m pip freeze
```

# Prepare for Debuging and Testing

If you are using VS Code, make sure the environment you want to use is selected in the Python extension for VS Code by running the [Select Interpreter](https://code.visualstudio.com/docs/python/environments) command or via the status bar. Otherwise you can explicitly [set the Python interpreter to be used when debugging](https://code.visualstudio.com/docs/python/debugging#_python) via the python setting for your debug config

Menubar -> View -> Command Palette -> Python: Select Interpreter

![vs_debug_activated_python_env](./images/aws-lambda-resizer-vscode-activated-python-env.png)

Create a file [lambda_function.py](lambda_function.py) with the minimum codes for testing first
```python
import boto3
from PIL import Image
import io

def handler(event, context):
    # Get the S3 bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    print("Got new image: " + key + " from the bucket: " + bucket)
    return {
        'statusCode': 200,
        'body': 'Image resized successfully!'
    }
```

Create a file [run_lambda.py](./run_lambda.py) for debuging and testing my lambda code
```python
import os
import json

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
```

This program will read the [S3 ObjectCreated::Put] event from the fixture file: [s3-object-created-put-event.json](./tests/fixtures/lambda_events/s3-object-created-put-event.json) and pass the data to lamdbda handler function.


In VSCode, you need to install the Python Debugger extension. Then configure the launch.json file
```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

Finally, open the file `run_lambda.py`, then cho RUN AND DEBUG with configuration: `Python Debugger: Current File`

![vs_run_debug_lambda](./images/aws-lambda-resizer-vscode-run-and-debug.png)

# Complete Lambda Process

We are parsing the uploaded image details from the event.

Using boto3, we are open the image and resize it using the Pillow library. 

Finally using boto3 to upload the resized image with a 'resized-' prefix attached.

```python
import boto3
from PIL import Image
import io

def handler(event, context):
    # Get the S3 bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    print("Got new image: " + key + " from the bucket: " + bucket)

    # Set the desired width and height for resizing
    width = 800
    height = 600

    # Load the image from S3
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    image = Image.open(io.BytesIO(response['Body'].read()))

    # Resize the image
    resized_image = image.resize((width, height))
    print("Image resized.")

    # Save the resized image to the same S3 bucket with a different name
    resized_key = 'resized-' + key
    with io.BytesIO() as output:
        resized_image.save(output, format='JPEG')
        output.seek(0)
        s3.put_object(Body=output, Bucket=bucket, Key=resized_key)

    print("Image " + resized_key + " uploaded.")
    return {
        'statusCode': 200,
        'body': 'Image resized successfully!'
    }
```

# Testing Lambda code with LocalStack

First pull LocalStack image
```sh
$ docker pull localstack/localstack
```

Ensure Ensure Python 3.10 is installed
```sh
$ pyenv versions
$ pyenv global 3.10.14
$ python --version
```

Next, we need to install `localstack` and `awscli-local` packages to use them with Docker container
```sh
$ pip install --upgrade localstack
$ pip install awscli-local
```

The final step is to run our Docker container, attaching the Docker socket. This is required for Lambda functions and other services that necessitate opening additional containers.
```sh
$ docker run \
  --rm -it \
  -p 4566:4566 \
  -p 4510-4559:4510-4559 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  localstack/localstack
```

LocalStack should be started at `http://localhost:4566` or `https://localhost.localstack.cloud:4566`. To check it’s running properly, check the health by visiting `{endpoint}/_localstack/health`.
```sh
$ curl --silent https://localhost.localstack.cloud:4566/_localstack/health | jq

{
  "services": {
    "acm": "available",
    "apigateway": "available",
    "cloudformation": "available",
    "cloudwatch": "available",
    "config": "available",
    "dynamodb": "available",
    "dynamodbstreams": "available",
    "ec2": "available",
    "es": "available",
    "events": "available",
    "firehose": "available",
    "iam": "available",
    "kinesis": "available",
    "kms": "available",
    "lambda": "available",
    "logs": "available",
    "opensearch": "available",
    "redshift": "available",
    "resource-groups": "available",
    "resourcegroupstaggingapi": "available",
    "route53": "available",
    "route53resolver": "available",
    "s3": "running",
    "s3control": "available",
    "scheduler": "available",
    "secretsmanager": "available",
    "ses": "available",
    "sns": "available",
    "sqs": "available",
    "ssm": "available",
    "stepfunctions": "available",
    "sts": "available",
    "support": "available",
    "swf": "available",
    "transcribe": "available"
  },
  "edition": "community",
  "version": "3.5.1.dev"
}
```

List all S3 buckets to verify that everything is working correctly
```sh
$ awslocal s3api list-buckets
{
    "Buckets": [],
    "Owner": {
        "DisplayName": "webfile",
        "ID": "75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a"
    }
}
```

Create S3 bucket for holding image and the resized image
```sh
$ awslocal s3 mb s3://awslambda-imageresizer-test-002 --region us-west-2
make_bucket: awslambda-imageresizer-test-002
```

List S3 bucket again for verifing S3 bucket created
```sh
$ awslocal s3api list-buckets

{
    "Buckets": [
        {
            "Name": "awslambda-imageresizer-test-002",
            "CreationDate": "2024-07-24T09:03:46+00:00"
        }
    ],
    "Owner": {
        "DisplayName": "webfile",
        "ID": "75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a"
    }
}
```

We can now push the sample image file to the bucket
```sh
$ cd ~/techspace/aws/aws-best-practices/lambda-s3-image-resizer
$ awslocal \
s3api put-object --bucket awslambda-imageresizer-test-002 \
--key happy-smiley-face.jpg --body=happy-smiley-face.jpg

{
    "ETag": "\"7c78efd6e95d7e1928ee34fa25fb5eb1\"",
    "ServerSideEncryption": "AES256"
}
```

Check S3 bucket to verify the image file has been uploaded:
```sh
$ awslocal s3api list-objects --bucket awslambda-imageresizer-test-002 --query 'Contents[].{Key: Key, Size: Size}'

[
    {
        "Key": "happy-smiley-face.jpg",
        "Size": 181915
    }
]
```

If we don't want to use the `awslocal` CLI, you can specify the endpoint of LocalStack:
```sh
$ aws s3api list-objects --endpoint-url=http://localhost:4566 --bucket awslambda-imageresizer-test-002 --query 'Contents[].{Key: Key, Size: Size}'
[
    {
        "Key": "happy-smiley-face.jpg",
        "Size": 181915
    }
]
```

We also can create a profile to access LocalStack
```sh
$ cat ~/.aws/config

[profile localstack]
output = json
region = us-east-1
endpoint_url = https://localhost.localstack.cloud:4566


$ cat ~/.aws/credentials

[localstack]
aws_access_key_id=test
aws_secret_access_key=test
```

Then we can using this profile for the CLI:
```sh
$ aws s3api list-objects --profile localstack --bucket awslambda-imageresizer-test-002 --query 'Contents[].{Key: Key, Size: Size}'
[
    {
        "Key": "happy-smiley-face.jpg",
        "Size": 181915
    }
]
```

Now update the file `run_lambda.py` to allow access LocalStack by using profile
```python
import boto3
boto3.setup_default_session(profile_name='localstack')
```

Run test lambda by command
```sh
$ python3 run_lambda.py
Got new image: happy-smiley-face.jpg from the bucket: awslambda-imageresizer-test-002
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
INFO:botocore.configprovider:Found endpoint for s3 via: config_global.
Image resized.
Image resized-happy-smiley-face.jpg uploaded.
{'statusCode': 200, 'body': 'Image resized successfully!'}
```

Re-check the S3 bucket to see the new resized file has been uploaded:
```sh
$  aws s3api list-objects --profile localstack --bucket awslambda-imageresizer-test-002 --query 'Contents[].{Key: Key, Size: Size}'
[
    {
        "Key": "happy-smiley-face.jpg",
        "Size": 181915
    },
    {
        "Key": "resized-happy-smiley-face.jpg",
        "Size": 73688
    }
]
```

We can download the resized file
```sh
$ wget http://localhost:4566/awslambda-imageresizer-test-002/resized-happy-smiley-face.jpg
```


# Creating a .zip deployment package with dependencies

* Ref: [Working with .zip file archives for Python Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)


In our case we are using a virtual environment for development. Then following these bellow commands to create the deployment package in a .ZIP file.

First check the folder in which pip install our libraries
```sh
(.venv) tvt@TVTLAP:~/techspace/aws/aws-best-practices/lambda-s3-image-resizer$ pip show boto3

Name: boto3
Version: 1.34.147
Summary: The AWS SDK for Python
Home-page: https://github.com/boto/boto3
Author: Amazon Web Services
Author-email: 
License: Apache License 2.0
Location: /home/tvt/techspace/aws/aws-best-practices/lambda-s3-image-resizer/.venv/lib/python3.10/site-packages
Requires: botocore, jmespath, s3transfer
Required-by: 
```

You can see this folder is located in `.venv/lib/python3.10/site-packages`. We will deactivate the environment, then navigate to this folder:
```sh
$ deactivate
$ cd .venv/lib/python3.10/site-packages
```

Create a .zip file in your project directory with the installed dependencies at the root
```
~/.venv/lib/python3.10/site-packages$ zip -r ../../../../my_deployment_package.zip .
```

Navigate to the root of your project directory where the `lambda_function.py` file containing your handler code is located and add that file to the root of your .zip package
```sh
~/.venv/lib/python3.10/site-packages$ cd ../../../../
$ zip my_deployment_package.zip lambda_function.py
adding: lambda_function.py (deflated 52%)
```

We can check the zip file content structure:
```sh
$ unzip -l my_deployment_package.zip

my_deployment_package.zip
|- bin
|  |-jp.py
|- boto3
|  |-compat.py
|  |-data
|  |-docs
...
|- lambda_function.py
```

You can use the `less` utility
```sh
$ less my_deployment_package.zip >> my_deployment_package.txt
```


# Deploy lambda to LocalStack using .zip file

Create the Lambda function by running (more details on [Lambda runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html)):
```sh
$ aws lambda create-function --profile localstack \
    --region us-west-2 \
    --function-name aws-lambda-image-resizer \
    --zip-file fileb://my_deployment_package.zip --handler lambda_function.handler --runtime python3.10 \
    --role arn:aws:iam::000000000000:role/awslambda-imageresizer-role

{
    "FunctionName": "aws-lambda-image-resizer",
    "FunctionArn": "arn:aws:lambda:us-west-2:000000000000:function:aws-lambda-image-resizer",
    "Runtime": "python3.10",
    "Role": "arn:aws:iam::000000000000:role/awslambda-imageresizer-role",
    "Handler": "lambda_function.handler",
    "CodeSize": 25267190,
    "Description": "",
    "Timeout": 3,
    "MemorySize": 128,
    "LastModified": "2024-07-24T10:49:18.440759+0000",
    "CodeSha256": "P5YuoytlaXw6WeDo7weJX/Z4vCSDwcHFD6bayMoUtwY=",
    "Version": "$LATEST",
    "TracingConfig": {
        "Mode": "PassThrough"
    },
    "RevisionId": "c8a55e85-57f2-4d53-8e9e-faafcf67b6e7",
    "State": "Pending",
    "StateReason": "The function is being created.",
    "StateReasonCode": "Creating",
    "PackageType": "Zip",
    "Architectures": [
        "x86_64"
    ],
    "EphemeralStorage": {
        "Size": 512
    },
    "SnapStart": {
        "ApplyOn": "None",
        "OptimizationStatus": "Off"
    },
    "RuntimeVersionConfig": {
        "RuntimeVersionArn": "arn:aws:lambda:us-west-2::runtime:8eeff65f6809a3ce81507fe733fe09b835899b99481ba22fd75b5a7338290ec1"
    },
    "LoggingConfig": {
        "LogFormat": "Text",
        "LogGroup": "/aws/lambda/aws-lambda-image-resizer"
    }
}
```

We can get information about the function
```sh
$ aws lambda --profile localstack --region us-west-2 get-function \
    --function-name aws-lambda-image-resizer

$ aws lambda --profile localstack --region us-west-2 get-function \
    --function-name aws-lambda-image-resizer
{
    "Configuration": {
        "FunctionName": "aws-lambda-image-resizer",
        "FunctionArn": "arn:aws:lambda:us-west-2:000000000000:function:aws-lambda-image-resizer",
        "Runtime": "python3.10",
        "Role": "arn:aws:iam::000000000000:role/awslambda-imageresizer-role",
        "Handler": "lambda_function.handler",
        "CodeSize": 25267190,
        "Description": "",
        "Timeout": 3,
        "MemorySize": 128,
        "LastModified": "2024-07-24T10:49:18.440759+0000",
        "CodeSha256": "P5YuoytlaXw6WeDo7weJX/Z4vCSDwcHFD6bayMoUtwY=",
        "Version": "$LATEST",
        "TracingConfig": {
            "Mode": "PassThrough"
        },
        "RevisionId": "32a13c74-a942-424d-abfe-17ac2feec0c3",
        "State": "Active",
        "LastUpdateStatus": "Successful",
        "PackageType": "Zip",
        "Architectures": [
            "x86_64"
        ],
        "EphemeralStorage": {
            "Size": 512
        },
        "SnapStart": {
            "ApplyOn": "None",
            "OptimizationStatus": "Off"
        },
        "RuntimeVersionConfig": {
            "RuntimeVersionArn": "arn:aws:lambda:us-west-2::runtime:8eeff65f6809a3ce81507fe733fe09b835899b99481ba22fd75b5a7338290ec1"
        },
        "LoggingConfig": {
            "LogFormat": "Text",
            "LogGroup": "/aws/lambda/aws-lambda-image-resizer"
        }
    },
    "Code": {
        "RepositoryType": "S3",
        "Location": "http://s3.localhost.localstack.cloud:4566/awslambda-us-west-2-tasks/snapshots/000000000000/aws-lambda-image-resizer-abfb9c21-4ad5-417c-9e56-54e1a90ca3c8?AWSAccessKeyId=949334387222&Signature=0xB0lY56TWAABIrHwo7%2FThtBTAE%3D&Expires=1721822010"
    }
}
```


You can see that the default function timeout is 3 sec. This is really low. We know that our code will not be able to download, resize and upload an image in 3 sec. 

So lets update the configuration.
```sh
$ aws lambda --profile localstack --region us-west-2 update-function-configuration \
    --function-name aws-lambda-image-resizer \
    --timeout 120
```


Now let's add the image upload event trigger in S3 to trigger our Lambda function.
```sh
$ aws lambda --profile localstack --region us-west-2 add-permission \
    --function-name aws-lambda-image-resizer \
    --action "lambda:InvokeFunction" \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::awslambda-imageresizer-test-002 \
    --statement-id s3-trigger

{
    "Statement": "{\"Sid\": \"s3-trigger\", \"Effect\": \"Allow\", \"Action\": \"lambda:InvokeFunction\", \"Resource\": \"arn:aws:lambda:us-west-2:000000000000:function:aws-lambda-image-resizer\", \"Principal\": {\"Service\": \"s3.amazonaws.com\"}, \"Condition\": {\"ArnLike\": {\"AWS:SourceArn\": \"arn:aws:s3:::awslambda-imageresizer-test-002\"}}}"
}
```

Now we'll add the bucket notification configuration so that our Lambda function is notified when anyone uploads a file with prefix "test-" and suffix ".jpg"
```sh
$ aws s3api put-bucket-notification-configuration --profile localstack \
    --bucket awslambda-imageresizer-test-002 \
    --notification-configuration '{
    "LambdaFunctionConfigurations": [
      {
        "LambdaFunctionArn": "arn:aws:lambda:us-west-2:000000000000:function:aws-lambda-image-resizer",
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {
          "Key": {
            "FilterRules": [
              {
                "Name": "prefix",
                "Value": "test-"
              },
              {
                "Name": "suffix",
                "Value": ".jpg"
              }
            ]
          }
        }
      }
    ]
  }'
```

Now let's test our setup by uploading a file.
```sh
$ aws --profile localstack s3 cp test-happy-smiley-face.jpg s3://awslambda-imageresizer-test-002/
```


You can check the Lambda logs
```sh
$ aws --profile localstack logs tail '/aws/lambda/aws-lambda-image-resizer' --follow
```
or using command
```sh
$ aws --profile localstack \
s3api put-object --bucket awslambda-imageresizer-test-002 \
--key test-happy-smiley-face.jpg --body=test-happy-smiley-face.jpg
```

We will check the logs. In order to do that we need to find the Cloudwatch LogGroup
```sh
$ aws --profile localstack --region us-west-2 logs describe-log-groups

{
    "logGroups": [
        {
            "logGroupName": "/aws/lambda/aws-lambda-image-resizer",
            "creationTime": 1721819360023,
            "metricFilterCount": 0,
            "arn": "arn:aws:logs:us-west-2:000000000000:log-group:/aws/lambda/aws-lambda-image-resizer:*",
            "storedBytes": 418
        }
    ]
}
```

Now we can check the logs to see how our function ran.
```sh
$ aws --profile localstack --region us-west-2 logs \
    tail /aws/lambda/aws-lambda-image-resizer
2024-07-24T11:09:20.014000+00:00 2024/07/24/[$LATEST]002eb047d7237ce44a04639e8cc81d21 START RequestId: 47063038-4a20-4326-b3ea-f0849a8d80e1 Version: $LATEST
2024-07-24T11:09:20.016000+00:00 2024/07/24/[$LATEST]002eb047d7237ce44a04639e8cc81d21 Got new image: test-happy-smiley-face.jpg from the bucket: awslambda-imageresizer-test-002
2024-07-24T11:09:20.018000+00:00 2024/07/24/[$LATEST]002eb047d7237ce44a04639e8cc81d21 Image resized.
2024-07-24T11:09:20.020000+00:00 2024/07/24/[$LATEST]002eb047d7237ce44a04639e8cc81d21 Image resized-test-happy-smiley-face.jpg uploaded.
2024-07-24T11:09:20.023000+00:00 2024/07/24/[$LATEST]002eb047d7237ce44a04639e8cc81d21 END RequestId: 47063038-4a20-4326-b3ea-f0849a8d80e1
2024-07-24T11:09:20.025000+00:00 2024/07/24/[$LATEST]002eb047d7237ce44a04639e8cc81d21 REPORT RequestId: 47063038-4a20-4326-b3ea-f0849a8d80e1 Duration: 179.32 ms     Billed Duration: 180 ms Memory Size: 128 MB  Max Memory Used: 128 MB
```

List bucket objects
```sh
$ aws s3api list-objects --bucket awslambda-imageresizer-test-002 --query 'Contents[].{Key: Key, Size: Size}' --profile localstack
[
    {
        "Key": "happy-smiley-face.jpg",
        "Size": 181915
    },
    {
        "Key": "resized-happy-smiley-face.jpg",
        "Size": 73688
    },
    {
        "Key": "resized-test-happy-smiley-face.jpg",
        "Size": 73688
    },
    {
        "Key": "test-happy-smiley-face.jpg",
        "Size": 181915
    }
]
```