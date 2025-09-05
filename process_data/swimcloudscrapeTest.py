from selenium import webdriver
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys



driver = webdriver.Chrome()

def open_and_search(driver, query, enter=False):### opens swimcloud and searches for query
    driver.get('https://www.swimcloud.com/')
    sleep(1)

    searchbar = driver.find_element(By.ID, "global-search-select")
    searchbar.click()
    searchbar.send_keys(query)
    if enter:
        searchbar.send_keys(Keys.ENTER)
    sleep(1)

def getallprofiles (driver, query):### gets the immediate search result lists of profiles (eg. Helen Chen WWP South)
    open_and_search(driver, query, enter=False)
    results = driver.find_elements(By.CSS_SELECTOR, '[role="option"]')
    texts = [r.text for r in results] 
    return texts



name = 'Emma Liu'

profs = getallprofiles(driver, name)

for p in profs:
    p.replace('\n', ' ')
    if name in p:
        open_and_search(driver, p, enter=True)
        ## TODO --- examine age and years of times. ( suggest make this another function)












