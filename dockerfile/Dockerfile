FROM python:3.8.7

RUN pip install neo4j requests beautifulsoup4 pyyaml

ADD ./WikiCrawler /opt/WikiCrawler/
ADD app.py /opt/app.py
ADD ./config /opt/config

WORKDIR /opt
