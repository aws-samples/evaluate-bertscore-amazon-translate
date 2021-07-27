FROM python:3.8-buster

RUN mkdir -p /srv/worker

COPY requirements.txt /srv/worker

WORKDIR /srv/worker

RUN pip install -r requirements.txt

COPY app.py   /srv/worker

RUN chmod +x /srv/worker/app.py

ENV WORKER_SQS_QUEUE_URL="<YOUR SQS QUEUE URL>"
ENV BUCKET_NAME="<YOUR S3 BUCKET NAME>"
ENV PREFIX="translate/score/"

ENTRYPOINT ["/srv/worker/app.py"]
