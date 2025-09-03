from selenium import webdriver
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import re

usr=input('Enter Email Id:') 
pwd=input('Enter Password:') 

driver = webdriver.Chrome()
wait = WebDriverWait(driver, 20)

#open the webpage
driver.get('https://highschoolsports.nj.com/girlsswimming/standings')
print ("opened nj.com login")
sleep(1)

#click sign in dropdown
dropdown = driver.find_element(By.XPATH, "//button[contains(@aria-label,'Sign In')]")
dropdown.click()
print ("clicked Sign in dropdown")
sleep(1)

#wait for dropdown to open
#wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'dropdown')][@aria-hidden='false']")))

#click sign in in dropdown
signin = driver.find_element(By.XPATH, "//ul[contains(@class,'usermenu')]/li//a[normalize-space()='Sign in' or normalize-space()='Sign In']")
signin.click()
print ("clicked Sign in")
sleep(1)

#manually signin and wait
input('Login manually and navigate to standings then press Enter here to continue:')
sleep(1)


#click other szns dropdown
szndropdown = driver.find_element(By.ID, "scheduleYearMenuList")
szndropdown.click()
print ("clicked other szns dropdown")
sleep(1)

#select correct szn
sznbutton = driver.find_element(By.LINK_TEXT, "2024-2025")
sznbutton.click()
print ("clicked correct szn")
sleep(1)

#select correct division
division = driver.find_element(By.LINK_TEXT, "CVC")
division.click()
print ("clicked division")
sleep(1)

#select team
team = driver.find_element(By.LINK_TEXT, "West Windsor-Plainsboro South")
team.click()
print ("clicked team")
sleep(1)


#select roster button
roster = driver.find_element(By.LINK_TEXT, "Roster")
roster.click()
print ("clicked roster")
sleep(1)

#collect all roster names + links
elmts = driver.find_elements(
    By.XPATH,
    "//table[contains(@class,'table-stats')]//tbody//tr"
    "/td[contains(@class,'text-left')][1]/a[contains(@href,'/player/')]"
)
names = [e.text.strip() for e in elmts]
links = [urljoin(driver.current_url, e.get_attribute("href")) for e in elmts]
nameandlink = zip(names, links)

#output names + links
for name, link in nameandlink:
    print(f"{name}: {link}")

#gather data for one swimmer
driver.get(links[0])
input("Press Enter to continue to scrape data for " + names[0])
print ("opened swimmer page")
events = driver.find_elements(
    By.XPATH,
    "//div[contains(@class,'card')][.//strong[contains(@class,'card-section-title')]]"
)
data = []
for event in events: ## interates through each event card
    title_el = event.find_element(By.CSS_SELECTOR, "strong.card-section-title")
    event_label = title_el.text.strip()
    event_name = re.sub(r'^\s*\d{4}\s*[–—-]\s*\d{4}\s*', '', event_label).strip()
    rows = event.find_elements(By.CSS_SELECTOR, "div.card-body div.mb-3")
    times = []
    for row in rows: ## iterates through each row in the event card
        lines = [ln.strip() for ln in row.text.splitlines() if ln.strip()]
        if not lines:
            continue
        perf_line = lines[-1]

        if "," in perf_line:
            time_txt, place_txt = perf_line.split(",", 1)
            time_txt = time_txt.strip()
            place_txt = place_txt.strip()
        else:
            time_txt, place_txt = perf_line.strip(), ""
        
        location_txt = lines[-2] if len(lines) >= 2 else ""
        
        times.append({"location": location_txt, "time": time_txt})

    if times != []:
        data.append({'event': event_name, 'times': times})

print(data)
    









# username_box = driver.find_element(By.ID, 'username-label')
# username_box.send_keys(usr)
# print ("Email Id entered")
# sleep(1)

# password_box = driver.find_element(By.ID, 'password-label')
# password_box.send_keys(pwd)
# print ("Password entered")
# sleep(1)





# login_box = driver.find_element(By.ID, "ulp-container-form-content-end")
# login_box.click()
# print ("Clicked login")


""" 
# username_box = driver.find_element(By.ID, 'email')
# username_box.send_keys(usr)
# print (&quot;Email Id entered&quot;)
# sleep(1)
 """
# password_box = driver.find_element(By.ID, 'pass')
# password_box.send_keys(pwd)
# print (&quot;Password entered&quot;)

# login_box = driver.find_element(By.ID, 'loginbutton')
# login_box.click()

# print (&quot;Done&quot;)
# input('Press anything to quit')
# driver.quit()
# print(&quot;Finished&quot;)