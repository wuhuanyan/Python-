import os
import requests
from bs4 import BeautifulSoup
from config import logger, Const, Config
import concurrent.futures
from mySelenium import getDriver, getContent
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import asyncio
import aiohttp
# import time


class IndexWeb:

    def __init__(self, home, lang):
        self.url = home
        self.lang = lang
        self.req = requests.get(self.url)
        self.soup = BeautifulSoup(self.req.content, 'html.parser')

    def getPageCount(self):
        pageArea = self.soup.find('ul', class_='pagination pagination-lg')
        liList = pageArea.find_all('li')
        lastPage = liList[-2].string
        return int(lastPage)


class Page:

    def __init__(self, home, lang, pageNum=1, content=None):
        self.home = home
        self.lang = lang
        self.pageNum = pageNum
        self.url = f'{home}page/{pageNum}{lang}'
        if content:
            self.soup = BeautifulSoup(content, 'html.parser')
        else:
            try:
                self.req = requests.get(self.url)
                self.soup = BeautifulSoup(self.req.content, 'html.parser')
            except Exception as e:
                print(str(e), home, lang, pageNum, content)
                raise e

    async def getMovieInfo(self):
        # 获取当页全部电影的标签
        movieTagList = self.soup.find_all('a', class_='movie-box')
        moviesList = []
        for m in movieTagList:
            movieDict = {}
            unitNum, title, href = self.getTitle(m)
            movieDict['番号'] = unitNum
            movieDict['标题'] = title
            movieDict['地址'] = href
            moviesList.append(movieDict)
            # logger.info('爬取到电影:' + "{" + f"'番号': '{unitNum}', '标题': '{title}', '地址': '{href}'" + "}")
        return moviesList

    def getTitle(self, movieTag):
        # 定位到每个电影
        img = movieTag.find('img')
        title = img.attrs['title']
        unitNum = title.split(' ')[0]
        title = title.split(' ')[1]
        href = movieTag.attrs['href']
        home = self.home[:-1] if self.home[-1] == '/' else self.home
        href = f'{home}{href}{self.lang}'
        return unitNum, title, href


