import os
import asyncio
import aiohttp
from model import IndexWeb, Page
from config import logger, Const, Config
import datetime
import shutil
from bs4 import BeautifulSoup
# from mySelenium import getDriver, getContent
from concurrent.futures._base import TimeoutError as connTimeoutError
from aiohttp.client_exceptions import ClientConnectorError
import time
from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from email.header import Header
from aiohttp.client_exceptions import ServerDisconnectedError
# from repairSam import main as repairMain


def asyncMain(sessionCount, remove=False):
    # 编辑基本信息
    sem = asyncio.Semaphore(sessionCount)
    home = Const.HOME  # 网站首页
    lang = Const.LANGUAGE_LIST[1]  # 选择语言
    pageCount = IndexWeb(home, lang).getPageCount()  # 总页数
    # pageCount = 5

    if remove:
        if os.path.exists(Const.PAGE_WEB_PATH):
            shutil.rmtree(Const.PAGE_WEB_PATH)
        os.mkdir(Const.PAGE_WEB_PATH)
    pageTuple = []
    step = 50
    stepNum = int(pageCount / step)
    for i in range(0, stepNum + 1):
        startPage = i * step + 1
        endPage = (i + 1) * step
        if endPage > pageCount:
            endPage = pageCount
        pageTuple.append((startPage, endPage))
    pageTuple = [(1, 1)]
    totalStartTime = datetime.datetime.now()
    loop = asyncio.get_event_loop()  # 启动异步首要语句
    for s, e in pageTuple:
        startTime = datetime.datetime.now()  # 获取启动时间
        # 调用异步获取每页的源代码
        pages = loop.run_until_complete(asyncGetPages(sem, home, lang, s, e))[0]
        logger.info('加载列表页面完毕!')
        # 把每页的源代码传递到asyncGetMovies,构建我创建的Page对象
        tasks = [asyncio.ensure_future(asyncGetMovies(home, lang, page.result())) for page in pages]
        movieList = loop.run_until_complete(asyncio.wait(tasks))[0]  # 全部页面的电影列表
        logger.info('加载电影页面完毕!')
        # 把所有页面的电影列表拼成一个列表
        movieList = [movies.result() for movies in movieList]
        movies = []
        unitNumList = []
        for i in movieList:
            for j in i:
                if j['番号'] not in unitNumList:
                    unitNumList.append(j["番号"])
                    movies.append(j)
        logger.info('加载电影列表完毕!')
        # 爬取电影
        loop.run_until_complete(asyncGetMovie(sem, movies))

        endTime = datetime.datetime.now()  # 获取结束时间
        logger.info('耗时:' + str(endTime - startTime))  # 打印耗时
        time.sleep(1)
    # loop.close()  # 关闭异步
    totalEndTime = datetime.datetime.now()
    payTime = str(totalEndTime - totalStartTime)
    logger.info('总耗时:' + payTime)
    return payTime


def getStatus(payTime=None):
    movieList = []
    for i, j, k in os.walk(Const.MOVIE_PATH):
        if i == Const.MOVIE_PATH:
            movieList = j
            break
    bigImgCount = 0
    samImgCount = 0
    downloadCount = 0
    allCount = 0
    for m in movieList:
        iniPath = os.path.join(Const.MOVIE_PATH, m, f'{m}.ini')
        config = Config(iniPath)
        bigImgStatus = config.get_config('海报信息', '状态')
        bigImgCount = bigImgCount + 1 if bigImgStatus == '成功' else bigImgCount
        samImgStatus = config.get_config('图片信息', '状态')
        samImgCount = samImgCount + 1 if samImgStatus == '成功' else samImgCount
        downloadStatus = config.get_config('下载信息', '状态')
        downloadCount = downloadCount + 1 if downloadStatus == '成功' else downloadCount
        if bigImgStatus == '成功' and samImgStatus == '成功' and downloadStatus == '成功':
            allCount += 1
    totalCount = len(movieList)
    logger.info(f'海报信息:{bigImgCount}/{totalCount}')
    logger.info(f'图片信息:{samImgCount}/{totalCount}')
    logger.info(f'下载信息:{downloadCount}/{totalCount}')
    logger.info(f'总体信息:{allCount}/{totalCount}')
    content = f'海报信息:{bigImgCount}/{totalCount}={totalCount-bigImgCount}\n'
    content += f'图片信息:{samImgCount}/{totalCount}={totalCount-samImgCount}\n'
    content += f'下载信息:{downloadCount}/{totalCount}={totalCount-downloadCount}\n'
    content += f'总体信息:{allCount}/{totalCount}={totalCount-allCount}\n'
    content += f'总体耗时:{payTime}'
    send_email(content)
    return totalCount - allCount


