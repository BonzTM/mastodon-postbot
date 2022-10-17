FROM python:3-alpine

RUN mkdir /app
WORKDIR /app
ADD mastodon-postbot.py /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD python mastodon-postbot.py