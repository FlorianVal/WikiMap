#from https://www.jitsejan.com/using-scrapy-in-jupyter-notebook.html
import scrapy
from scrapy.crawler import CrawlerProcess

import json

class JsonWriterPipeline(object):

    def open_spider(self, spider):
        self.file = open('linksResult.jl', 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line)
        return item

import logging

class QuotesSpider(scrapy.Spider):
    name = "links"
    start_urls = [ 'https://en.wikipedia.org/wiki/Philosophy' ]
    custom_settings = {
        'LOG_LEVEL': logging.WARNING,
        'ITEM_PIPELINES': {'__main__.JsonWriterPipeline': 1}, # Used for pipeline 1
        'FEED_FORMAT':'json',                                 # Used for pipeline 2
        'FEED_URI': 'linksResult.json'                        # Used for pipeline 2
    }

    #Todo: fix parsing for wikipedia
    def parse(self, response):
        for link in response.css('div.mw-parser-output a'):
            linkString = str(link.css('::attr(href)').extract_first())
            if ( (linkString[0:6] == '/wiki/') & (linkString[6:11] != 'File:') ):
                yield {
                    'text': linkString,
                }

process = CrawlerProcess({
    'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
})

process.crawl(QuotesSpider)
process.start()

import pandas as pd
dfjl = pd.read_json('linksResult.jl', lines=True)
dfjl

from neo4j import GraphDatabase, unit_of_work

class Neo4jDatabase:
    # Wrapper around Neo4j database to easily use Cypher in Python
    def __init__(self, uri, user=None, password=None):
        if user and password:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        else:
            self.driver = GraphDatabase.driver(uri)

    def __del__(self):
        self.driver.close()

    @unit_of_work(timeout=5)
    def _get_nodes(self, tx, limit):
        return [dict(record) for record in tx.run(f"MATCH (node) RETURN (node) LIMIT {limit}")]

    @unit_of_work(timeout=5)
    def _get_relations(self, tx, limit):
        return [dict(record) for record in tx.run(f"MATCH (root)-[relation]->(leaf) RETURN root, relation, leaf LIMIT {limit}")]

    @unit_of_work(timeout=5)
    def _add_nodes(self, tx, query):
        return tx.run(query)

    def get_all_nodes(self, limit=25):
        # Return all nodes in limit
        with self.driver.session() as session:
            return session.read_transaction(self._get_nodes, limit)

    def get_all_relations(self, limit=25):
        # Return all nodes in limit
        with self.driver.session() as session:
            return session.read_transaction(self._get_relations, limit)

    def add_new_page(self, root, leaves):
        # Add a new root node and create a relationship with all the leaves
        # This function create new leaves if it don't already exist
        query = "merge (%s:WikiPage {link: '%s'})\n" % (root, root)
        for leave in leaves:
            query += "merge (%s:WikiPage {link: '%s'})\n" % (leave, leave)
        for leave in leaves:
            query += "merge (%s)-[:IsIn]->(%s)\n" % (root, leave)
        with self.driver.session() as session:
            return session.write_transaction(self._add_nodes, query)

def test_neo4j_wrapper():
    database = Neo4jDatabase("bolt://db:7687")
    database.add_new_page("leaf2",["leaf3", "leaf9", "Philosophy"])
    database.add_new_page("Philosophy", ["leaf3", "leaf1", "leaf5"])
    print(database.get_all_nodes()) # should print all nodes in database
    print("\n")
    print(database.get_all_relations()) # should print all relations in database
test_neo4j_wrapper()
