#!/usr/bin/env python
import sys
import os
import time
from time import gmtime, strftime
import logging
import json
import boto3
import csv
import bert_score
from bert_score import score

slang = "es"
dlang = "it"

PROCESSING_TIME_SECONDS = 1

def receive_message(queue_url):
    sqs = boto3.resource('sqs')
    queue = sqs.Queue(queue_url)
    s3 = boto3.resource('s3')
    output = []

    while True:
        print('Waiting for messages from the queue...')
        messages = queue.receive_messages(MessageAttributeNames=['All'], WaitTimeSeconds=2, MaxNumberOfMessages=10)

        if not len(messages):
            print('No messages were returned after last poll')
            continue

        for msg in messages:
            print('Processing message (ID: %s, body: %s)' % (msg.message_id, json.dumps(msg.body)))
            mid = msg.message_id
            stext = msg.message_attributes['stext']['StringValue']
            sref = []
            sref += [msg.message_attributes['sref']['StringValue']]

            # Translate
            translate = boto3.client('translate')
            result = translate.translate_text(Text=stext, SourceLanguageCode=slang, TargetLanguageCode=dlang)
            cand = []
            cand += [result["TranslatedText"]]

            # BERTscore
            print(f'BERTscore version: {bert_score.__version__}')
            print('Original text: %s, Translated text: %s, Reference text: %s' % (stext, cand, sref))
            if (len(cand) == len(sref)):
                P, R, F1 = score(cands=cand, refs=sref, lang=dlang, model_type='bert-base-multilingual-cased', verbose=False)
            else:
                print('Elements mismatch - len cand:', len(cand), 'len sref:', len(sref))
                continue
            #P = R = F1 = 1
            #print('BERTscores - P: %s, R: %s, F1: %s' % (P, R, F1))

            # Output
            output += [stext+"|"+sref[0]+"|"+cand[0]+"|{:.4f}".format(P.item())+"|{:.4f}".format(R.item())+"|{:.4f}\n".format(F1.item())]

            time.sleep(PROCESSING_TIME_SECONDS)
            msg.delete()
            print('Message processed (ID: %s)' % (mid))

        # Write output to S3 file
        if len(output) >= 1:
            print('Writing output to S3:', output)
            temp_csv_file = open('/tmp/csv_file.csv', 'w')
            for i in output:
                temp_csv_file.write(i)
            temp_csv_file.close()
        
            s3.Bucket(os.environ['BUCKET_NAME']).upload_file(
                '/tmp/csv_file.csv',
                os.environ['PREFIX']+'bert-score'+strftime("%Y%m%d%H%M%S", gmtime())+'.csv'
                )

if __name__ == '__main__':
    #if __name__ == '__main__': (Use this if deploying in Containers)
    #def lambda_handler(event, context): (Use this if testing in Lambda)
    if ('WORKER_SQS_QUEUE_URL' not in os.environ) or ('BUCKET_NAME' not in os.environ) or ('PREFIX' not in os.environ):
        logging.error('Missing environment variable. Execution requires: WORKER_SQS_QUEUE_URL, BUCKET_NAME, PREFIX.')
        sys.exit(1)

    receive_message(os.environ['WORKER_SQS_QUEUE_URL'])
