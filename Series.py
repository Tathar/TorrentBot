#!/usr/bin/env python3

# --- pour test----

from typing import List, Dict, AsyncGenerator
import re

# import asyncio
# import aiohttp
from urllib.parse import urlparse

from bs4 import BeautifulSoup as Soup
from pyppeteer import errors

from ActionTag import ActionTag


# search if title is in search
def as_one_ellement(search: List[str], title: str) -> bool:
    print("search " + str(search) + " in ", end="")
    if len(title) > 0:
        print(title, end="")
        for regex in search:
            p = re.compile(regex, re.IGNORECASE)
            result = p.search(title)
            if result:
                print(" Bads")
                return True
    else:
        print('"" No Title')
        return False

    print(" Ok")

    return False


# search if all elements of search is in title
def as_all_ellements(search: List[str], title: str) -> bool:
    print("search " + str(search) + " in ", end="")
    if len(title) > 0:
        print(title, end="")
        for regex in search:
            p = re.compile(regex, re.IGNORECASE)
            result = p.search(title)
            if not result:
                print(" Bads")
                return False
    else:
        print('"" No Title')
        return False

    print(" Ok")

    return True


def full_url(page, url: str) -> str:
    link = urlparse(url)
    if link.scheme == "":  # si le lien est incomplet (manque le http://www.site.org)
        base_url = urlparse(page.url)
        return base_url.scheme + "://" + base_url.netloc + url
    else:  # si le lien contient le domaine
        return url


class Series:
    def __init__(self, site, search_name, filters, episode: int, index_episode,
                 separator, path):
        self._count = 0
        # self.site = site
        if isinstance(site, list):
            self.site = site
        elif isinstance(site, dict):
            self.site = list()
            self.site.append(site)
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
        self.torrent_file = None
        self.url_cookies: Dict[str, str] = dict()

        self.regex: List[str] = list()
        self._searchs = list()

        names = list()
        for sep in self.separator:
            xname = ""
            for name in self.search_name:
                xname += str(name) + sep

            names.append(xname)

        for name in names:
            for index in self.index_episode:
                search = name + index + str(self.episode)
                self._searchs.append(search)

            # search = name + str(self.episode)
            # self._searchs.append(search)

    @property
    def episode(self):
        return self._episode

    @episode.setter
    def episode(self, value):
        self._episode = value

        if isinstance(self._filters,
                      list):  # on filtre sur le nom, le filtre et l épisode
            self.filters_and = self._filters
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

        self._searchs.clear()
        names = list()
        for sep in self.separator:
            xname = ""
            for name in self.search_name:
                xname += str(name) + sep

            names.append(xname)

        for name in names:
            for index in self.index_episode:
                search = name + index + str(self._episode)
                self._searchs.append(search)

            search = name + str(self._episode)
            self._searchs.append(search)

    async def _screenshot(self, page, name=""):
        await page.screenshot(
            {"path": "screenshot" + str(self._count) + str(name) + ".png"})
        self._count += 1

    async def _going_to(self, page, Dest):

        ret = None
        if isinstance(Dest, list):
            for dest in Dest:
                await self._screenshot(page)
                ret = await dest.run(page)
        elif isinstance(Dest, ActionTag):
            await self._screenshot(page)
            ret = await Dest.run(page)
        return ret

    async def login(self, page):
        """ return True if OK, False is not OK """

        print("in login goto " + self.site[0]["url"])
        try:
            await page.goto(self.site[0]["url"], {"timeout": 30000})
            await self._going_to(page, self.site[0]["going_login"])
        except errors.TimeoutError:
            return False

        return True

    async def search(self, page) -> AsyncGenerator[str, None]:
        """effectue une ou plusieurs recherches sur le sites et ajoute toute les pages coresspondantes dans self.torrent_page_url"""

        print("in search goto " + self.site[0]["url"])

        self.site[0]["url"] = page.url

        search_tag = list()
        for data in self._searchs:
            search_tag.append(
                ActionTag(self.site[0]["search_field_selector"].selector,
                          data))

        content = None
        for search in search_tag:
            # await page.goto(self.site[0]["url"], {"timeout": 30000})
            try:
                await self._going_to(page, self.site[0]["going_search"])
                print(search.data)
                await search.run(page)
                await self._screenshot(page)
                await self.site[0]["search_button_selector"].run(page)
                # sleep(10)
                if self.site[0]["search_response_selector"] is not None:
                    await self.site[0]["search_response_selector"].run(page)
                content = await page.content()  # return HTML document
                # print(content)

            except errors.TimeoutError:
                await self._screenshot(page, "_timeout")
                continue

            # print(content)
            soup = Soup(content, features="lxml")
            ahref = soup.find_all("a", href=True)
            print(ahref)
            for data in ahref:
                if as_all_ellements(self.filters_and, data.get_text()):
                    if as_one_ellement(self.filters_or, data.get_text()):
                        #self.torrent_page_url.append(full_url(page, data["href"]))
                        yield full_url(page, data["href"])

            # if len(self.torrent_page_url) >= 1:
            #     return True

        # if len(self.torrent_page_url) == 0:
        #     return False

        # self.torrent_page_url.reverse()  # on retourn la liste pour pouvoir facilement retiré les element dans l'ordre (pop)
        # return True

    async def get_torrent_url(self, torrent_page_url, page):
        """ return True if OK, False is not OK """
        print("in get_next_torrent_url goto " + torrent_page_url)
        await page.goto(torrent_page_url, {"timeout": 30000})
        await self._going_to(page, self.site[0]["going_download"])
        content = await page.content()  # return HTML document
        soup = Soup(content, features="lxml")

        html = soup.select_one(self.site[0]["download_link_selector"])

        print("html = " + str(html))

        print(type(html))
        # print(html["href"])

        if html is not None and "href" in html.attrs:
            self.torrent_url = full_url(page, html["href"])
            print(self.torrent_url)

            chrome_cookies = await page.cookies()
            for cookie in chrome_cookies:
                self.url_cookies[cookie["name"]] = cookie["value"]

            return True
        else:
            self.torrent_url = None

        return False

    async def download_torrent(self, aio_session):
        """return True if download success , False is not"""

        # with open("test.torrent", "wb") as file:
        #     r = requests.get(self.torrent_url, cookies=self.url_cookies,)
        #     file.write(r.html)
        async with aio_session.get(self.torrent_url,
                                   cookies=self.url_cookies) as resp:
            if resp.status == 200:
                self.torrent_file = await resp.read()
                return True

        return False
