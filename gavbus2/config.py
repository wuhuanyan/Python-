import os
import logging
import configparser
import colorlog  # 控制台日志输入颜色
from logging.handlers import RotatingFileHandler  # 按文件大小滚动备份

log_colors_config = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red',
}


class Config:
    """
    配置文件类
    """
    def __init__(self, filename='./config.ini'):
        """
        载入配置文件
        :param filename: 配置文件名称
        """
        self.config = configparser.ConfigParser()
        self.filename = filename
        if os.path.exists('{}'.format(filename)):
            self.config.read(filename)
            # logger.info('配置信息载入成功')
        else:
            f = open(filename, "w")
            f.close()
            self.config.read(filename)
            # logger.info('配置信息载入失败,自动创建配置信息文件!')

    def print_config(self, section, option):
        """
        打印配置文件信息
        :return:
        """
        if section is not None and option is not None:
            print(self.config[section][option])
        elif section is not None and option is None:
            for i in self.config[section]:
                print(self.config[section][i])
        elif section is None and option is None:
            for i in self.config:
                print('[{}]'.format(i))
                for j in self.config[i]:
                    print("    [{}] = '{}'".format(j, self.config[i][j]))
                print()

    def modify_config(self, section, option, value):
        """
        修改配置属性
        :param section:section名称
        :param option:option名称
        :param value:value值
        :return:是否修改成功
        """
        if self.config.has_option(section, option):
            self.config.set(section, option, value)
            logger.info(f'配置信息修改成功![{section}]:{option}:{value}')
            return True
        else:
            logger.info(f'配置信息修改失败![{section}]:{option}:{value},没有该配置项!')
            return False

    def add_config(self, section, option, value):
        """
        增加配置属性
        :param section:section名称
        :param option:option名称
        :param value:value值
        :return:是否增加成功
        """
        if self.config.has_section(section):
            self.config.set(section, option, value)
        else:
            self.config.add_section(section)
            self.config.set(section, option, value)
        with open('{}'.format(self.filename), 'w') as f:
            self.config.write(f)
        # logger.info(f'配置信息增加成功![{section}]:{option}:{value}')
        return True

    def delete_config(self, section, option):
        """
        删除配置项
        :param section: section
        :param option: option
        :return: 是否成功删除
        """
        if self.config.has_option(section, option):
            self.config.remove_option(section, option)
            with open('{}'.format(self.filename), 'w') as f:
                self.config.write(f)
            logger.info(f'配置信息删除成功![{section}]:{option}')
        else:
            pass
            logger.info(f'配置信息删除失败，"{self.filename}"下无[{section}]-[{option}]配置项，请检查！')
        return True

    def delete_section(self, section):
        if self.config.has_section(section):
            self.config.remove_section(section)
            with open('{}'.format(self.filename), 'w') as f:
                self.config.write(f)
            logger.info(f'配置信息删除成功![{section}]')
        else:
            pass
            logger.info(f'配置信息删除失败，"{self.filename}"下无[{section}]配置项，请检查！')
        return True

    def get_config(self, section, option):
        """
        获取配置属性值
        :param section:section名称
        :param option: option名称
        :return: value值
        """
        if self.config.has_section(section) and self.config.has_option(section, option):
            return self.config.get(section, option)
        else:
            return ''


basePath, filename1 = os.path.split(os.path.abspath(__file__))


class Const(object):
    """
    常量类
    主要是一些文件目录和文件的定义,在这里可以统一修改.
    测试了一下网上的常量类,发现修改不成功,所以暂时先这样定义啦.
    """
    LOG_FILE = os.path.join(basePath, './log.log')  # 日志文件的路径
    MOVIE_PATH = os.path.join(basePath, 'movie')
    PAGE_WEB_PATH = os.path.join(basePath, 'pageWebFiles')
    MOVIE_WEB_PATH = os.path.join(basePath, 'movieWebFiles')
    LANGUAGE_LIST = ['', '?lang=en', '?lang=ja', '?lang=ko', '?lang=cn']
    HOME = 'https://www.不能说的秘密.com/'  # 网站首页
    FROM_EMAIL_ADDR = 'qq20071115@126.com'  # 发送邮件的邮箱账号
    FROM_EMAIL_SMTP = 'smtp.126.com'  # SMTP服务器地址
    FROM_EMAIL_PASSWD = '不能说的秘密'  # 发送邮件的邮箱密码
    MAX_FAIL_NUM = 5  # 最大失败次数
    TIMEOUT = 30  # 超时时间

    @classmethod
    def getLogFilePath(cls):
        """
        获取配置的日志文件位置
        :return:
        """
        return cls.LOG_FILE


def get_logger():
    log_format = colorlog.ColoredFormatter(
        '%(log_color)s[%(asctime)s] %(levelname)s: %(message)s'.format(log_colors=log_colors_config))

    log = logging.getLogger()

    log_file = RotatingFileHandler(filename=Const.getLogFilePath(), mode='a')
    log_file.setFormatter(log_format)
    log.addHandler(log_file)

    log_cmd = colorlog.StreamHandler()
    log_cmd.setFormatter(log_format)
    log.addHandler(log_cmd)

    log.setLevel(logging.INFO)
    return log


logger = get_logger()