def send_email(content):
    """
    用邮件发送json数据给接收人
    :return:
    """
    smtp = SMTP_SSL(Const.FROM_EMAIL_SMTP)
    smtp.ehlo(Const.FROM_EMAIL_SMTP)
    smtp.login(Const.FROM_EMAIL_ADDR, Const.FROM_EMAIL_PASSWD)
    dtStr = '[{dt:%Y-%m-%d %H:%M:%S}]'.format(dt=datetime.datetime.now())
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = Header(f'{dtStr}日志信息')
    msg['from'] = Const.FROM_EMAIL_ADDR
    msg['to'] = Const.FROM_EMAIL_ADDR
    smtp.sendmail(Const.FROM_EMAIL_ADDR, Const.FROM_EMAIL_ADDR, msg.as_string())
    smtp.quit()
    logger.info('日志邮件已发送!')


async def asyncGetPages(sem, home, lang, startPageNum, endPageNum):
    async with aiohttp.ClientSession() as session:  # 给所有的请求，创建同一个session
        async with sem:
            tasks = [asyncio.ensure_future(asyncFetchPages(session, home, lang, pageNum)) for pageNum in
                     range(startPageNum, endPageNum + 1)]
            return await asyncio.wait(tasks)


async def asyncFetchPages(session, home, lang, pageNum, reStartNum=1):
    topPageWebPath = Const.PAGE_WEB_PATH  # 保存页面web文件的文件夹
    pagePath = os.path.join(topPageWebPath, '%04d' % pageNum + '.txt')
    if not os.path.exists(pagePath):
            try:
                async with session.get(f'{home}page/{pageNum}{lang}') as respone:
                    page = await respone.text()
                    with open(pagePath, 'w') as pageWeb:
                        pageWeb.write(page)
                logger.info('完成爬取第' + '%04d' % pageNum + '页!')
            except Exception as e:
                reStartNum += 1
                if reStartNum > Const.MAX_FAIL_NUM:
                    if isinstance(e, connTimeoutError) or isinstance(e, ClientConnectorError)\
                            or isinstance(e, ServerDisconnectedError):
                        return None
                    else:
                        msg = f'爬取第[{pageNum}]页时,出现[{str(e)}]错误!'
                        logger.error(msg)
                        raise e
                else:
                    return await asyncGetPages(session, home, lang, pageNum, reStartNum)
    else:
        with open(pagePath, 'r') as pageWeb:
            page = pageWeb.read()
        logger.info('完成提取第' + '%04d' % pageNum + '页!')
    if page:
        return page
    else:
        logger.error('失败提取第' + '%04d' % pageNum + '页!')
        raise Exception('失败提取第' + '%04d' % pageNum + '页!')


async def asyncGetMovies(home, lang, content):
    if content is None:
        return []
    p = Page(home, lang, content=content)
    return await p.getMovieInfo()


async def asyncGetMovie(sem, movies):
    async with aiohttp.ClientSession() as session:  # 给所有的请求，创建同一个session
        async with sem:
            tasks = [asyncio.ensure_future(asyncFetchMovie(session, movie)) for movie in movies]
            return await asyncio.wait(tasks)


