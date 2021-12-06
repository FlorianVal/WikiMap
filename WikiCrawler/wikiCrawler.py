import logging
import requests
import random
import time
import yaml
import re

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
        url = str(self.config.get("website") + str(url))
        req = requests.get(url)
        soup = BeautifulSoup(req.text, "html.parser")
        return soup

    def filter_links(self, item):
        # filter links to crawl
        return item.startswith("/wiki") and not item.startswith("/wiki/File")

    def get_links_from_page(self, soup_page):
        # get all links from page
        links = []

        for item in soup_page.select(f"{self.config.get('div_to_crawl')} a"):
            if item.has_attr("href") and self.filter_links(item["href"]):
                links.append(item["href"])
        return [res.split("/")[2] for res in list(set(links))]

    @staticmethod
    def remove_references(text):
        # remove references and multiple spaces
        return re.sub(" +", " ", (re.sub("[\[].*?[\]]", "", text)))

    def get_page_content(self, soup_page):
        # get content of page
        # For now only take paragraphs TODO: add ul, li
        content = soup_page.select(self.config.get("div_to_crawl"))[0].select("p, ol, h1, h2, h3, h4, h5, h6")
        # apply text method to each selected content and join them
        content = " ".join([self.remove_references(item.text) for item in content])
        # replace ' in content
        content = content.replace("'", " ").replace("\\", " ")
        return content


    def crawler(self, link):
        node_content = {}
        logging.info(f"Crawling : {str(link)}")
        webpage = self.get_page(link)
        links_in_page = self.get_links_from_page(webpage)
        node_content["Text"] = self.get_page_content(webpage)
        node_content["Title"] = str(link)
        self.database.add_new_page(node_content,links_in_page)

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
                logging.info(f"Doing : {str(link[0].get('Title'))}")
                self.crawler(link[0].get("Title"))
                #prevent ban IP
                time.sleep(self.config.get("time_between_request"))
