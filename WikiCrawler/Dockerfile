FROM python:3.8.7

RUN pip install neo4j requests beautifulsoup4

ADD ./wikiCrawler.py /opt/wikiCrawler.py
ADD ./loop.py /opt/loop.py

CMD echo "Launching container"
CMD python3 /opt/loop.py