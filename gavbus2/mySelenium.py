from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time


def wait_for_load(driver, timeout=10):
    # 处理重定向，可以定时检查页面的某元素
    # 如果和先前的不一致则可认为客户端重定向
    # elem = driver.find_element_by_tag_name("html")
    title = driver.find_element_by_tag_name("title")
    count = 0
    while True:
        count += 1
        if count > timeout:
            # print("Timing out after 10 seconds and returning")
            return
        time.sleep(.5)
        newtitle = driver.find_element_by_tag_name("title")
        if newtitle != title:
            return
        # try:
        #    elem = driver.find_element_by_tag_name("html")
        # except StaleElementReferenceException:
        #    return


def getDriver():
    # myDriver = webdriver.PhantomJS(executable_path='./phantomjs/bin/phantomjs')
    chrome_options = webdriver.ChromeOptions()  # 创建chrome参数对象
    chrome_options.add_argument('--headless')  # 把chrome设置成无界面模式，不论windows还是linux都可以，自动适配对应参数
    capa = DesiredCapabilities.CHROME
    capa["pageLoadStrategy"] = "none"
    myDriver = webdriver.Chrome(options=chrome_options, desired_capabilities=capa)  # 创建chrome无界面对象
    myDriver.set_page_load_timeout(10)  # 超时时间
    myDriver.set_script_timeout(10)
    return myDriver


def getContent(driver, url):
    try:
        wait = WebDriverWait(driver, 10)
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="magnet-table"]/tbody/tr[2]/td[2]/a')))
        wait_for_load(driver)
    except Exception as e:
        str(e)
        driver.execute_script("window.stop();")
    return driver.page_source
