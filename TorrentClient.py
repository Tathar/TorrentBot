#!/usr/bin/env python3
from abc import abstractmethod
from typing import List, Union
from typing_extensions import TypedDict

Movie = TypedDict('Movie', {'name': str, 'year': int})

# TorrentStatus = TypedDict(
#     "TorrentStatus", {
#         "Availabilities": float,
#         "downloading": bool,
#         "stoped": bool,
#         "progress": float,
#         "torrent_id": str,
#         "name": str,
#         "size": int,
#         "free_space": int,
#     })


class TorrentStatus():
    @abstractmethod
    def __init__(self, torrent_id: str, torrent_client):
        pass
        #self.torrent_id: str
        # self.availabilities: float
        # self.downloading: bool
        # self.paused: bool
        # self.progress: float
        # self.name: str
        # self.size: int
        # self.free_space: int

    @abstractmethod
    def refresh(self):
        raise NotImplementedError

    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError


class TorrentClient:
    def __init__(self, url: str, port: int, user: str, password: str):
        self.url = url
        self.port = port
        self.user = user
        self.password = password

    @abstractmethod
    def connect(self):
        raise NotImplementedError

    @abstractmethod
    def disconnect(self):
        raise NotImplementedError

    @abstractmethod
    def add_torrent(self, file: bytes, paused: bool, path: str = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def del_torrent(self, torrent_id: str):
        raise NotImplementedError

    @abstractmethod
    def get_torrent_status(self, torrent_id: str) -> TorrentStatus:
        raise NotImplementedError

    @abstractmethod
    def get_torrents_status(self,
                            torrent_id: List[str]) -> List[TorrentStatus]:
        raise NotImplementedError

    @abstractmethod
    def start_torrent(self, torrent_id: str):
        raise NotImplementedError

    @abstractmethod
    def stop_torrent(self, torrent_id: str):
        raise NotImplementedError
