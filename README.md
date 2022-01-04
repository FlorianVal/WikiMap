# WikiMap
A simple crawler of Wikipedia to create a graph database with links on Wikipedia pages

## WikiCrawler
Give all the article links in a given wikipedia article using BeautifulSoup in python.

## Database

Datas are stored in a Neo4J database. For now, it is built up in docker-compose :

## Run
To run this project just do:

```
docker-compose up
```
This will build :
- A neo4j database
- A docker with Python

Neo4j control panel on
```
localhost:7474
```

On this interface just click connect

and then write 
```
MATCH (n:WikiPage)-[r]->(m:WikiPage) return n
```

at the top of the page to see processed pages 
