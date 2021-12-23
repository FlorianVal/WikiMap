import logging
import yaml
import logging.config
import os
import argparse

with open('config/log_config.yaml', 'r') as stream:
    config = yaml.load(stream, Loader=yaml.FullLoader)
    # get path to logs file in config and create folder if not already created
    log_path = config['handlers']['file']['filename']
    log_dir = os.path.dirname(log_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
logging.config.dictConfig(config)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the app')
    parser.add_argument('--action', type=str, help='Action to perform')
    parser.add_argument("--db", help="Link to db", nargs="?", default="bolt://db:7687")

    parser.add_argument("--link", help="Page to start crawling", default='Philosophy')

    args = parser.parse_args()

    if args.action == 'webcrawl':
        from WikiCrawler.wikiCrawler import Crawler
        Crawler(args.db).start(args.link)
    elif args.action == 'apicrawl':
        from WikiCrawler.apiCrawler import ApiCrawler
        ApiCrawler(args.db).start()
    