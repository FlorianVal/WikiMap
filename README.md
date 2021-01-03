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
- A docker with Python

Neo4j control panel on
```
localhost:7474
```

## Test with kubernetes (Failed)

## Installation

### minikube
```
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```
### kubectl
```
curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```
## Run
To run this project just do:
```
minikube start
```
```
cd Kubernetes_config
kubectl apply -f .
```
This will build :
- A neo4j database
- A docker with Python

Neo4j control panel on
```
localhost:7474
```

##Changes needed

In docker-compose.yml
```
version: '3'

services:
  neo4j:
    labels:
      kompose.service.type: loadbalancer
    image: neo4j:4.2
    restart: unless-stopped
    ports:
      - 7474:7474
      - 7687:7687
    volumes:
      - ./database/conf:/var/lib/neo4j/conf
      - ./database/data:/var/lib/neo4j/data
      - ./database/import:/var/lib/neo4j/import
      - ./database/logs:/logs
      - ./database/plugins:/var/lib/neo4j/plugins
  wikicrawler:
    labels:
      kompose.service.type: loadbalancer
    build: ./WikiCrawler/
    image: florianval/wiki-crawler:1.0.1
    volumes:
      - ./WikiCrawler/:/opt/
    ports:
      - "8888:8888"
