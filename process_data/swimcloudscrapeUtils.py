from selenium import webdriver
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import re

HSEVENTS = ['50 Free', '100 Free', '200 Free', '500 Free', '400 Free', '100 Back', '100 Breast', '100 Fly', '200 IM']

def getYr(row): #returns string yr
    cells = row.find_elements(By.CSS_SELECTOR, "td.u-text-truncate")
    if not cells:
        return ""
    txt = cells[-1].text.strip()                 # e.g. "Jan 23, 2025"
    m = re.search(r"\b(19|20)\d{2}\b", txt)      # extract 4-digit year
    return m.group(0) if m else ""

def getEvent(row): #returns list [event, distance]
    e = row.find_element(By.CSS_SELECTOR, "td .btn-link")
    tokens = e.text.split()                      # ['50','Free','SCY']
    return [' '.join(tokens[:2]), tokens[2] if len(tokens) > 2 else ""]

def getTime(row): #returns time string
    return row.find_element(By.CSS_SELECTOR, "td.u-text-end").text.strip()

def validyrs(yr):
    year = int(yr)
    current_year = datetime.now().year
    if current_year - year <= 2:
        return True
    return False

def to_seconds(s: str) -> float:
    """Parse swim time strings like '27.88', '1:06.38', '2:01', '1:02:03.4' into seconds."""
    s = re.sub(r'[^0-9:.]', '', s.strip())      # keep only digits, colon, dot
    if not s:
        raise ValueError(f"Empty/invalid time: {s!r}")
    parts = s.split(':')                         # rightmost = seconds(.fraction)
    total = 0.0
    for i, part in enumerate(reversed(parts)):
        if part == '':
            part = '0'
        total += float(part) * (60 ** i)
    return total


def comparetimestrings(t1, t2): ## returns the faster time string
    if to_seconds(t1) < to_seconds(t2):
        return t1
    return t2
     



def checktimeshistory(driver, url): ## opens url and returns fastest time dictionary with valid yr
    ## if no valid time, return None
    driver.get(url)
    rows = driver.find_elements(By.XPATH, "//h3[normalize-space()='History']/following-sibling::div//table//tbody/tr[td[contains(@class,'u-text-end')]]")
    print (len(rows)) ###############something about getting the rows is wrong

    fasttime = '30:00.00'
    for row in rows:
        time_text = row.find_element(By.XPATH, ".//td[contains(@class,'u-text-end')]").text.strip()
        # date is the last truncate cell, e.g. "Dec 11, 2021"
        date_cells = row.find_elements(By.XPATH, ".//td[contains(@class,'u-text-truncate')]")
        date_text = date_cells[-1].text.strip() if date_cells else ""

        # extract 4-digit year
        m = re.search(r"\b(19|20)\d{2}\b", date_text)
        year = m.group(0) if m else ""

        if validyrs(year):
            fasttime = comparetimestrings(fasttime, time_text)
    if fasttime == '30:00.00':
        return None
    return fasttime

    

driver = webdriver.Chrome()
driver.get('https://www.swimcloud.com/swimmer/829178/times/')

rows = driver.find_elements(By.XPATH,
    "//div[@id='js-swimmer-profile-times-container']"
    "//tbody/tr[td//button[contains(@class,'btn-link')]]")


data = []
print (len(rows))
for row in rows:
    yr = getYr(row)
    event = getEvent(row)
    time = getTime(row)
    if validyrs(yr) and event[0] in HSEVENTS:
            data.append({"event": event[0], 'times': {"location": event[1], "time": time}})
            continue
    elif event[0] in HSEVENTS:
            
            ## click and check history (maybe a diff function for this)
            continue
    ## else click and check history (maybe a diff function for this)


    # TODO -- scrape needed data from this url