import json
import logging
import sys
import os
import boto3
from botocore.exceptions import ClientError
logger = logging.getLogger(__name__)

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

def send_message(message_body, message_attributes, queue):
    """
    Send a message to an Amazon SQS queue.
    :param message_body: The body text of the message.
    :param queue: The queue that receives the message.
    :param message_attributes: Custom attributes of the message. These are key-value
                               pairs that can be whatever you want.
    :return: The response from SQS that contains the assigned message ID.
    """
    if not message_attributes:
        message_attributes = {}

    try:
        response = sqs.send_message(
            QueueUrl=queue,
            DelaySeconds=2,
            MessageBody=message_body,
            MessageAttributes=message_attributes
        )
    except ClientError as error:
        logger.exception("Send message failed: %s", message_body)
        raise error
    else:
        return response

def read_new_file(record):
    # Read new file from S3:
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']
    print('Reading file:', key)
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read().decode('utf-8')

def lambda_handler(event, context):
    if ('WORKER_SQS_QUEUE_URL' not in os.environ):
        logging.error('Missing environment variable. Execution requires: WORKER_SQS_QUEUE_URL.')
        sys.exit(1)
    
    # Read new file from S3 and send rows to SQS:
    queue_url = os.environ['WORKER_SQS_QUEUE_URL']
    for file in event['Records']:
        file_text = read_new_file(file)
        #Send messages to the SQS queue:
        for line in file_text.splitlines():
            subtext = line.split('|')
            if len(subtext) == 2:
                message = {"stext":{"DataType":"String","StringValue": subtext[0] },"sref":{"DataType":"String","StringValue": subtext[1] }}
                print('Sending message:', json.dumps(message))
                response = send_message(line, message, queue_url)
                print('Received:', json.dumps(response))
            else:
                print('Wrong format for line, expected 2 strings separated by | but received:', json.dumps(subtext))

    return {
        'statusCode': 200,
        'body': 'OK'
    }
