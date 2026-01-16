from selenium import webdriver
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import re

def scrapeprofile(driver): ## return scraped data from a page
    hmpgurl = driver.current_url
    driver.get(hmpgurl + 'times/')
    sleep(2)  # Increased sleep time
    
    rows = driver.find_elements(By.CSS_SELECTOR, '#js-swimmer-profile-times-container tbody tr')
    
    if len(rows) == 0:
        print("ERROR: No rows found! The page might not have loaded or selector is wrong.")
        print(f"Current URL: {driver.current_url}")
        return ## might need to check what we're returning here
    
    for i, row in enumerate(rows):
        print(f"\n--- Processing row {i+1} ---")
        
        # Get all cells in the row
        all_cells = row.find_elements(By.CSS_SELECTOR, "td")
        
        try:
            ## get date - cell 4 (5th cell, index 4)
            if len(all_cells) > 4:
                dt = all_cells[4].text
                print(f"Date: {dt}")
                #yr = dt.split(', ')[1].strip()
            else:
                print("Not enough cells for date")
        except Exception as ex:
            print(f"Error getting date: {ex}")
        
        try:
            ###### get event - cell 0 (first cell, index 0)
            if len(all_cells) > 0:
                event_text = all_cells[0].text
                print(f"Event: {event_text}")
                #events = event_text.split(' ')
                #event = [' '.join(events[:2]), events[2]]
            else:
                print("No cells found for event")
        except Exception as ex:
            print(f"Error getting event: {ex}")
        
        try:
            #### get time - cell 1 (second cell, index 1)
            if len(all_cells) > 1:
                time_text = all_cells[1].text
                print(f"Time: {time_text}")
            else:
                print("Not enough cells for time")
        except Exception as ex:
            print(f"Error getting time: {ex}")


    ####TODO-- clean this code up- (like less printing) and process all elements is a good step 1
    ##### then maybe figure out which events to consider and when times are considered expired

        #print(yr, event, time)
        
        #if validyrs(yr) and event[0] in HSEVENTS:
            ## scrape the row
        #else:
            ## click and check history (maybe a diff function for this)

    # todo -- scrape needed data from this url


######## test

driver = webdriver.Chrome()
driver.get('https://www.swimcloud.com/swimmer/2643240/')
scrapeprofile(driver)