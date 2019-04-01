import os
from config import Const, Config
import aiohttp
import asyncio
from asyncMain import saveDownload, saveBigImg, saveSampleImg


def repairList():
    # 取出电影liebiao
    moviePath = Const.MOVIE_PATH
    movieList = []
    for i, j, k in os.walk(moviePath):
        if i == moviePath:
            movieList = j
            break

    # 遍历列表获取配置
    movieInfoList = []
    for i in movieList:
        iniPath = os.path.join(Const.MOVIE_PATH, i, f'{i}.ini')
        config = Config(iniPath)
        bigImgStatus = config.get_config('海报信息', '状态')
        samImgStatus = config.get_config('图片信息', '状态')
        if bigImgStatus == '成功' and samImgStatus != '成功':
            movieInfo = dict()
            movieInfo['番号'] = config.get_config('基本信息', '番号')
            movieInfo['地址'] = config.get_config('基本信息', '地址')
            movieInfo['标题'] = config.get_config('基本信息', '标题')
            movieInfoList.append(movieInfo)
    return movieInfoList


async def repair(movieInfo):
    topMoviePath = Const.MOVIE_PATH
    moviePath = os.path.join(topMoviePath, f"{movieInfo['番号']}")
    iniPath = os.path.join(moviePath, f"{movieInfo['番号']}.ini")
    config = Config(iniPath)
    async with aiohttp.ClientSession() as session:
        await saveBigImg(session, movieInfo, config, moviePath)
        await saveSampleImg(session, movieInfo, config, moviePath)
        await saveDownload(session, movieInfo, config)


def main():
    movieInfoList = repairList()
    loop = asyncio.get_event_loop()  # 启动异步首要语句
    if len(movieInfoList) > 0:
        moviess = [movieInfoList[i:i + 20] for i in range(0, len(movieInfoList), 20)]
        for movies in moviess:
            tasks = [asyncio.ensure_future(repair(movie)) for movie in movies]
            loop.run_until_complete(asyncio.wait(tasks))  # 全部页面的电影列表
    print(len(repairList()))


if __name__ == '__main__':
    main()
