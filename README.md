

# PA Department of Health Facility Survey Scraper

## Overview

This Python application automates the scraping of health facility survey data from the Pennsylvania Department of Health website. Designed to navigate through a list of URLs dynamically, it extracts and processes survey details for various facilities. The program filters the surveys based on specified years, and organizes the data in a structured JSON format, making it easily accessible for further analysis or archival purposes.

## Key Features

* Dynamic URL Processing: Parses a provided list of URLs to extract survey data for each health facility.
* Customizable Data Extraction: Fetches important details such as facility names, event IDs, dates, and specific survey information.
* Yearly Filter: Includes functionality to filter the surveys by specific years, with default settings for 2023 and 2024.
* JSON Data Storage: Structures the scraped data into JSON format, saving each facility's survey information in a separate file to ensure data integrity and ease of access.
* Filename Collision Handling: Implements a system to avoid overwriting existing files by appending a counter to filenames in case of duplicates.
* Efficient Deduplication: Utilizes sets to remove duplicate URLs before processing to ensure efficiency.

# Packages Required: 
1. requests
2. beautifulsoup4

* tqdm (for progress tracking, so technically not require, but very helpful if you want to know where the application is while running as it can take a while scraping pages)****

Configuration
You can customize the list of URLs and the years for which you want to scrape the surveys by editing the main() function in the script. The headers and cookies dictionaries may also be adjusted according to the requirements or changes in the target website's request handling.

Output
The program saves the scraped data in the ./json directory, creating one JSON file per facility. The filenames are generated based on the facility name, with safeguards against overwriting existing data.

https://github.com/e-supple/PA-Department-of-Health-Survey-Scraper

# Methods: 

## get_links()
### The get_links method fetches and parses a web page to extract specific links. It requests the content of the provided URL, then filters table rows based on certain criteria, including a check for a particular character in one of the table cells. Finally, it extracts and returns the href attributes of anchor tags within the first two cells of these filtered rows.

### filtered_rows = [row for row in rows if len(row.findAll('td')) >= 4 and contains_adm(row.findAll('td')[3].text)]

### terating Through the Table: The process begins by iterating through each row of the table. These rows are represented by the row variable in the list comprehension.

### Ensuring Adequate Cells in Each Row: It checks that each row has at least 4 cells. This is to ensure that there's enough data in each row for further processing, and possibly to avoid errors when accessing a specific cell that may not exist in rows with fewer cells.

### Identifying Specific Survey Categories: The code looks for rows where the fourth cell (row.findAll('td')[3], since indexing is zero-based) contains text that matches specific survey categories, identified by the presence of certain characters ('a', 'd', '3', 'm'). This is achieved through the contains_adm function, which presumably checks for these characters within the cell's text.

### Building the Filtered List: Only rows that meet both criteria (having 4 or more cells and containing the specified survey category characters) are included in the filtered_rows list. This results in a filtered list of rows that are relevant to the specific analysis or processing task at hand, based on the survey categories of interest.



## save_json()
### Creates a JSON file in a designated directory to store extracted data. The filename is dynamically generated based on the facility name, sanitized to replace spaces and slashes with underscores and hyphens, respectively. If a file with the intended name already exists, a counter is appended to create a unique filename, preventing overwrites. The method saves the data in a readable JSON format and outputs the file's location.


## get_endpoints(links)
### Transforms a list of full URLs into relative endpoints by removing a specified base URI. This is useful for operations that require working with the path component of URLs, especially when the base part is consistent across all links.

## contains_ad3m(text)
### Evaluates if a given text string contains any of the characters 'a', 'd', '3', or 'm', irrespective of case. This could be used for filtering or identifying strings based on the presence of these specific characters.

## contains_m(text)
### Determines whether the character 'm' (case-insensitive) is present in the given text. This method can be useful for simple text filtering tasks based on the occurrence of 'm'.

## scrape_pages()
### navigates to a specified health facility page, extracts relevant survey data, and organizes it into a structured format. It begins by parsing the URL to retrieve the facility's unique identifier (Facid), then requests the page content. The function searches for a dropdown menu listing surveys and extracts the facility name from a specified font tag. For each survey option within the dropdown, it compiles details such as the event ID and survey date, requests the survey's specific page, and aggregates text data from tables that follow a certain index. Finally, it packages all collected data into a comprehensive dictionary structure, ready for further processing or saving. If the dropdown menu is missing, indicating a potential issue with the page or data accessibility, it returns a minimal structure with an empty data list.