async def asyncFetchMovie(session, movieInfo):

    topMoviePath = Const.MOVIE_PATH
    moviePath = os.path.join(topMoviePath, f"{movieInfo['番号']}")
    iniPath = os.path.join(moviePath, f"{movieInfo['番号']}.ini")
    # shutil.rmtree(moviePath)
    if not os.path.exists(moviePath):
        os.mkdir(moviePath)
    if not os.path.exists(iniPath):
        with open(iniPath, 'w') as f:
            f.write('')
    config = Config(iniPath)
    longInfo = False
    bigImgStatus = True
    if config.get_config('基本信息', '番号') == '':
        await saveBaseInfo(movieInfo, config)
    if config.get_config('海报信息', '状态') != '成功':
        bigImgStatus = await saveBigImg(session, movieInfo, config, moviePath)
        longInfo = True
    if config.get_config('图片信息', '状态') != '成功' and bigImgStatus:
        await saveSampleImg(session, movieInfo, config, moviePath)
        longInfo = True
    if config.get_config('下载信息', '状态') != '成功':
        await saveDownload(session, movieInfo, config)
        longInfo = True
    if longInfo is True:
        logger.info(f"[{movieInfo['番号']}]爬取完成!")
    return None


async def saveBaseInfo(movieInfo, config):
    section = '基本信息'
    for k, v in movieInfo.items():
        config.add_config(section, k, v)
    # logger.info(f"[{movieInfo['番号']}]基本信息已爬取!")


async def saveBigImg(session, movieInfo, config, moviePath, reStartNum=1):
    section = '海报信息'
    bigImgStatus = config.get_config(section, '状态')
    if bigImgStatus == '成功':
        # logger.info(f'[{movieInfo["番号"]}]{section}已被成功爬取!')
        return True
    else:
        imgName = f"{movieInfo['番号']}.jpg"
        imgPath = os.path.join(moviePath, imgName)
        imgHref = None
        tmpImgHref = None
        for lang in Const.LANGUAGE_LIST:
            url = movieInfo['地址'] + lang
            try:
                async with session.get(url, timeout=Const.TIMEOUT) as moviePage:
                    movie = await moviePage.text()
                soup = BeautifulSoup(movie, 'html.parser')
                bigImg = soup.find('a', class_='bigImage')
                imgHref = 'https:' + bigImg.attrs['href']
            except Exception as e:
                reStartNum += 1
                if reStartNum > Const.MAX_FAIL_NUM:
                    if isinstance(e, connTimeoutError) or isinstance(e, ClientConnectorError)\
                            or isinstance(e, ServerDisconnectedError):
                        return None
                    else:
                        msg = f'爬取[{movieInfo["番号"]}]{section}时,出现[{str(e)}]错误!'
                        logger.error(msg)
                        raise e
                else:
                    return await saveBigImg(session, movieInfo, config, moviePath, reStartNum)
            if tmpImgHref == imgHref:
                continue
            try:
                async with session.get(imgHref, timeout=Const.TIMEOUT) as img:
                    imgFile = await img.read()
                    with open(imgPath, "wb")as f:
                        f.write(imgFile)
                config.add_config(section, '状态', '成功')
                config.add_config(section, '进度', '已完成')
                config.add_config(section, imgName, imgHref)
                logger.info(f'[{movieInfo["番号"]}]{section}已经成功爬取!')
                return True
            except Exception as e:
                tmpImgHref = imgHref
                if isinstance(e, connTimeoutError) or isinstance(e, ClientConnectorError)\
                        or isinstance(e, ServerDisconnectedError):
                    continue
                else:
                    msg = f'爬取[{movieInfo["番号"]}]{section}时,出现[{str(e)}]错误!'
                    logger.error(msg)
                    raise e
        reStartNum += 1
        if not reStartNum > Const.MAX_FAIL_NUM:
            return await saveBigImg(session, movieInfo, config, moviePath, reStartNum)
    config.add_config(section, '状态', '失败')
    config.add_config(section, '进度', '已完成')
    config.add_config(section, imgName, imgHref)
    logger.warning(f'[{movieInfo["番号"]}]{section}已经失败爬取!')
    return False


