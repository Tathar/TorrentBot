#!/usr/bin/env python3

from typing import List
from copy import deepcopy
from urllib.parse import urlparse
from io import BytesIO
from transmission_rpc import Client, Torrent
from TorrentClient import TorrentClient, TorrentStatus


class TransmissionRpcStatus(TorrentStatus):
    def __init__(self, torrent_id: str, torrent_client: TorrentClient):
        super().__init__(torrent_id, torrent_client)
        if isinstance(torrent_id, str):
            copy = torrent_client.get_torrent_status(torrent_id)
            self.__dict__ = deepcopy(copy.__dict__)
        elif isinstance(torrent_id, Torrent):
            self._torrent = torrent_id
            self._torrent_client = torrent_client
            self._torrent_to_prop()

    def _torrent_to_prop(self):
        self.availabilities = 1 if self._torrent.leftUntilDone == 0 else self._torrent.desiredAvailable / self._torrent.leftUntilDone
        self.downloading = self._torrent.status == "downloading"
        self.stoped = self._torrent.status == "stopped"
        self.progress = self._torrent.progress
        self.torrent_id = self._torrent.id
        self.name = self._torrent.name
        self.size = self._torrent.totalSize
        self.free_space = self._torrent_client.free_space(
            self._torrent.downloadDir)
        print("free_space =", self.free_space)

    def refresh(self):
        self._torrent.refresh()
        self._torrent_to_prop()

    def start(self):
        self._torrent.start()

    def stop(self):
        self._torrent.stop()


class TransmissionRpcClient(TorrentClient):
    def __init__(self, url: str, port: int, user: str, password: str):
        super().__init__(url, port, user, password)
        parse = urlparse(url)

        self.client_args = {
            "protocol": parse.scheme,
            "host": parse.netloc,
            "port": port,
            "path": parse.path,
            "username": user,
            "password": password,
        }

        # print(self.client_args)
        self.session: Client = None

    def connect(self):
        self.session = Client(**self.client_args)

    def disconnect(self):
        pass

    def add_torrent(self, file: bytes, paused: bool, path: str = None) -> str:

        if self.session is None:
            raise ConnectionError()

        send = BytesIO(file)

        args = {
            "torrent": send,
            "paused": paused,
        }

        if path is not None:
            args["download_dir"] = path

        torrent = self.session.add_torrent(**args)
        return torrent.id

    def del_torrent(self, torrent_id: str):
        self.session.remove_torrent(ids=torrent_id, delete_data=True)

    def get_torrent_status(self, torrent_id: str) -> TorrentStatus:
        torrent = self.session.get_torrent(torrent_id=torrent_id)
        return TransmissionRpcStatus(torrent, self.session)

    def get_torrents_status(self,
                            torrent_id: List[str]) -> List[TorrentStatus]:
        torrents = self.session.get_torrents(ids=torrent_id)
        ret: List[TorrentStatus] = list()
        for torrent in torrents:
            ret.append(TransmissionRpcStatus(torrent, self.session))

        return ret

    def start_torrent(self, torrent_id: str):
        torrent = self.session.get_torrent(torrent_id=torrent_id)
        torrent.start()

    def stop_torrent(self, torrent_id: str):
        torrent = self.session.get_torrent(torrent_id=torrent_id)
        torrent.stop()

    # def _create_status(self, torrent: Torrent) -> TorrentStatus:
    #     return {
    #         "Availabilities":
    #         1 if torrent.leftUntilDone == 0 else torrent.desiredAvailable /
    #         torrent.leftUntilDone,
    #         "downloading":
    #         torrent.status == "downloading",
    #         "pause":
    #         torrent.status == "stopped",
    #         "progress":
    #         torrent.progress,
    #         "torrent_id":
    #         torrent.id,
    #         "name":
    #         torrent.name,
    #         "size":
    #         torrent.totalSize,
    #         "free_space":
    #         self.session.free_space(torrent.downloadDir),
    #     }


if __name__ == "__main__":
    rpc = TransmissionRpcClient(
        "https://torrent.tathar.net/transmission/rpc",
        443,
        "tathar",
        "c6d4c2ace50e654e0b0a0f7402c4f8c7",
    )

    rpc.connect()

    print(rpc.get_torrent_status(194))
