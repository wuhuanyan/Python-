from config import logger
import requests
import aiohttp
import asyncio
from asyncMain import saveDownload, saveBigImg, saveSampleImg
from config import Config, Const
import os


async def asyncMain():
    url = 'https://www.gavbus668.com/video/SUPD-140.html'
    unitNum = 'SUPD-140'
    name = '标题标题'
    movieInfo = {
        '番号': unitNum,
        '标题': name,
        '地址': url
    }
    topMoviePath = Const.MOVIE_PATH
    moviePath = os.path.join(topMoviePath, f"{movieInfo['番号']}")
    iniPath = os.path.join(moviePath, f"{movieInfo['番号']}.ini")
    config = Config(iniPath)
    async with aiohttp.ClientSession() as session:
        await saveBigImg(session, movieInfo, config, moviePath)
        await saveSampleImg(session, movieInfo, config, moviePath)
        await saveDownload(session, movieInfo, config)


def main():

    loop = asyncio.get_event_loop()  # 启动异步首要语句
    loop.run_until_complete(asyncMain())


if __name__ == '__main__':
    main()
