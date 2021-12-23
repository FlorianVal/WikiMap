from neo4j import GraphDatabase, unit_of_work

import types
import logging
import time

class Neo4jDatabase:
    # Wrapper around Neo4j database to easily use Cypher in Python
    def __init__(self, uri, user=None, password=None):
        logging.info("Connecting to Neo4j database")
        self.max_query_size = 10
        self.uri = uri
        if user and password:
            self.user = user
            self.password = password
        if user and password:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        else:
            self.driver = GraphDatabase.driver(uri)
        logging.info("Connected to Neo4j database")

    def reload_connection(self, uri = None):
        self.driver.close()
        if hasattr(self, "user") and hasattr(self, "password"):
            self.driver = GraphDatabase.driver(uri, auth=(self.user, self.password))
            return True
        else:
            logging.info("Reloading connection to Neo4j database")
            if uri:
                self.driver = GraphDatabase.driver(uri)
                return True
            else:
                self.driver = GraphDatabase.driver(self.uri)
                logging.info("Connection to Neo4j database reloaded")
                return True
        return False
                
    @staticmethod
    def clean_string(string):
        """Clean a string to be used in Cypher query

        Args:
            string (str): string to clean

        Returns:
            [str]: cleaned string
        """
        return string.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")


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
    def _update_node_not_found(self, tx, title):
        tx.run("MATCH (n:WikiPage {Title: \"%s\"}) SET n.NotFound = true" % title)

    @unit_of_work(timeout=5)
    def _get_lonely_nodes(self, tx):
        return [record for record in tx.run("MATCH (a:WikiPage) WHERE a.Analyzed is null AND a.NotFound is null RETURN a LIMIT 50;")]

    @unit_of_work(timeout=50)
    def _add_nodes(self, tx, query):
        try:
            return tx.run(query)
        except Exception as e:
            logging.error(query)
            logging.error(e)

    def get_all_nodes(self, limit=25):
        # Return all nodes in limit
        with self.driver.session() as session:
            return session.read_transaction(self._get_nodes, limit)

    def get_all_relations(self, limit=25):
        # Return all nodes in limit
        with self.driver.session() as session:
            return session.read_transaction(self._get_relations, limit)

    def get_lonely_nodes(self):
        with self.driver.session() as session:
            return self._get_lonely_nodes(session)

    def update_node_not_found(self, title):
        logging.info("Page not found : %s notified to db" % title)
        with self.driver.session() as session:
            session.write_transaction(self._update_node_not_found, title)
        return "Ok"

    def add_new_page(self, content, leaves):
        """add a new node in the database

        Args:
            content (dict): dict containing keys to add in node must contain Title
            leaves (list): list of nodes to link to the new node

        Returns:
            str: ok
        """
        # Add a new root node and create a relationship with all the leaves
        # This function create new leaves if it don't already exist

        list_of_leaves = self.split_list_in_sublist(leaves)
        title = content['Title']
        content.pop('Title')
        content["Analyzed"] = "true"
        for key in content:
            if content[key] == None:
                content.pop(key)
        content = ", ".join(['root.%s = \'%s\'' % (key, self.clean_string(value)) for (key, value) in content.items()])
        for leaves in list_of_leaves:
            query = "merge (root:WikiPage {Title: \"%s\"}) SET %s\n" % (title, content)
            for i, leave in enumerate(leaves):
                leave = leave.replace('"','\\"')
                query += "merge (%s:WikiPage {Title: \"%s\"})\n" % ("n"+str(i), leave)
            for i, leave in enumerate(leaves):
                query += "merge (root)-[:IsIn]->(%s)\n" % ("n"+str(i))
            with self.driver.session() as session:
                session.write_transaction(self._add_nodes, query)
            continue
        return "Ok"

    def split_list_in_sublist(self, leaves):
        # this function is made to split big list in many list
        # Trolling in school was fun :D
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