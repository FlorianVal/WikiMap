import requests
import logging
import json
import yaml
import random
import time

from WikiCrawler.database import Neo4jDatabase

class ApiCrawler:

    def __init__(self, url):
        self.database = Neo4jDatabase(url)
        with open('config/crawler_config.yaml', 'r') as stream:
            self.config = yaml.load(stream, Loader=yaml.FullLoader)

        self.base_url = self.config['website']
        self.session = requests.Session()
        self.calls = 0

    def start(self):
        """Start the crawling process

        Args:
            title (str): title to start crawling from
        """
        nodes = self.database.get_all_nodes()
        if len(self.database.get_all_nodes()) == 0:
            title = "Philosophy"
        else:
            title = random.choice(self.database.get_lonely_nodes())[0].get('Title')
        links = self.get_links_from_page(title)
        text = self.get_text_from_page(title)

        # loop until full db completed
        while links:
            content = {'Title': title, 'Text': " ".join(list(text)).encode('utf-8').decode('utf-8')}
            links = list(links)
            links = list(filter(lambda x: ":" not in x, links))
            for i in range(10):
                #retry loop
                logging.info(f"Trying to add to db {title}")
                try:
                    self.database.add_new_page(content, links)
                    break
                except Exception as e:
                    logging.error(e)
                    logging.error(f"Page : {title} not added to database")
                    logging.info("Retrying...")
                    self.database.reload_connection()
                    time.sleep(5)
            
            lonely_node_titles = self.database.get_lonely_nodes()
            if len(lonely_node_titles) == 0:
                break
            lonely_node_title = random.choice(lonely_node_titles)

            title = lonely_node_title[0].get('Title')
            links = self.get_links_from_page(title)
            text = self.get_text_from_page(title)
            #prevent ban IP
            #time.sleep(self.config.get("time_between_request"))

    def count_calls(method):
        """Decorator to count number of api calls inside class
        """
        def wrapper(self, *args, **kwargs):
            self.calls += 1
            return method(self, *args, **kwargs)
        return wrapper

    def get_links_from_page(self, title):
        """Generator that returns the links from a page

        Args:
            title (str): Title of the page to get the links from 

        Yields:
            str: links from the page
        """
        next_page = None

        logging.info(f"Fetching links from page {title}")

        while True:

            data = self._get_links(title, next_page)

            if 'query' in data:
                if 'pages' in data['query']:
                    for page in data['query']['pages'].values():
                        if 'links' in page:
                            for link in page['links']:
                                yield link['title']
            else:
                logging.error(f"Error while fetching links from page {title}")
                break
            if 'continue' in data:
                next_page = data['continue']['plcontinue']
            else:
                next_page = None
                break

    @count_calls
    def _get_links(self, title, next_page=None):
        """Make a request to the API to get the links

        Args:
            title (str): Title of the page to get the links from
            next_page (str, optional): string for the plcontinue field . Defaults to None.

        Returns:
            json: json response from the API 
        """
        PARAMS = {
            'action': 'query',
            'prop': 'links',
            'format': 'json',
            'pllimit': 'max',
            'titles': title,
        }
        if next_page:
            PARAMS['plcontinue'] = next_page

        logging.info(f"Fetching links with request {PARAMS}")

        response = self.session.get(url=self.base_url, params=PARAMS)
        if '-1' in response.json()['query']['pages']:
            logging.error(f"Page {title} not found : {response.json()['query']['pages']}")
            self.database.update_node_not_found(title)
        elif 'normalized' in response.json()['query']:
            logging.error(f"Page {title} normalized : {response.json()['query']['normalized']}")

        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error with request : {self.base_url} with params {PARAMS}")
            raise Exception(f"Error while fetching links from page {title} error {response.status_code}")

    def get_text_from_page(self, title):
        """Generator that returns the text from a page

        Args:
            title (str): Title of the page to get the text from

        Yields:
            str: text from the page
        """

        next_page = None

        logging.info(f"Fetching text from page {title}")

        while True:

            data = self._get_text(title, next_page)

            if 'query' in data:
                if 'pages' in data['query']:
                    for page in data['query']['pages'].values():
                        if 'extract' in page:
                            yield page['extract']
            else:
                logging.error(f"Error while fetching text from page {title}")
                break
            if 'continue' in data:
                next_page = data['continue']['plcontinue']
            else:
                next_page = None
                break

    @count_calls    
    def _get_text(self, title, next_page=None):
        """Make a request to the API to get the text

        Args:
            title (str): Title of the page to get the text from
            next_page (str, optional): string for the excontinue field . Defaults to None.

        Returns:
            json: json response from the API
        """
        PARAMS = {
            'action': 'query',
            'prop': 'extracts',
            'format': 'json',
            'explaintext': '',
            'titles': title,
        }
        if next_page:
            PARAMS['excontinue'] = next_page

        logging.info(f"Fetching text with request {PARAMS}")

        response = self.session.get(url=self.base_url, params=PARAMS)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error while fetching links from page {title} error {response.status_code}")

    
    def get_images_from_page(self, title):
        """Generator that returns the images from a page

        Args:
            title (str): Title of the page to get the images from

        Yields:
            str: images from the page
        """

        next_page = None

        logging.info(f"Fetching images from page {title}")


        while True:

            data = self._get_images(title, next_page)

            if 'query' in data:
                if 'pages' in data['query']:
                    for page in data['query']['pages'].values():
                        if 'images' in page:
                            for image in page['images']:
                                # TODO download image and return np array

                                yield image['title']
            else:
                logging.error(f"Error while fetching images from page {title}")
                break
            if 'continue' in data:
                next_page = data['continue']['plcontinue']
            else:
                next_page = None
                break
    
    @count_calls
    def _get_images(self, title, next_page=None):
        """Make a request to the API to get the images

        Args:
            title (str): Title of the page to get the images from
            next_page (str, optional): string for the imcontinue field . Defaults to None.

        Returns:
            json: json response from the API
        """
        PARAMS = {
            'action': 'query',
            'prop': 'images',
            'format': 'json',
            'imlimit': 'max',
            'titles': title,
        }
        if next_page:
            PARAMS['imcontinue'] = next_page

        logging.info(f"Fetching images with request {PARAMS}")

        response = self.session.get(url=self.base_url, params=PARAMS)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error while fetching links from page {title} error {response.status_code}")
  