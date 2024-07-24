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