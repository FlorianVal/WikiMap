import logging
import argparse
import requests
import random
import time
import yaml

from urllib.parse import urljoin
from bs4 import BeautifulSoup

from WikiCrawler.database import Neo4jDatabase



class Crawler:
    def __init__(self, url):
        self.database = Neo4jDatabase(url)
        with open('config/crawler_config.yaml', 'r') as stream:
            self.config = yaml.load(stream, Loader=yaml.FullLoader)

    def start(self, link):
        self.controler(link)

    def get_page(self, url):
        url = urljoin(self.config.get("website"), str(url))
        req = requests.get(url)
        soup = BeautifulSoup(req.text, "html.parser")
        return soup

    def get_links_from_page(self, soup_page):
        # get all links from page
        links = []

        for item in soup_page.select("div.mw-parser-output a"):
            if item.has_attr("href") and item["href"].startswith("/wiki") and not item["href"].split("/")[2].startswith("File:"):
                links.append(item["href"])
        return [res.split("/")[2] for res in list(set(links))]

    def crawler(self, link):
        webpage = self.get_page(link)
        links_in_page = self.get_links_from_page(webpage)
        self.database.add_new_page(str(link),links_in_page)

    def controler(self, link):
        # implement crawling strategy
        self.crawler(link)
        with self.database.driver.session() as session:
            #init for while
            links = [link]

            # loop until full db completed
            while links:
                links = self.database._get_lonely_nodes(session)
                link = random.choice(links)
                logging.info(f"Doing : {str(link[0].get('link'))}")
                self.crawler(link[0].get("link"))
                #prevent ban IP
                time.sleep(self.config.get("time_between_request"))
