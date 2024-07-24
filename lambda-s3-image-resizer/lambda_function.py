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