async def saveSampleImg(session, movieInfo, config, moviePath, reStartNum=1):
    section = '图片信息'
    if config.get_config(section, '状态') == '成功':
        # logger.info(f'[{movieInfo["番号"]}]{section}已被成功爬取!')
        return True
    else:
        for lang in Const.LANGUAGE_LIST:
            url = movieInfo['地址'] + lang
            try:
                async with session.get(url, timeout=Const.TIMEOUT) as moviePage:
                    movie = await moviePage.text()
                soup = BeautifulSoup(movie, 'html.parser')
                samImgList = soup.find_all('a', class_='sample-box')
                totalCount = len(samImgList)
            except Exception as e:
                reStartNum += 1
                if reStartNum > Const.MAX_FAIL_NUM:
                    if isinstance(e, connTimeoutError) or isinstance(e, ClientConnectorError)\
                            or isinstance(e, ServerDisconnectedError):
                        return None
                    else:
                        msg = f'爬取[{movieInfo["番号"]}]{section}时,出现[{str(e)}]错误!'
                        logger.error(msg)
                        raise e
                else:
                    return await saveSampleImg(session, movieInfo, config, moviePath, reStartNum)
            imgInfoList = []
            for i, imgTag in enumerate(samImgList):
                imgName = movieInfo['番号'] + '[' + "%03d" % i + '].jpg'
                imgPath = os.path.join(moviePath, imgName)
                imgHref = 'https:' + imgTag.attrs['href']
                try:
                    async with session.get(imgHref, timeout=Const.TIMEOUT) as img:
                        imgFile = await img.read()
                        with open(imgPath, "wb")as f:
                            f.write(imgFile)
                        imgInfoList.append([imgName, imgHref])
                except Exception as e:
                    if isinstance(e, connTimeoutError) or isinstance(e, ClientConnectorError)\
                            or isinstance(e, ServerDisconnectedError):
                        break
                    else:
                        msg = f'爬取[{movieInfo["番号"]}]{section}时,出现[{str(e)}]错误!'
                        logger.error(msg)
                        raise e
            if len(imgInfoList) == totalCount:
                config.add_config(section, '状态', '成功')
                config.add_config(section, '进度', '已完成')
                config.add_config(section, '数量', str(totalCount))
                for i in imgInfoList:
                    config.add_config(section, i[0], i[1])
                logger.info(f'[{movieInfo["番号"]}]{section}已经成功爬取!')
                return True
        reStartNum += 1
        if not reStartNum > Const.MAX_FAIL_NUM:
            return await saveSampleImg(session, movieInfo, config, moviePath, reStartNum)
        config.add_config(section, '状态', '失败')
        config.add_config(section, '进度', '已完成')
        config.add_config(section, '数量', str(0))
        logger.warning(f'[{movieInfo["番号"]}]{section}已经失败爬取!')
        return False


