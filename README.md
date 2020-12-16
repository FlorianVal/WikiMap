# WikiMap
Let's map wikipedia

## WikiCrawler
Give all the article links in a given wikipedia article using [Scrapy](https://scrapy.org/) in python.

## Database

Datas are stored in a Neo4J database. For now, it is built up in docker-compose :

## Run
To run this project just do:

```
docker-compose up
```
This will build :
- A neo4j database
- A docker with Python and a Jupyter notebook

Jupyter will be accessible on 
```
localhost:8888
```
Neo4j control panel on
```
localhost:7474
```
## ToDo

Add Kerberos auth to neo4j, see : https://neo4j.com/docs/operations-manual/current/authentication-authorization/introduction/#auth-introduction under "Kerberos authentication and single sign-on" section
