FROM python:3-alpine

RUN mkdir /app
WORKDIR /app
ADD mastodon_postbot.py /app/
ADD requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

CMD python mastodon-postbot.py