async def saveDownload(session, movieInfo, config, reStartNum=1):
    section = '下载信息'
    if config.get_config(section, '状态') == '成功':
        # logger.info(f'[{movieInfo["番号"]}]{section}已被成功爬取!')
        return True
    else:
        status = False
        prefix = "        $.get('/magnet/"
        suffix = ".html',{},function (ret) {"
        try:
            async with session.get(movieInfo['地址'], timeout=Const.TIMEOUT) as moviePage:
                movie = await moviePage.text()
        except Exception as e:
            reStartNum += 1
            if reStartNum > Const.MAX_FAIL_NUM:
                if isinstance(e, connTimeoutError) or isinstance(e, ClientConnectorError)\
                        or isinstance(e, ServerDisconnectedError):
                    return None
                else:
                    msg = f'爬取[{movieInfo["番号"]}]{section}时,出现[{str(e)}]错误!'
                    logger.error(msg)
                    raise e
            else:
                return await saveDownload(session, movieInfo, config, reStartNum)
        soup = BeautifulSoup(movie, 'html.parser')
        scriptList = soup.find_all('script')
        interfaceUrl = None
        for s in scriptList:
            script = str(s)
            if '/magnet/' in script:
                interfaceUrl = script.split('\n')[2]
                interfaceUrl = interfaceUrl.replace(prefix, '').replace(suffix, '')
                break
        if 'index.php' not in interfaceUrl:
            interfaceNum = int(interfaceUrl)
            interfaceUrl = f"{Const.HOME}/magnet/{str(interfaceNum)}.html"
        else:
            interfaceNum = int(interfaceUrl.replace("        $.get('/index.php/magnet/", ""))
            interfaceUrl = f"{Const.HOME}index.php/magnet/{str(interfaceNum)}.html"
        try:
            async with session.get(interfaceUrl, timeout=Const.TIMEOUT) as interface:
                inter = await interface.text()
        except Exception as e:
            reStartNum += 1
            if reStartNum > Const.MAX_FAIL_NUM:
                if isinstance(e, connTimeoutError) or isinstance(e, ClientConnectorError)\
                        or isinstance(e, ServerDisconnectedError):
                    return None
                else:
                    msg = f'爬取[{movieInfo["番号"]}]{section}时,出现[{str(e)}]错误!'
                    logger.error(msg)
                    raise e
            else:
                return await saveDownload(session, movieInfo, config, reStartNum)
        num = 0
        downSize = None
        inter = inter.replace('\\"', '"')
        inter = inter.replace('&lt;', '<')
        inter = inter.replace('&gt;', '>')
        inter = inter.replace('\\/', '/')
        soup = BeautifulSoup(inter, 'html.parser')
        downList = soup.find_all('td', style='text-align:center;white-space:nowrap')
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
                    config.add_config(section, option, value)
                    status = True
        if status:
            config.add_config(section, '状态', '成功')
            logger.info(f'[{movieInfo["番号"]}]{section}已经成功爬取!')
        else:
            noneDown = '"<script type=\\"text\\/javascript\\">$('
            noneDown += "'#movie-loading').hide();<\\/script>\\r\\n"
            noneDown += '"'
            noneDown = noneDown.replace('\\"', '"')
            noneDown = noneDown.replace('&lt;', '<')
            noneDown = noneDown.replace('&gt;', '>')
            noneDown = noneDown.replace('\\/', '/')

            if inter == noneDown:
                config.add_config(section, '状态', '成功')
                logger.info(f'[{movieInfo["番号"]}]{section}已经成功爬取!')
                status = True
            else:
                noneDown = noneDown.replace('"<', '<')
                noneDown = noneDown.replace('>\\r\\n"', '>\r\n')
                if inter == noneDown:
                    config.add_config(section, '状态', '成功')
                    logger.info(f'[{movieInfo["番号"]}]{section}已经成功爬取!')
                    status = True
                else:
                    config.add_config(section, '状态', '失败')
                    logger.warning(f'[{movieInfo["番号"]}]{section}已经失败爬取!')
    return status


def main():
    while True:
        while True:
            payTime = asyncMain(150, True)
            logger.info('统计正在执行中......')
            failCount = getStatus(payTime)
            if failCount == 0:
                logger.info('所有数据执行完成!')
                break
            else:
                maxCountDown = 60
                # repairMain()
                for countDown in range(0, maxCountDown + 1):
                    logger.error(f'共有{failCount}条未完成,执行倒计时中{countDown}/{maxCountDown}......')
                    time.sleep(60)

        maxCountDown2 = 1440
        for countDown2 in range(0, maxCountDown2 + 1):
            logger.info(f'等待电影数据刷新,执行倒计时中{countDown2}/{maxCountDown2}......')
            time.sleep(60)


if __name__ == '__main__':
    main()
