from swimcloudscrapeUtils import checktimeshistory
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import datetime

driver = webdriver.Chrome()

time = checktimeshistory(driver, 'https://www.swimcloud.com/swimmer/2902858/times/')
print (time)