class Movie:
    def __init__(self, movieInfo, content=None):
        self.url = movieInfo['地址']
        self.unitNum = movieInfo['番号']
        self.title = movieInfo['标题']
        self.movieInfo = movieInfo
        self.path = os.path.join(Const.MOVIE_PATH, self.unitNum)
        self.iniPath = os.path.join(self.path, f'{self.unitNum}.ini')
        self.initBagPath()
        self.config = Config(self.iniPath)
        if content:
            self.soup = BeautifulSoup(content, 'html.parser')
        else:
            self.req = requests.get(self.url)
            self.soup = BeautifulSoup(self.req.content, 'html.parser')

    def initBagPath(self):
        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def saveBaseInfo(self):
        section = '基本信息'
        for k, v in self.movieInfo.items():
            self.config.add_config(section, k, v)
        logger.info(f'[{self.unitNum}]基本信息已爬取!')

    def saveBigImg(self):
        section = '海报信息'
        if self.config.get_config(section, '进度') == '已完成':
            logger.info(f'[{self.unitNum}]{section}已爬取!')
            status = True
        else:
            bigImg = self.soup.find('a', class_='bigImage')
            imgName = f'{self.unitNum}.jpg'
            imgPath = os.path.join(self.path, imgName)
            imgHref = 'https:' + bigImg.attrs['href']
            try:
                imgFile = requests.get(imgHref, timeout=10)
                with open(imgPath, "wb")as f:
                    f.write(imgFile.content)
                self.config.add_config(section, '状态', '成功')
                status = True
            except Exception as e:
                str(e)
                self.config.add_config(section, '状态', '失败')
                self.config.add_config('图片信息', '状态', '失败')
                self.config.add_config('图片信息', '进度', '已完成')
                self.config.add_config('图片信息', '数量', '0')
                status = False
            self.config.add_config(section, '进度', '已完成')
            self.config.add_config(section, imgName, imgHref)
            logger.info(f'[{self.unitNum}]{section}已爬取!')
        return status

    def saveSampleImg(self):
        section = '图片信息'
        if self.config.get_config(section, '进度') == '已完成':
            logger.info(f'[{self.unitNum}]{section}已爬取!')
            status = True
        else:
            samImgList = self.soup.find_all('a', class_='sample-box')
            totalCount = len(samImgList)
            if totalCount == 0:
                self.config.add_config(section, '状态', '成功')
                self.config.add_config(section, '进度', '已完成')
                self.config.add_config(section, '数量', '0')
                status = True
            else:
                imgInfoList = []
                for i, img in enumerate(samImgList):
                    imgName = self.unitNum + '[' + "%03d" % i + '].jpg'
                    imgPath = os.path.join(self.path, imgName)
                    imgHref = 'https:' + img.attrs['href']
                    try:
                        imgFile = requests.get(imgHref, timeout=10)
                        with open(imgPath, "wb")as f:
                            f.write(imgFile.content)
                        imgInfoList.append([imgName, imgHref])
                    except Exception as e:
                        str(e)
                        break
                if len(imgInfoList) == totalCount:
                    self.config.add_config(section, '状态', '成功')
                    self.config.add_config(section, '进度', '已完成')
                    self.config.add_config(section, '数量', str(totalCount))
                    for i in imgInfoList:
                        self.config.add_config(section, i[0], i[1])
                    status = True
                else:
                    self.config.add_config(section, '状态', '失败')
                    self.config.add_config(section, '进度', '已完成')
                    self.config.add_config(section, '数量', str(totalCount))
                    status = False
            logger.info(f'[{self.unitNum}]{section}已爬取!')
        return status

    def saveDownLoad(self):
        section = '下载信息'
        if self.config.get_config(section, '进度') == '已完成':
            logger.info(f'[{self.unitNum}]{section}已爬取!')
            status = True
        else:
            driver = getDriver()
            num = 0
            downSize = None
            status = False
            try:
                content = getContent(driver, self.url)
                downSoup = BeautifulSoup(content, 'html.parser')
                downList = downSoup.find_all('td', style='text-align:center;white-space:nowrap')
                for d in downList:
                    downUrlList = d.find_all('a', style='color:#333', rel='nofollow')
                    for u in downUrlList:
                        if num % 2 == 0:
                            downSize = u.string
                            num += 1
                        else:
                            downHref = u.attrs['href']
                            num += 1
                            count = int(num / 2)
                            downSize = 'N/A' if downSize is None else downSize
                            option = '下载地址-' + "%02d" % count
                            value = '{' + f"'href': '{downHref.replace('%', '❀')}', 'size': '{downSize}'" + '}'
                            self.config.add_config(section, option, value)
                            status = True
                # if not status:
                #     logger.error('页面加载失败')
            except Exception as e:
                str(e)
                status = False
            if status:
                self.config.add_config(section, '状态', '成功')
            else:
                self.config.add_config(section, '状态', '失败')
            self.config.add_config(section, '进度', '已完成')
            logger.info(f'[{self.unitNum}]{section}已爬取!')
            # 测试
            # if self.config.get_config(section, '下载地址-01') == '':
            #     logger.error(f'[{self.unitNum}]{section}爬取出错!')
            # 测试
        return status


def main():
    home = Const.HOME  # 网站首页
    pageMaxWork = 1  # 最大进程页数,最大值不能超过CPU核心数量
    lang = Const.LANGUAGE_LIST[2]

    g = IndexWeb(home, lang)
    pageCount = g.getPageCount()
    with concurrent.futures.ProcessPoolExecutor(pageMaxWork) as executor:
        executor.map(partial(getPage, home, lang), range(1, pageCount+1))

    # for pageNum in range(1, pageCount+1):
    #     p = Page(home, lang, pageNum)
    #     movieList = p.getMovieInfo()
    #     for movie in movieList:
    #         m = Movie(movie)
    #         m.saveBaseInfo()
    #         if m.saveBigImg():
    #             m.saveSampleImg()
    #         m.saveDownLoad()
    #         exit()


