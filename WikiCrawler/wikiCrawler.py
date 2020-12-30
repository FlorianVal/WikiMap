import scrapy
import logging
import json
import pandas as pd
import argparse

from neo4j import GraphDatabase, unit_of_work
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher
from scrapy import signals

class JsonWriterPipeline(object):

    def open_spider(self, spider):
        self.file = open('linksResult.jl', 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line)
        return item

class LinkSpider(scrapy.Spider):
    name = "links"

    def __init__(self, link):
        super(LinkSpider, self).__init__()
        self.start_urls = [f"https://en.wikipedia.org/{str(link)}"]

    custom_settings = {
        'LOG_LEVEL': logging.WARNING,
    }

    #Todo: fix parsing for wikipedia
    def parse(self, response):
        for link in response.css('div.mw-parser-output a'):
            linkString = str(link.css('::attr(href)').extract_first())
            if ( (linkString[0:6] == '/wiki/') & (linkString[6:11] != 'File:') ):
                yield {
                    'text': linkString,
                }

def get_links_from_page(url):
    results = []

    def crawler_results(signal, sender, item, response, spider):
        results.append(item)

    dispatcher.connect(crawler_results, signal=signals.item_passed)

    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })
    process.crawl(LinkSpider, link=args.link)
    process.start()  # the script will block here until the crawling is finished
    return [result["text"] for result in results]

class Neo4jDatabase:
    # Wrapper around Neo4j database to easily use Cypher in Python
    def __init__(self, uri, user=None, password=None):
        self.max_query_size = 10
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
        list_of_leaves = self.split_list_in_sublist(leaves)
        for leaves in list_of_leaves:
            query = "merge (%s:WikiPage {link: '%s'})\n" % ("root", root)
            for i, leave in enumerate(leaves):
                query += "merge (%s:WikiPage {link: '%s'})\n" % ("n"+str(i), leave)
            for i, leave in enumerate(leaves):
                query += "merge (%s)-[:IsIn]->(%s)\n" % ("root", "n"+str(i))
            with self.driver.session() as session:
                session.write_transaction(self._add_nodes, query)
        return "Ok"
    
    def split_list_in_sublist(self, leaves):
        # this function is made to split big list in many list
        _ = 0
        __ = 0
        ___ = []
        while _ < len(leaves):
            _ += 1
            if _ % self.max_query_size == 0:
                ___.append(leaves[__:_])
                __ = _
        if not __ == _:
            ___.append(leaves[__:_])
        return ___

def test_neo4j_wrapper():
    database = Neo4jDatabase("bolt://db:7687")
    database.add_new_page("leaf2",["leaf3", "leaf9", "Philosophy"])
    database.add_new_page("Philosophy", ["leaf3", "leaf1", "leaf5"])
    print(database.get_all_nodes()) # should print all nodes in database
    print("\n")
    print(database.get_all_relations()) # should print all relations in database


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("link", help="Page to crawl")
    parser.add_argument("db", help="Link to db", nargs="?", default="bolt://db:7687")
    args = parser.parse_args()

    links_in_page = get_links_from_page(args.link)
    print(links_in_page)
    database = Neo4jDatabase(args.db)

    database.add_new_page(str(args.link),links_in_page)



