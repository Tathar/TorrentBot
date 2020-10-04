#!/usr/bin/env python3

from collections import UserDict
from pathlib import Path

import validate
from configobj import ConfigObj

from ActionTag import ActionTag


class ConfiguartionError(Exception):
    pass


VALIDE_API = ("transmission-rpc", )
DEFAULT_TIMEOUT = 30000
DEFAULT_CONF = """
name = string()
url = string()
username = string()
password = string()

search_field_selector = string()
search_button_selector = string()
search_response_selector = string()

[login]
[going_search]
[going_download]
"""


def dict_as_timeout(dic) -> int:
    if "timeout" in dic:
        return int(dic["timeout"])

    return DEFAULT_TIMEOUT


def dict_as_error(dic) -> bool:
    if "error" in dic and (dic["error"] == "False" or dic["error"] == "false"):
        return False

    return True


class SiteConfig:
    def __init__(self, path):
        self.site = dict()
        path_file = Path(path)
        if path_file.exists():
            self._config_file = ConfigObj(str(path),
                                          configspec=DEFAULT_CONF.split("\n"))
        else:
            raise FileNotFoundError()

        validator = validate.Validator()
        self._config_file.validate(validator)

        self.name = self._config_file["name"]
        self.__username = None
        self.__password = None

        self.site["url"] = self._config_file["url"]
        self.site["search_field_selector"] = ActionTag(
            self._config_file["search_field_selector"],
            timeout=DEFAULT_TIMEOUT)
        self.site["search_button_selector"] = ActionTag(
            self._config_file["search_button_selector"],
            timeout=DEFAULT_TIMEOUT)
        self.site["search_response_selector"] = ActionTag(
            self._config_file["search_response_selector"],
            timeout=DEFAULT_TIMEOUT)

        self.site["download_link_selector"] = self._config_file[
            "download_link_selector"]

        self.site["going_login"] = self._create_action_tag(
            self._config_file["login"])
        self.site["going_search"] = self._create_action_tag(
            self._config_file["going_search"])
        self.site["going_download"] = self._create_action_tag(
            self._config_file["going_download"])

    @property
    def username(self) -> str:
        return self.__username

    @username.setter
    def username(self, username: str):
        self.__username = username
        self.site["going_login"] = self._create_action_tag(
            self._config_file["login"])

    @property
    def password(self) -> str:
        return self.__password

    @password.setter
    def password(self, password: str):
        self.__password = password
        self.site["going_login"] = self._create_action_tag(
            self._config_file["login"])

    def _create_action_tag(self, dic) -> list:
        ret = list()
        for key, value in dic.items():
            if key[:5] == "click":
                args = {"selector": value["selector"]}
                args["timeout"] = dict_as_timeout(value)
                args["error"] = dict_as_error(value)
                ret.append(ActionTag(**args))
            elif key[:8] == "username":
                args = {"selector": value["selector"]}
                args["data"] = self.__username
                args["timeout"] = dict_as_timeout(value)
                args["error"] = dict_as_error(value)
                ret.append(ActionTag(**args))
            elif key[:8] == "password":
                args = {"selector": value["selector"]}
                args["data"] = self.__password
                args["timeout"] = dict_as_timeout(value)
                args["error"] = dict_as_error(value)
                ret.append(ActionTag(**args))
            elif key[:5] == "clear":
                args = {"selector": value["selector"]}
                args["timeout"] = dict_as_timeout(value)
                args["error"] = dict_as_error(value)
                args["action"] = "clear"
                ret.append(ActionTag(**args))
            elif key[:4] == "wait":
                args = {"selector": value["selector"]}
                args["timeout"] = dict_as_timeout(value)
                args["error"] = dict_as_error(value)
                args["action"] = "wait"
                ret.append(ActionTag(**args))
        return ret


class GlobalConfig():
    def __init__(self, path):
        config_file = Path(path)
        if config_file.exists():
            self._param = ConfigObj(str(config_file))
        else:
            raise FileNotFoundError()

        #if root_download is not configured
        if "root_download" not in self._param.keys(
        ) or self._param["root_download"] is None:
            self._param["root_download"] = self._param["root_config"]

        #if sites_config is not configured
        if "sites_config" not in self._param.keys(
        ) or self._param["sites_config"] is None:
            self._param["sites_config"] = "./sites.d/"

        #if torrrent_client is not configured
        if "torrrent_client" not in self._param.keys(
        ) or self._param["torrrent_client"] is None:
            raise ConfiguartionError("torrrent_client")

        #if api is not configured
        if "api" not in self._param["torrrent_client"].keys(
        ) or self._param["torrrent_client"]["api"] not in VALIDE_API:
            raise ConfiguartionError("API")

    def __getitem__(self, key):
        return self._param[key]


class SerieConfig(UserDict):
    def __init__(self, path):
        super().__init__(self)
        config_file = Path(path)
        if config_file.exists():
            self._param = ConfigObj(str(config_file))
        else:
            raise FileNotFoundError()

        #if site is not configured
        if "site" not in self._param.keys() or self._param["site"] is None:
            raise ConfiguartionError("site")

        if isinstance(self._param["site"], str):
            self.site = [
                self._param["site"],
            ]
        elif isinstance(self._param["site"], list):
            self.site = self._param["site"]

        #if search_name is not configured
        if "search_name" not in self._param.keys(
        ) or self._param["search_name"] is None:
            raise ConfiguartionError("search_name")

        #if filters is not configured
        if "filters" not in self._param.keys(
        ) or self._param["filters"] == "None" or self._param[
                "filters"] == "none" or self._param["filters"] == "":
            self.data["filters"] = None
        else:
            self.data["filters"] = self._param["filters"]

        #if episode is not configured
        if "episode" not in self._param.keys(
        ) or self._param["episode"] is None:
            raise ConfiguartionError("episode")
        else:
            self._param["episode"] = int(self._param["episode"])

        #if index_episode is not configured
        if "index_episode" not in self._param.keys(
        ) or self._param["index_episode"] is None:
            raise ConfiguartionError("index_episode")

        #if path is not configured
        if "path" not in self._param.keys(
        ) or self._param["path"] == "None" or self._param["path"] == "none":
            self._param["path"] = config_file.parent

        #self.data["site"] = self._param["site"]
        self.data["search_name"] = self._param["search_name"]
        self.data["episode"] = self._param["episode"]
        self.data["index_episode"] = self._param["index_episode"]
        self.data["separator"] = self._param["separator"]
        self.data["path"] = self._param["path"]

    def write(self):
        self._param["episode"] = self.data["episode"]
        self._param.write()


if __name__ == "__main__":
    config = SiteConfig("./sites.d/ygg.conf")
    print(config.name)
    config.username = "tathar"
    config.password = "mot de passe"
    print(config.site)

    glob_config = GlobalConfig("./torrent-bot.conf")
    print(glob_config["site"]["ygg"]["password"])

    serie_config = SerieConfig("./series.trbot")
    print(serie_config.site)
    print(serie_config["search_name"])
    print(serie_config["episode"])
    print(serie_config["path"])

    # serie_config["episode"] += 1
    # serie_config.write()