import os
from config import Config, Const
from model import Movie
from concurrent.futures import ThreadPoolExecutor
from functools import partial


def start():
    topPath = Const.MOVIE_PATH
    for i1, j1, k1 in os.walk(topPath):
        if i1 != topPath:
            continue
        for j2 in j1:
            print(j2)
            unitNum = j2
            moviePath = os.path.join(i1, unitNum)
            iniPath = os.path.join(moviePath, f'{unitNum}.ini')
            config = Config(iniPath)
            movieInfo = dict()
            movieInfo['地址'] = config.get_config('基本信息', '地址')
            movieInfo['番号'] = config.get_config('基本信息', '番号')
            movieInfo['标题'] = config.get_config('基本信息', '标题')

            # 修复下载信息
            cStatus = config.get_config('下载信息', '状态')
            if cStatus == '失败':
                config.add_config('下载信息', '进度', '未完成')
                m = Movie(movieInfo)
                m.saveDownLoad()

            # 修复海报信息
            config = Config(iniPath)
            cStatus = config.get_config('海报信息', '状态')
            if cStatus == '失败':
                config.add_config('海报信息', '进度', '未完成')
                config.add_config('图片信息', '进度', '未完成')
                baseUrl = movieInfo['地址'][:-8] if '?lang=' in movieInfo['地址'] else movieInfo['地址']
                for lang in Const.LANGUAGE_LIST:
                    movieInfo['地址'] = f'{baseUrl}{lang}'
                    m = Movie(movieInfo)
                    m.saveBaseInfo()
                    if m.saveBigImg():
                        m.saveSampleImg()
                        break
                    else:
                        config.add_config('海报信息', '进度', '未完成')
                        config.add_config('图片信息', '进度', '未完成')

            # 修复图片信息
            config = Config(iniPath)
            cStatus = config.get_config('图片信息', '状态')
            if cStatus == '失败':
                cStatus = config.get_config('海报信息', '状态')
                if cStatus == '失败':
                    continue
                config.add_config('图片信息', '进度', '未完成')
                baseUrl = movieInfo['地址'][:-8] if '?lang=' in movieInfo['地址'] else movieInfo['地址']
                for lang in Const.LANGUAGE_LIST:
                    movieInfo['地址'] = f'{baseUrl}{lang}'
                    m = Movie(movieInfo)
                    m.saveBaseInfo()
                    if m.saveSampleImg():
                        break
                    else:
                        config.add_config('图片信息', '进度', '未完成')


def repair(unitNum):
    topPath = Const.MOVIE_PATH
    moviePath = os.path.join(topPath, unitNum)
    iniPath = os.path.join(moviePath, f'{unitNum}.ini')
    config = Config(iniPath)
    movieInfo = dict()
    movieInfo['地址'] = config.get_config('基本信息', '地址')
    movieInfo['番号'] = config.get_config('基本信息', '番号')
    movieInfo['标题'] = config.get_config('基本信息', '标题')
    # 修复下载信息
    try:
        cStatus = config.get_config('下载信息', '状态')
        if cStatus == '失败':
            config.add_config('下载信息', '进度', '未完成')
            m = Movie(movieInfo)
            m.saveDownLoad()
            # 修复海报信息
            config = Config(iniPath)
            cStatus = config.get_config('海报信息', '状态')
            if cStatus == '失败':
                config.add_config('海报信息', '进度', '未完成')
                config.add_config('图片信息', '进度', '未完成')
                baseUrl = movieInfo['地址'][:-8] if '?lang=' in movieInfo['地址'] else movieInfo['地址']
                for lang in Const.LANGUAGE_LIST:
                    movieInfo['地址'] = f'{baseUrl}{lang}'
                    m = Movie(movieInfo)
                    m.saveBaseInfo()
                    if m.saveBigImg():
                        m.saveSampleImg()
                        break
                    else:
                        config.add_config('海报信息', '进度', '未完成')
                        config.add_config('图片信息', '进度', '未完成')
            # 修复图片信息
            config = Config(iniPath)
            cStatus = config.get_config('图片信息', '状态')
            if cStatus == '失败':
                cStatus = config.get_config('海报信息', '状态')
                if cStatus == '失败':
                    return
                config.add_config('图片信息', '进度', '未完成')
                baseUrl = movieInfo['地址'][:-8] if '?lang=' in movieInfo['地址'] else movieInfo['地址']
                for lang in Const.LANGUAGE_LIST:
                    movieInfo['地址'] = f'{baseUrl}{lang}'
                    m = Movie(movieInfo)
                    m.saveBaseInfo()
                    if m.saveSampleImg():
                        break
                    else:
                        config.add_config('图片信息', '进度', '未完成')
    except Exception as e:
        print(str(e))
        return


def filterFinsh(finshList, unitNum):
    if unitNum not in finshList:
        return True
    else:
        return False


def getFinsh(unitNum):
    if unitNum == 'EQ-440':
        pass
    topPath = Const.MOVIE_PATH
    moviePath = os.path.join(topPath, unitNum)
    iniPath = os.path.join(moviePath, f'{unitNum}.ini')
    finshPath = os.path.join(topPath, 'finsh.ini')
    config = Config(iniPath)
    bigImgStatus = config.get_config('海报信息', '状态')
    samImgStatus = config.get_config('图片信息', '状态')
    downloadStatus = config.get_config('下载信息', '状态')
    if bigImgStatus == '成功' and samImgStatus == '成功' and downloadStatus == '成功':
        finshConfig = Config(finshPath)
        finshConfig.add_config('成功列表', unitNum, unitNum)
        print(f'{unitNum}已添加到成功列表!')


def main():
    topPath = Const.MOVIE_PATH
    movieList = None
    for i, j, k in os.walk(topPath):
        if i == topPath:
            movieList = j
            break
        else:
            continue
    finshPath = os.path.join(topPath, 'finsh.ini')
    finshConfig = Config(finshPath)
    finshList = [i[1] for i in finshConfig.config.items('成功列表')]
    unFinshList = list(filter(partial(filterFinsh, finshList), movieList))
    print(len(unFinshList))
    for m in unFinshList:
        getFinsh(m)
    try:
        with ThreadPoolExecutor(max_workers=60) as executor:
            executor.map(repair, unFinshList)
    except Exception as e:
        raise e
    finally:
        print('本次成功列表:')
        for m in unFinshList:
            getFinsh(m)


if __name__ == '__main__':
    main()
