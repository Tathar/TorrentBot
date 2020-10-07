#!/bin/sh
workFolder=$(readlink -f $(dirname $0))
cd $workFolder
pipenv run python torrent-bot.py $@