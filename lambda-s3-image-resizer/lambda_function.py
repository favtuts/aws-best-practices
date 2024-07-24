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