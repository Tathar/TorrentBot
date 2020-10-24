#!/usr/bin/env python3

import asyncio
import logging
from pathlib import Path

import aiohttp
from docopt import docopt
from pyppeteer import launch

import Config
from Series import Series

#from TorrentClient import TorrentStatus

DOC = """
torrent-bot
 
Usage:
  torrent-bot.py [--conf=file] [--logfile=file] [--loglevel=int] [--screenshot=<folder>]
 
Options:
  -h --help         
  --conf=<file>             fichier de configuration.[default: ./configuration/torrent-bot.conf]
  --logfile=<file>          fichier de log.[default: ./logfile.log]
  --loglevel=<int>          1=Debug 2=info 3=warning 4=error 5=CRITICAL. [default: 1]

"""

__doc__ = DOC

VERSION = '0.1'


def start_all_torrents(series, torrent_client):
    status = torrent_client.get_torrents_status(None)
    if len(status) > 1:
        free_space = status[0]["free_space"]
    for stats in status:
        if stats["pause"] and stats["progress"] != 1:
            for serie in series:
                for string in serie.search_name:
                    if string.lower() not in stats["name"].lower():
                        if stats["size"] < free_space - 100000000:
                            logger.info("start torrent %s", stats["name"])
                            torrent_client.start_torrent(stats["torrent_id"])
                            free_space -= stats["size"]
                        break


async def task(serie_config, browser_context, aio_session, torrent_client):

    config = serie_config
    serie = Series(**config)
    page = await browser_context.newPage()
    await page.setViewport({"width": 1920, "height": 1080})
    #await page.setUserAgent(user_agent)
    episode = serie.episode - 1
    while serie.episode > episode:
        episode = serie.episode
        async for torrent_file in serie.get_torrent(page, aio_session):

            if torrent_file is not None:
                logger.info("%s %i - in task: download torrent ok", serie.name,
                            serie.episode)

                if not serie.path.exists():
                    serie.path.mkdir(mode=0o777)

                torrent_id = torrent_client.add_torrent(
                    torrent_file, True, str(serie.path))

                config.read()
                config["episode"] = serie.episode + 1
                config.write()

                # await asyncio.sleep(10)
                torrent = torrent_client.get_torrent_status(torrent_id)
                if torrent.size <= torrent.free_space - 100000000:
                    torrent.start()
                    logger.info("%s %i- in task: start %s", serie.name,
                                serie.episode, torrent.name)

                logger.debug("%s %i - in task: Cancel pending Task",
                             serie.name, serie.episode)

                serie.stop()
                serie = Series(**config)

    try:
        await page.close()
    except Exception as error:
        logger.error("%s - in task: %s", serie.name, error)


async def create_task(global_conf, sites, browser_context, aio_session,
                      torrent_client):

    for filename in Path(global_conf["root_config"]).rglob("*.trbot"):
        serie_config = Config.SerieConfig(filename)
        serie_config["sites"] = list()
        for serie_config_site in serie_config.site:
            for site in sites:
                if serie_config_site == site.name:
                    serie_config["sites"].append(site.site)

        yield task(serie_config, browser_context, aio_session, torrent_client)


async def main():

    global_conf = Config.GlobalConfig()
    global_conf.init(args["--conf"])

    if global_conf["torrrent_client"]["api"] == "transmission-rpc":
        from TransmissionRpcClient import TransmissionRpcClient as TorrentClient

    torrent_client = TorrentClient(global_conf["torrrent_client"]["url"],
                                   global_conf["torrrent_client"]["port"],
                                   global_conf["torrrent_client"]["user"],
                                   global_conf["torrrent_client"]["password"])

    torrent_client.connect()

    sites = list()
    for filename in Path(global_conf["sites_config"]).rglob("*.conf"):
        site_config = Config.SiteConfig(filename)
        for gcs in global_conf["site"]:
            if gcs == site_config.name:
                site_config.username = global_conf["site"][gcs]["username"]
                site_config.password = global_conf["site"][gcs]["password"]
        sites.append(site_config)

    #user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36"

    chrome_args = ["-size=1920,1080", "--no-sandbox"]
    browser = await launch(args=chrome_args, headless=True)
    # browser = await launch(args=chrome_args, headless=False)
    #browser_context = await browser.createIncognitoBrowserContext()
    browser_context = browser
    # await browser.setWindowSize({"width": 1200, "height": 800})

    aio_session = aiohttp.ClientSession()

    tasks = [
        asyncio.create_task(coro) async for coro in create_task(
            global_conf, sites, browser_context, aio_session, torrent_client)
    ]
    # await download_torrents(param, browser_context)
    done, pending = await asyncio.wait(tasks,
                                       timeout=600,
                                       return_when=asyncio.ALL_COMPLETED)

    if len(pending) > 0:
        logger.error('Main timout occurs')
        for ptask in pending:
            ptask.cancel()

        await asyncio.wait(pending, timeout=10)

    await aio_session.close()
    await browser.close()
    # finally:
    #     await browser.close()

    # start_all_torrents([
    #     series[0],
    # ], torrent_client)


if __name__ == "__main__":

    args = docopt(__doc__, version=VERSION)
    logger = logging.getLogger("main")
    logger.setLevel(int(args["--loglevel"]) * 10)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')

    if args["--logfile"] is not None:
        path = Path(args["--logfile"]).parent
        if not path.exists():
            path.mkdir()
        fh = logging.FileHandler(filename=args["--logfile"], mode='w')
        fh.setLevel(int(args["--loglevel"]) * 10)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    else:
        sh = logging.StreamHandler()
        sh.setLevel(int(args["--loglevel"]) * 10)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    logger.info('Start AsyncIO')
    asyncio.run(main())
    logger.info('end of log file')
