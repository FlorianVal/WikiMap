import logging
import argparse
import requests
import random
import time

from bs4 import BeautifulSoup
from neo4j import GraphDatabase, unit_of_work

logging.basicConfig(level=logging.INFO)

def get_links_from_page(url):
    url = f"https://en.wikipedia.org/wiki/{str(url)}"
    req = requests.get(url)
    soup = BeautifulSoup(req.text, "html.parser")

    links = []

    for item in soup.select("div.mw-parser-output a"):
        if item.has_attr("href") and item["href"].startswith("/wiki"):
            links.append(item["href"])
    return [res.split("/")[2] for res in list(set(links))]

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
    def _get_relations(self, tx, link, limit):
        #return [dict(record) for record in tx.run(f"MATCH (root)-[relation]->(leaf) RETURN root, relation, leaf LIMIT {limit}")]
        return [record for record in tx.run("MATCH (:WikiPage {" + f"link: \"{str(link)}\"" + "}" + f")-[relation]-(leaf) RETURN leaf LIMIT {limit}")]
   
    @unit_of_work(timeout=5)
    def _get_lonely_nodes(self, tx):
        return [record for record in tx.run("MATCH (a:WikiPage) WHERE not ((a)-[:IsIn]->(:WikiPage)) RETURN a LIMIT 50;")]

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
            root = root.replace('"','\\"')
            query = "merge (%s:WikiPage {link: \"%s\"})\n" % ("root", root)
            for i, leave in enumerate(leaves):
                leave = leave.replace('"','\\"')
                query += "merge (%s:WikiPage {link: \"%s\"})\n" % ("n"+str(i), leave)
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

def crawler(database, link):
    links_in_page = get_links_from_page(link)
    database.add_new_page(str(link),links_in_page)

def controler(database, link):

    crawler(database, link)

    with database.driver.session() as session:
        #init for while
        links = [link]

        # loop until full db completed
        while links:
            links = database._get_lonely_nodes(session)
            link = random.choice(links)
            logging.info(f"Doing : {str(link[0].get('link'))}")
            crawler(database, link[0].get("link"))
            #prevent ban IP
            time.sleep(2)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("link", help="Page to crawl")
    parser.add_argument("db", help="Link to db", nargs="?", default="bolt://db:7687")
    args = parser.parse_args()
    logging.info(f"Initialising Crawler on {args.link}")
    #Db initialisation
    database = Neo4jDatabase(args.db)

    controler(database, args.link)
