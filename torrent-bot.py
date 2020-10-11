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
  --logfile=<file>          fichier de log.
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

    serie = Series(**serie_config)
    page = await browser_context.newPage()
    await page.setViewport({"width": 1920, "height": 1080})
    #await page.setUserAgent(user_agent)
    next_episode = True
    if await serie.login(page):
        while next_episode:
            next_episode = False
            async for url in serie.search(page):
                if await serie.get_torrent_url(url, page):
                    if await serie.download_torrent(aio_session):
                        logger.info("download torrent ok")
                        torrent_id = torrent_client.add_torrent(
                            serie.torrent_file, True, str(serie.path))

                        # await asyncio.sleep(10)
                        torrent = torrent_client.get_torrent_status(torrent_id)
                        if torrent.size <= torrent.free_space - 100000000:
                            torrent.start()
                            logger.info("start %s", torrent.name)
                        serie.episode += 1
                        next_episode = True
                        break

        if serie.episode != serie_config["episode"]:
            serie_config["episode"] = serie.episode
            serie_config.write()


def create_task(global_conf, sites, browser_context, aio_session,
                torrent_client):
    # series = list()
    for filename in Path(global_conf["root_config"]).rglob("*.trbot"):
        # logger.debug(filename)
        serie_config = Config.SerieConfig(filename)
        serie_config["site"] = list()
        for serie_config_site in serie_config.site:
            for site in sites:
                if serie_config_site == site.name:
                    serie_config["site"].append(site.site)

        root_config = Path(global_conf["root_config"]).parts
        file_path = Path(serie_config["path"]).parts

        # recherche de la racince commune entre root_config et file_path
        num_part = 0
        for part in root_config:
            if len(file_path) > num_part and part == file_path[num_part]:
                num_part += 1
            else:
                logger.debug("num_part = %i", num_part)
                break

        serie_config["path"] = str(
            Path(global_conf["root_download"]).joinpath(*file_path[num_part:]))

        # series.append(Series(**serie_config))
        yield task(serie_config, browser_context, aio_session, torrent_client)


async def main():
    #////////// OLD ///////
    # param = global_config()

    # param["semaphore"] = asyncio.Semaphore(4)

    # # try:
    # async with aiohttp.ClientSession(headers=headers) as session:
    #     tasks = [
    #         asyncio.create_task(coro)
    #         async for coro in pars_conf(param, session, browser_context)
    #     ]
    #     # await download_torrents(param, browser_context)
    #     await asyncio.wait(tasks)
    # # finally:
    # #     await browser.close()
    #///////// OLD ///////////

    global_conf = Config.GlobalConfig(args["--conf"])

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
    # browser_context = await browser.createIncognitoBrowserContext()
    browser_context = browser
    # await browser.setWindowSize({"width": 1200, "height": 800})

    aio_session = aiohttp.ClientSession()

    tasks = [
        asyncio.create_task(coro) for coro in create_task(
            global_conf, sites, browser_context, aio_session, torrent_client)
    ]
    # await download_torrents(param, browser_context)
    await asyncio.wait(tasks)

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

    logger.debug('Start')
    asyncio.run(main())
    logger.debug('end')