def asyncMain():
    # pageMaxWork = 4  # 最大进程页数,最大值不能超过CPU核心数量
    home = Const.HOME  # 网站首页
    lang = Const.LANGUAGE_LIST[2]  # 选择语言
    pageCount = IndexWeb(home, lang).getPageCount()  # 总页数

    # 这里我想用进程池做异步操作
    # with concurrent.futures.ProcessPoolExecutor(pageMaxWork) as executor:
    #     executor.map(partial(getPage, home, lang), range(1, pageCount+1))
    loop = asyncio.get_event_loop()
    session = asyncGetSession()
    tasks = [asyncio.ensure_future(asyncGetPage(home, lang, pageNum)) for pageNum in range(1, pageCount + 1)]
    loop.run_until_complete(asyncio.wait(tasks))  # home:主页, lang:语言, pageCount:总页数
    loop.close()


async def asyncGetSession():
    return aiohttp.ClientSession()


async def asyncGetPages(home, lang, pageCount):
    topPageWebPath = Const.PAGE_WEB_PATH  # 保存页面web文件的文件夹
    for pageNum in range(1, pageCount+1):
        logger.warning('正在爬取第' + '%04d' % pageNum + '页!')
        pagePath = os.path.join(topPageWebPath, '%04d' % pageNum + '.txt')
        async with aiohttp.ClientSession() as sessionPage:
            # logger.warning('    第' + '%04d' % pageNum + '页数据----请求中!')
            page = await asyncGetPage(sessionPage, home, lang, pageNum)  # 这里应该怎么样遍历pageCount把页号传递进去？
            logger.warning('    第' + '%04d' % pageNum + '页数据----已到达!')
            if not os.path.exists(pagePath):
                with open(pagePath, 'w') as pageWeb:
                    pageWeb.write(page)
            logger.warning('完成爬取第' + '%04d' % pageNum + '页!')


async def asyncGetPage(home, lang, pageNum):
    topPageWebPath = Const.PAGE_WEB_PATH  # 保存页面web文件的文件夹
    pagePath = os.path.join(topPageWebPath, '%04d' % pageNum + '.txt')
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{home}page/{pageNum}{lang}') as respone:
            logger.warning('正在爬取第' + '%04d' % pageNum + '页!')
            page = await respone.text()
            logger.warning('    第' + '%04d' % pageNum + '页数据----已到达!')
            if not os.path.exists(pagePath):
                with open(pagePath, 'w') as pageWeb:
                    pageWeb.write(page)
            logger.warning('完成爬取第' + '%04d' % pageNum + '页!')
    return page


async def asyncGetMovie(session, movieInfo):
    url = movieInfo['地址']
    async with session.get(url) as respone:
        return await respone.text()


def getPage(home, lang, pageNum):
    print(f'第{pageNum}页开始爬取:')
    p = Page(home, lang, pageNum)
    movieList = p.getMovieInfo()
    with ThreadPoolExecutor(max_workers=30) as executor:
        executor.map(getMovie, movieList)


def getMovie(movieInfo):
    try:
        m = Movie(movieInfo)
        m.saveBaseInfo()
        if m.saveBigImg():
            m.saveSampleImg()
        m.saveDownLoad()
    except Exception as e:
        print(str(e))
        return


def checkDownLoad(unitNum):
    topPath = Const.MOVIE_PATH
    path = os.path.join(topPath, unitNum)
    iniPath = os.path.join(path, f'{unitNum}.ini')
    config = Config(iniPath)
    movieInfo = dict()
    movieInfo['地址'] = config.get_config('基本信息', '地址')
    movieInfo['番号'] = config.get_config('基本信息', '番号')
    movieInfo['标题'] = config.get_config('基本信息', '标题')
    m = Movie(movieInfo)
    m.saveDownLoad()


if __name__ == '__main__':
    main()
    # checkDownLoad('DDOB-048')
    # asyncMain()
