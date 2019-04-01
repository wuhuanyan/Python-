import os
from config import Const, Config, logger
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
        if samImgStatus != '成功':
            print(m)
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
    # send_email(content)
    return totalCount - allCount