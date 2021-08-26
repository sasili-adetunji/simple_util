import time
from datetime import datetime
from models import Article
import asyncio
import logging
import sys
import aiohttp


def remove_html_markup(s):
    tag = False
    quote = False
    out = ""
    for c in s:
        if c == '<' and not quote:
            tag = True
        elif c == '>' and not quote:
            tag = False
        elif (c == '"' or c == "'") and tag:
            quote = not quote
        elif not tag:
            out = out + c
    return out

async def fetch_articles_list(url, session):
    """
    GET request wrapper to fetch all the articles list.
    """

    resp = await session.request(method="GET", url=url)
    resp.raise_for_status()
    logging.info("Got response [%s] for URL: %s", resp.status, url)
    articles = await resp.json()
    return articles

async def fetch_article_details(url, session):
    """
    GET request wrapper to fetch each articles details.
    """
    try:
        articles = await fetch_articles_list(url=url, session=session)
    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as e:
        logging.error(
            "aiohttp exception for %s [%s]: %s",
            url,
            getattr(e, "status", None),
            getattr(e, "message", None),
        )
    except Exception as e:
        logging.exception(
            "Non-aiohttp exception occured:  %s", getattr(e, "__dict__", {})
        )
    else:
        for article in articles:
            u = 'https://mapping-test.fra1.digitaloceanspaces.com/data/articles/' + article['id'] + '.json'
            resp = await session.request(method="GET", url=u)
            resp.raise_for_status()
            logging.info("Got response [%s] for URL: %s", resp.status, url)
            details = await resp.json()
            if details['pub_date']:
                details['publication_date'] = datetime.strptime(details['pub_date'], "%Y-%m-%d-%H;%M;%S")
                del details['pub_date']
            if details['mod_date']:
                details['modification_date'] = datetime.strptime(details['mod_date'], "%Y-%m-%d-%H:%M:%S")
                del details['mod_date']
            if details['sections']:
                for i in details['sections']:
                    if i['text']:
                        i['text'] = remove_html_markup(i['text'])
            return details

async def fetch_media(url, session):
    try:
        articles = await fetch_articles_list(url=url, session=session)
    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as e:
        logging.error(
            "aiohttp exception for %s [%s]: %s",
            url,
            getattr(e, "status", None),
            getattr(e, "message", None),
        )
    except Exception as e:
        logging.error(
            "Non-aiohttp exception occured:  %s", getattr(e, "__dict__", {})
        )
    else:
        for article in articles:
            try:
                r = 'https://mapping-test.fra1.digitaloceanspaces.com/data/media/' + article['id'] + '.json'
                resp = await session.request(method="GET", url=r)
                logging.info("Got response [%s] for URL: %s", resp.status, url)
                details = await resp.json()
                return details
            except Exception as e:
                logging.error(
                    "Fetch media aiohttp exception for %s [%s]: %s",
                    url,
                    getattr(e, "status", None),
                    getattr(e, "message", None),
                )
                continue

async def run_all(url):
    async with aiohttp.ClientSession() as session:
        media = await fetch_media(url=url, session=session)
        article = await fetch_article_details(url=url, session=session)
        data = { **media[0], **article }
        model = Article(**data)
        print(model)


if __name__ == "__main__":
    import sys
    assert sys.version_info >= (3, 7), "Script requires Python 3.7+."
    url = 'https://mapping-test.fra1.digitaloceanspaces.com/data/list.json'
    while True:
        t = time.time()
        asyncio.run(run_all(url))
        t = time.time()-t
        time.sleep(3 - t)
