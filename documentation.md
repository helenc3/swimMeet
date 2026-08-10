src

```
- common/ : contains globally useful util functions/statics
    - mongodb/ : contains globally useful utils for mongodb
        - connect.py : contains functions for connecting
        - queries1.py : useful queries for working with the older collection, COLLECTION_NAME
        - queries2.py : useful queries for working with the newer collection,
        OFFICIAL_COLLECTION_NAME
    - conversions.json : a file with the scraped conversions
    - utils.py : a bunch of globally useful statics/methods including data directtory path and collection names, parse time to seconds, etc
    
- scraper/ : contains all scripts related to scraping
        -njcom/ : contains all scrape scripts pertaining to nj.com
			- updates/ : all scripts which update new data (require existing data)
			   - errorevents/ : folder for error csv files that get reviewed. 
	            - fixerrors.py : file for pushing fixxed error csvs to mongoDB, ONLY RUN AFTER YOU CHECK THROUGH ALL ERROREVENTS FILES 
	            - utils.py : utils functions for scraping
	            - main.py : main script for scraping -- run for updated data
			
			- ogdata/ : all og scripts 
				  -main.py
				  -utils.py
           
        - swimcloud/ : contains all update scripts pertaining to swimcloud
	          -scutils.py : globally useful swimcloud scraping functions
	          - updates/ : used to gather new data
		            -main.py
	        
		      - ogdata/ : used to gather intial data
			        - main.py
    

- data/ : contains backup datafile

- archive/ : contains a bunch of one time run scripts to fix little errors. might be useful for emergency fixes...
    - jsontodb.py : used to write the backup data files in njcom to mngodb
    - rvillefix.py : used to fix the scm/scy problem with all rville meets
    - scrape_conversions.py : used to scrape+calculate the conversion constants from an online site
    - nulltimes.py : used to find the swimmers with a lot of null times in the OFFICAL_COLLECTION_NAME
    - transfer_scripts/ : scripts used for the original migration between old and new collections (COLLECTION_NAME -> OFFICIAL COLLECTION NAME)
        - official.py : merges old docs from old collection and puts them in new collection
        - sc_adder/ : all scripts that add swimcloudurl fields to new docs.
            - addsc.py : adds swim clouds from old collection to new collection profiles
            - nosc.json : kinda garbage file, contains all swimmers (out of date) with no swimcloud profile
            - missingswimclouds.json : manually created file for swimmers with swimclouds that aren't automatically searchable
            - errors.json : a dump of all the swimmers which failed to find/add swimcloud url for
    -outlier_handler/ : for the old collection-- detects and handles times that are improbable. note this has no main file for some reason i think i mightve deleted the scripts and im too lazy to search for it. make your own if you wanna use it. 
        - utils.py : utility functions for improbable time detection
        - impossibletimes.json : a list of times that are improbable (doesnt mean impossible)
    - course_handler : for the old olddd collection, handles meet location names "eg teamA vs teamB 6/7/2067" to "SCM" (also no main file)
        - utils.py: utility functions for the task
        - teamcourses.json : from my knowledge the courses for each home team
        - swimmer_teams.txt : list of home pools each swimmer has been to
        - locationerrors.txt : just a notes txt file so i can internally keep track of the manual errors i had to fix
        - uniqueteams.txt : a list of unique teams found across all swimmer docs
        

- predict_times: used to fill in missing times w llm generated predictions
	- main.py : main file to predict all times
	- utils.py : utility functions
	- system_prompt.txt :system prompt
	  ```
	  
- lineup/ : a work in progress ...


pipeline to run : (last scrapeday : 2/6/2026 )

cd /Users/HChen/workspace/swimMeet/src
python -m scraper.swimcloud.updates.main
python -m scraper.njcom.updates.main
python -m scraper.njcom.updates.fixerrors (if errorevents/ isnt empty and is fixed)
python -m predict_times.main 