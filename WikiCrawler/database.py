from neo4j import GraphDatabase, unit_of_work

import logging

class Neo4jDatabase:
    # Wrapper around Neo4j database to easily use Cypher in Python
    def __init__(self, uri, user=None, password=None):
        logging.info("Connecting to Neo4j database")
        self.max_query_size = 10
        if user and password:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        else:
            self.driver = GraphDatabase.driver(uri)
        logging.info("Connected to Neo4j database")

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
        return [record for record in tx.run("MATCH (a:WikiPage) WHERE not ((a)-[:IsIn]->(:WikiPage)) RETURN a LIMIT 50;")]

    @unit_of_work(timeout=15)
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


    def update_node_not_found(self, title):
        logging.info("Page not found : %s notified to db" % title)
        with self.driver.session() as session:
            session.write_transaction(self._update_node_not_found, title)
        return "Ok"

    def add_new_page(self, content, leaves):
        # Add a new root node and create a relationship with all the leaves
        # This function create new leaves if it don't already exist
        list_of_leaves = self.split_list_in_sublist(leaves)
        content = ", ".join(['%s: \'%s\'' % (key, value) for (key, value) in content.items()])
        for leaves in list_of_leaves:
            query = "merge (%s:WikiPage {%s})\n" % ("root", content)
            for i, leave in enumerate(leaves):
                leave = leave.replace('"','\\"')
                query += "merge (%s:WikiPage {Title: \"%s\"})\n" % ("n"+str(i), leave)
            for i, leave in enumerate(leaves):
                query += "merge (%s)-[:IsIn]->(%s)\n" % ("root", "n"+str(i))
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