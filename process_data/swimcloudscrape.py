from selenium import webdriver
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import datetime

HSEVENTS = ['50 Free', '100 Free', '200 Free', '500 Free', '400 Free', '100 Back', '100 Breast', '100 Fly', '200 IM']

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

def validyrs(yr):
    year = int(yr)
    current_year = datetime.now().year
    if current_year - year <= 2:
        return True
    return False

def scrapeprofile(driver): ## return scraped data from a page
    hmpgurl = driver.current_url
    driver.get(hmpgurl + 'times/')
    sleep(1)
    rows = driver.find_elements(By.CSS_SELECTOR, '#js-swimmer-profile-times-container tbody tr')
    for row in rows:
        ## get year
        dt = row.find_elements(By.CSS_SELECTOR, "td.u-text-truncate") 
        yr = dt.text.split(', ')[1].strip()

        ###### get event
        e = row.find_element(By.CSS_SELECTOR, "td .btn-link")
        events = e.text.split(' ').strip()
        event = [' '.join(events[:2]), events[2]]

        #### get time

        if validyrs(yr) and event[0] in HSEVENTS:
            ## scrape the row
        else:
            ## click and check history (maybe a diff function for this)

    # TODO -- scrape needed data from this url



name = 'Emma Liu'
hsteam = 'West Windsor-Plainsboro South' ### theres a bit of discordance with how swimcloud lists teams
## for the wwps, might wanna get rid of south or north

profs = getallprofiles(driver, name)

urls = []
for p in profs:
    p.replace('\n', ' ')
    if name in p:
        open_and_search(driver, p, enter=True)
        lastmeetyr = driver.find_element(By.CSS_SELECTOR, 'u-color-mute u-text-small u-text-normal').text
        lastmeetyr = lastmeetyr.split(', ')[1]
        if validyrs(lastmeetyr):
            urls.append(driver.current_url)
            ### TODO -- scrape needed data from this url
        else:
            continue

        ## TODO --- examine age and years of times. ( suggest make this another function)












