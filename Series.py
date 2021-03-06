#!/usr/bin/env python3

import asyncio
import logging
import re
from os.path import exists
from pathlib import Path
from typing import AsyncGenerator, Dict, Generator, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup as Soup
from pyppeteer import errors

from ActionTag import ActionTag

logger = logging.getLogger("main.Series")
logger.addHandler(logging.NullHandler())


def clean_str(var):
    ret = " ".join(var.split())  #supression de espace en double
    ret = "\n".join(ret.split(","))  #remplacement des \n en double
    return ret


def full_url(page, url: str) -> str:
    link = urlparse(url)
    if link.scheme == "":  # si le lien est incomplet (manque le http://www.sites.org)
        base_url = urlparse(page.url)
        return base_url.scheme + "://" + base_url.netloc + url
    else:  # si le lien contient le domaine
        return url


class Series:
    def __init__(self, sites, search_name, filters, episode: int,
                 index_episode, separator, path):
        self._count = 0
        if isinstance(search_name, list):
            self.name = str()
            for part_name in search_name:
                self.name += " " + (str(part_name))
            self.name = self.name[1:]
        else:
            self.name = search_name
        # self.sites = sites
        if isinstance(sites, list):
            if len(sites) == 0:
                raise ValueError("Need a sites")
            self.sites = sites
        elif isinstance(sites, dict):
            self.sites = list()
            self.sites.append(sites)
        else:
            raise TypeError()

        # self.search_name = search_name
        if isinstance(search_name, list):
            self.search_name = search_name
        elif isinstance(search_name, str):
            self.search_name = list()
            self.search_name.append(search_name)
        else:
            raise TypeError()

        # self.index_episode = Index_episode
        if isinstance(index_episode, list):
            self.index_episode = index_episode
        elif isinstance(index_episode, str):
            self.index_episode = list()
            self.index_episode.append(index_episode)
        else:
            raise TypeError()

        self._filters = [filters] if isinstance(filters, str) else filters

        self._episode = episode

        if self._filters is not None:  # on filtre sur le nom, le filtre et l épisode
            self.filters_and = self._filters.copy()
            self.filters_and.extend(self.search_name)
        else:
            self.filters_and = self.search_name.copy()

        self.filters_or: List[str] = [
            index + str(self._episode) for index in self.index_episode
        ]

        self.filters_or.extend(
            [index + "0" + str(self._episode) for index in self.index_episode])

        logger.debug("%s %i - filter_or = '%s'", self.name, self._episode,
                     self.filters_or)

        # self.separator = separator
        if isinstance(separator, list):
            self.separator = separator
        elif isinstance(separator, str):
            self.separator = list()
            self.separator.append(separator)
        else:
            raise TypeError()

        self.path = path
        self.torrent_page_url: List[str] = list()
        self.torrent_url = ""
        #self.url: queues.Queue = queues.Queue(maxsize=1)
        #self._semaphore = asyncio.Semaphore(32)
        self.torrent_file: asyncio.Queue = asyncio.Queue()
        self.url_cookies: Dict[str, Dict[str, str]] = dict()

        self.regex: List[str] = list()
        self._searchs = list()

        self.canceled = False

        names = list()
        for sep in self.separator:
            xname = ""
            for name in self.search_name:
                xname += str(name) + sep

            names.append(xname)
            names.append(xname[:-len(sep)])

        for name in names:
            for index in self.index_episode:
                search = name + index + str(self.episode)
                self._searchs.append(search)
                search = name + index + "0" + str(self._episode)
                self._searchs.append(search)

            search = name + str(self.episode)
            self._searchs.append(search)
            search = name + "0" + str(self._episode)
            self._searchs.append(search)

    @property
    def episode(self):
        return self._episode

    @episode.setter
    def episode(self, value):
        self._episode = value

        if isinstance(self._filters,
                      list):  # on filtre sur le nom, le filtre et l épisode
            self.filters_and = self._filters.copy()
            self.filters_and.extend(self.search_name)
            # self.filters.append(str(self._episode))
        # elif isinstance(filters, str):
        #     self.filters_and = list()
        #     self.filters.append(filters)
        #     self.filters.append(str(episode))
        elif self._filters is None:
            self.filters_and = self.search_name.copy()
            # self.filters.append(str(self._episode))
        else:
            raise TypeError()

        self.filters_or: List[str] = [
            index + str(self._episode) for index in self.index_episode
        ]

        self.filters_or.extend(
            [index + "0" + str(self._episode) for index in self.index_episode])

        logger.debug("%s %i - filter_or = '%s'", self.name, self._episode,
                     self.filters_or)

        self._searchs.clear()
        names = list()
        for sep in self.separator:
            xname = ""
            for name in self.search_name:
                xname += str(name) + sep

            names.append(xname)
            names.append(xname[:-len(sep)])

        for name in names:
            for index in self.index_episode:
                search = name + index + str(self._episode)
                self._searchs.append(search)
                search = name + index + "0" + str(self._episode)
                self._searchs.append(search)

            search = name + str(self._episode)
            self._searchs.append(search)
            search = name + "0" + str(self._episode)
            self._searchs.append(search)

        # search if title is in search
    def as_one_ellement(self, search: List[str], title: str) -> bool:
        logger.debug("%s %i - as_one_ellement: search or '%s' in '%s'",
                     self.name, self._episode, str(search), title)
        if len(title) > 0:
            for regex in search:
                p = re.compile(regex, re.IGNORECASE)
                result = p.search(title)
                if result:
                    logger.info("%s %i - as_one_ellement: found '%s' in '%s'",
                                self.name, self._episode, str(regex), title)
                    return True
        else:
            logger.debug('%s %i - No Title', self.name, self._episode)
            return False

        logger.debug("%s %i - '%s' as_one_ellement: not found in '%s'",
                     self.name, self._episode, str(search), title)

        return False

    # search if all elements of search is in title
    def as_all_ellements(self, search: List[str], title: str) -> bool:
        logger.debug("%s %i - in as_all_ellements: search '%s' in '%s'",
                     self.name, self._episode, str(search), title)
        if len(title) > 0:
            for regex in search:
                p = re.compile(regex, re.IGNORECASE)
                result = p.search(title)
                if not result:
                    logger.debug(
                        "%s %i - as_all_ellements: not found '%s' in '%s'",
                        self.name, self._episode, str(regex), title)
                    return False
        else:
            logger.debug('%s %i - as_all_ellements: No Title', self.name,
                         self._episode)
            return False

        logger.info("%s %i - as_all_ellements: found '%s' in '%s'", self.name,
                    self._episode, str(search), title)

        return True

    async def _screenshot(self, page, name=""):
        main_logger = logging.getLogger("main")
        if main_logger.level <= 10:
            screenshot = Path(".")
            for handler in main_logger.handlers:
                try:
                    filenames = (handler.baseFilename)
                    screenshot = Path(filenames).parent
                    break
                except AttributeError:
                    pass

            screenshot /= str("screenshot " + str(self.name) + " " +
                              str(self._count) + str(name) + ".png")
            try:
                await page.screenshot({"path": str(screenshot)})
                logger.debug('%s %i - in _screenshot: make screenshout n°%i',
                             self.name, self._episode, self._count)
            except Exception as error:
                logger.error('%s %i - in _screenshot: %s', self.name,
                             self._episode, error)
            self._count += 1

    async def _going_to(self, page, Dest):

        if self.canceled:
            raise asyncio.CancelledError
        ret = None
        if isinstance(Dest, list):
            for dest in Dest:
                await self._screenshot(page)
                ret = await dest.run(page)
                if self.canceled:
                    raise asyncio.CancelledError
        elif isinstance(Dest, ActionTag):
            await self._screenshot(page)
            ret = await Dest.run(page)
        return ret

    async def _close_page(self, page):
        try:
            await page.close()
        except Exception as error:
            logger.error('%s %i - in _close_page: %s', self.name,
                         self._episode, error)

    async def _make_task(self, page):
        for site in self.sites:
            if await self.login(site, page):
                for coro in self.make_search_task(site, page):
                    yield asyncio.create_task(coro)

    async def get_torrent(self, page, aio_session):
        tasks = [task async for task in self._make_task(page)]

        while len(tasks) > 0:

            logger.debug("%s %i - in get_torrent: Wait task", self.name,
                         self.episode)

            done, tasks = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED)

            for this_task in done:
                try:
                    urls = this_task.result()
                except asyncio.CancelledError as error:
                    logger.debug("%s %i - in get_torrent: CancelledError : %s",
                                 self.name, self.episode, error)
                    continue
                except asyncio.InvalidStateError as error:
                    logger.error(
                        "%s %i - in get_torrent: InvalidStateError : %s",
                        self.name, self.episode, error)
                    continue
                except Exception as error:
                    logger.error("%s %i - in get_torrent: Exception : %s",
                                 self.name, self.episode, error)
                    continue

                if not isinstance(urls, list):
                    logger.debug("%s %i - in get_torrent: not found episode",
                                 self.name, self.episode)
                    continue

                for site, url in urls:
                    logger.debug("%s %i - in get_torrent: url = %s", self.name,
                                 self.episode, url)
                    if await self.get_torrent_url(site, url, page):
                        yield await self.download_torrent(site, aio_session)

    def stop(self):
        self.canceled = True

    async def login(self, site, page):
        """ return True if OK, False is not OK """

        logger.debug("%s %i - in login %s : befor wait logged = %s", self.name,
                     self._episode, site["name"], site["logged"])
        if not site["logged"]:
            with await site["lock"]:
                logger.debug("%s %i - in login %s : after wait logged = %s",
                             self.name, self._episode, site["name"],
                             site["logged"])

                if not site["logged"]:
                    logger.debug("%s %i - in login %s : goto %s", self.name,
                                 self._episode, site["name"],
                                 site["going_login"][0].selector)
                    try:
                        await self._going_to(page, site["going_login"])
                    except errors.TimeoutError as error:
                        logger.error("%s %i - in login %s : %s", self.name,
                                     self._episode, site["name"], error)
                        return False
                    except errors.NetworkError as error:
                        logger.error("%s %i - in login %s : %s", self.name,
                                     self._episode, site["name"], error)
                        return False
                    except errors.PageError as error:
                        logger.error("%s %i - in login %s : %s", self.name,
                                     self._episode, site["name"], error)
                        return False
                    except Exception as error:
                        logger.error("%s %i - in login %s : %s", self.name,
                                     self._episode, site["name"], error)
                        return False
                    site["logged"] = True

        return True

    def make_search_task(self, site, page) -> Generator[str, None, None]:
        """créé les tache de recherche"""

        logger.debug("%s %i - in make_search_task: goto %s", self.name,
                     self._episode, site["url"])

        #site["last_url"] = page.url

        search_tag = list()
        for data in self._searchs:
            search_tag.append(
                ActionTag(site["search_field_selector"].selector, data))

        for search in search_tag:

            yield self.search_task(site, page, search)

    async def search_task(self, site, page, search):
        """taches de recherche"""
        async with site["semaphore"]:

            logger.debug("%s %i - in search_task: search '%s'", self.name,
                         self._episode, search.data)
            content = None
            try:
                page = await page.browser.newPage()
                if self.canceled:
                    raise asyncio.CancelledError
                await page.setViewport({"width": 1920, "height": 1080})
                if self.canceled:
                    raise asyncio.CancelledError
                await self._going_to(page, site["going_search"])
                logger.debug("%s %i - in search_task: search.data = '%s'",
                             self.name, self._episode, search.data)
                if self.canceled:
                    raise asyncio.CancelledError
                await search.run(page)
                if self.canceled:
                    raise asyncio.CancelledError
                await self._screenshot(page)
                if self.canceled:
                    raise asyncio.CancelledError
                await site["search_button_selector"].run(page)
                if self.canceled:
                    raise asyncio.CancelledError
                # sleep(10)
                if site["search_response_selector"] is not None:
                    await site["search_response_selector"].run(page)
                if self.canceled:
                    raise asyncio.CancelledError
                content = await page.content()  # return HTML document
                # print(content)

            except asyncio.CancelledError:
                raise

            except errors.TimeoutError as error:
                logger.error("%s %i - in search_task : TimeoutError : %s",
                             self.name, self._episode, error)
                await self._close_page(page)
                # logger.debug("%s %i - in search_task: send = None", self.name,
                #              self._episode)
                #await self.url.put(None)
                raise asyncio.CancelledError("TimeoutError : {}".format(error))

            except errors.NetworkError as error:
                logger.error("%s %i - in search_task : NetworkError : %s",
                             self.name, self._episode, error)
                await self._close_page(page)
                # logger.debug("%s %i - in search_task: send = None", self.name,
                #              self._episode)
                #await self.url.put(None)
                raise asyncio.CancelledError("NetworkError : {}".format(error))

            except errors.PageError as error:
                logger.error("%s %i - in search_task : PageError : %s",
                             self.name, self._episode, error)
                await self._close_page(page)
                # logger.debug("%s %i - in search_task: send = None", self.name,
                #              self._episode)
                #await self.url.put(None)
                raise asyncio.CancelledError("PageError : {}".format(error))

            except Exception as error:
                logger.error("%s %i - in search_task : Exception : %s",
                             self.name, self._episode, error)
                await self._close_page(page)
                # logger.debug("%s %i - in search_task: send = None", self.name,
                #              self._episode)
                #await self.url.put(None)
                raise asyncio.CancelledError("Exception : {}".format(error))
            # except:
            #     await self._screenshot(page, "_except")
            #     await self.url.put(None)
            #     logger.debug("raise error '%s'", search.data)
            #     await self._close_page(page)
            #     raise asyncio.CancelledError

            # print(content)
            soup = Soup(content, features="lxml")
            ahref = soup.find_all("a", href=True)
            logger.debug("%s %i - in search_task: ahref = '%s'", self.name,
                         self._episode, clean_str(str(ahref)))
            logger.info("%s %i - in search_task: search episode %s of %s",
                        self.name, self._episode, self.episode,
                        " ".join(self.filters_and))
            urls = list()
            for data in ahref:
                if self.as_all_ellements(self.filters_and, data.get_text()):
                    if self.as_one_ellement(self.filters_or, data.get_text()):
                        #self.torrent_page_url.append(full_url(page, data["href"]))
                        url = full_url(page, data["href"])
                        logger.debug(
                            "%s %i - in search_task: append url = '%s'",
                            self.name, self._episode, url)
                        #await self.url.put(url)
                        urls.append((site, url))

            await self._close_page(page)
            # logger.debug("%s %i - in search_task: send = None", self.name,
            #              self._episode)
            #await self.url.put(None)
            return urls

    async def get_torrent_url(self, site, torrent_page_url, page):
        """ return True if OK, False is not OK """
        logger.debug("%s %i - in get_torrent_url: goto %s", self.name,
                     self._episode, torrent_page_url)
        try:
            await page.goto(torrent_page_url, {"timeout": 30000})
            await self._going_to(page, site["going_download"])
            content = await page.content()  # return HTML document
        except Exception as error:
            logger.error("%s %i - in get_torrent_url: %s", self.name,
                         self._episode, error)
            return False

        logger.debug("%s %i - in get_torrent_url: content = %s", self.name,
                     self._episode, clean_str(str(content)))
        soup = Soup(content, features="lxml")

        html = soup.select_one(site["download_link_selector"])

        logger.debug("%s %i - in get_torrent_url: html = %s", self.name,
                     self._episode, str(html))
        logger.debug("%s %i - in get_torrent_url: html is %s", self.name,
                     self._episode, type(html))

        # logger.debug(html["href"])

        if html is not None and "href" in html.attrs:
            self.torrent_url = full_url(page, html["href"])
            logger.debug("%s %i - in get_torrent_url: url = %s", self.name,
                         self._episode, self.torrent_url)

            try:
                chrome_cookies = await page.cookies()
            except Exception as error:
                logger.error("%s %i - in get_torrent_url: get cookies: %s",
                             self.name, self._episode, error)
                return False

            if site["name"] not in self.url_cookies:
                self.url_cookies[site["name"]] = dict()

            for cookie in chrome_cookies:
                self.url_cookies[site["name"]][
                    cookie["name"]] = cookie["value"]

            return True
        else:
            self.torrent_url = None

        return False

    async def download_torrent(self, site, aio_session):
        """return True if download success , False is not"""
        logger.info("%s %i - in download_torrent: download %s", self.name,
                    self._episode, str(self.torrent_url))

        # with open("test.torrent", "wb") as file:
        #     r = requests.get(self.torrent_url, cookies=self.url_cookies,)
        #     file.write(r.html)
        async with aio_session.get(
            self.torrent_url, cookies=self.url_cookies[site["name"]]) as resp:
            if resp.status == 200:
                logger.info(
                    "%s %i- in download_torrent: torrent %s episode %i downloaded",
                    self.name, self._episode, self.name, self._episode)
                return await resp.read()

        logger.error(
            "%s %i - in download_torrent: error at download torrent %s  episode %i ",
            self.name, self._episode, self.search_name, self._episode)

        return None
