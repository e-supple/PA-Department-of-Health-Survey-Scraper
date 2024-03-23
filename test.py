from datetime import datetime
import os
import json
import time
from urllib.parse import parse_qs, urlparse
import httpx
import asyncio
from bs4 import BeautifulSoup, NavigableString

def contains_adm(text):
    text_lower = text.lower()
    return any(char in text_lower for char in ['a', 'd', 'm', '3'])

def get_endpoints(links):
    uri = 'https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/'
    endpoints = [link.replace(uri, '') for link in links]
    return endpoints

def save_json(data):
    os.makedirs('./json', exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    facility_name = data['facility'].replace(' ', '_').replace('/', '-').replace('<br>', '')

    filename = f'{timestamp}_survey_{facility_name}'
    file_extension = '.json'
    file_path = f'./json/{filename}{file_extension}'
    counter = 0
    
    while os.path.exists(file_path):
        counter += 1
        file_path = f'./json/{filename}.{counter}{file_extension}'
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f' Data has been written to {file_path}.')

def filter_surveys_by_year(options, years=[2023, 2024]):
    filtered_options = []
    for option in options:
        date_text = option.text.strip()
        try:
            survey_date = datetime.strptime(date_text, "%m/%d/%Y")
            if survey_date.year in years:
                filtered_options.append(option)
                # DEBUG print(f"Filtered Dates: Complete {filtered_options}")
        except ValueError:
            # Handle date format does not match or parsing fails
            print(f"Error parsing date for option: {date_text}")
    return filtered_options

async def fetch_page(url: str, headers: dict = None, cookies: dict = None, params: dict= None):
    timeout = httpx.Timeout(10.0, read=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers, cookies=cookies)
        return response
    
async def fetch_page_1(url: str, headers: dict = None, cookies: dict= None, retries: int = 3, delay: float = 2.0):
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(cookies=cookies, timeout=httpx.Timeout(10.0, read=30.0)) as client:
                return await client.get(url=url, headers=headers, cookies=cookies)
        except httpx.ReadTimeout:
            print(f"Timeout encountered. Retrying ({attempt + 1}/{retries}) after {delay} seconds...")
            await asyncio.sleep(delay)
    print("Failed to fetch the page after retries. Handling failure...")

async def async_getlinks(url, headers, cookies= None, data= None):
    response = await fetch_page(url, headers=headers, cookies=cookies)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        content_container = soup.find('div', class_='content-container')
        table = content_container.find('table')
        rows = table.findAll('tr')
        filtered_rows = [row for row in rows if len(row.findAll('td')) >= 4 and contains_adm(row.findAll('td')[3].text)]
        urls = [cell.find('a')['href'] for row in filtered_rows for cell in row.find_all('td', limit=2) if cell.find('a')]
        return urls 
    else:
        print("Failed to fetch the webpage")

async def scrape_pages(link: str, headers: dict, cookies: dict= None, data: dict= None):
    base_url = "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/"
    parsed_url = urlparse(link)
    # Parse the query parameters from the URL
    query_params = parse_qs(parsed_url.query)
    
    # Extract the 'Facid' value
    facid = query_params.get('Facid', [None])[0]
    if not facid:
        print("Facid not found in the link.")
        return None
    
    initial_page_url = f"{base_url}{link}"
    response = await fetch_page(initial_page_url, headers, cookies)
    soup = BeautifulSoup(response.content, 'html.parser')
    select_element = soup.find('select', id='SurveyList')
    
    all_survey_data = {}
    survey_data = []
    
    facility_name_tag = soup.find('font', {'size': '+1'})
    facility_name = ''
    
    if facility_name_tag:
        for content in facility_name_tag.contents:
            if isinstance(content, NavigableString):
                facility_name = content.strip()
                break
            
    all_survey_data['facility'] = facility_name       
    
    if not select_element:
        print("Couldn't find the survey list dropdown.")
        return {'facility': '', 'data': []}
    
    if select_element:
        tasks = []
        options = select_element.find_all('option')
        options = filter_surveys_by_year(options)
        
        for option in options:
            eventid = option['value']
            survey_url = f"{base_url}ltc-survey.asp?facid={facid}&page=1&name=&SurveyType=H&eventid={eventid}"
            tasks.append(fetch_page(survey_url, headers=headers, cookies=cookies))
        
        responses = await asyncio.gather(*tasks)
        
        for response, option in zip(responses, options):
            eventid = option['value']
            date_txt = option.text.strip()
            survey_details = {'eventid': eventid, 'date': date_txt}
            
            if response is not None:
                soup = BeautifulSoup(response.content, 'html.parser')
                tables = soup.findAll('table')
            
            if len(tables) >= 5:
                data_tables = tables[5:-1]
                survey_details['data'] = ' '.join([table.text.strip() for table in data_tables])            
            survey_data.append(survey_details)
        all_survey_data['data'] = survey_data
        
        return all_survey_data  

async def main():
    daac_url = "https://apps.health.pa.gov/surveyspostedDAAC/DAAC-SurveysPosted_202402.aspx"
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Cookie': 'paGov=1; _ga_43SYEQBLV4=GS1.1.1701298993.1.1.1701299170.0.0.0; _ga_Y97KNG0WT3=GS1.1.1702655416.2.0.1702655416.0.0.0; _ga_EFBFYET3JS=GS1.1.1705532227.1.1.1705532239.0.0.0; visid_incap_2815744=xjCHti1DRE+C+DecvMgYa1NbqGUAAAAAQUIPAAAAAABnHMKnuYDw6XcK4WUnuxn1; _ga_5ETEHW2RE7=GS1.1.1705532245.1.0.1705532250.0.0.0; _ga_45SCT2E2LM=GS1.2.1710243958.6.0.1710243958.60.0.0; _ga_EVYRH4J3SP=GS1.1.1710697627.53.0.1710697627.0.0.0; visid_incap_2815840=dIL4Z5f4SA2OLlZEESUVbHiY+2UAAAAAQUIPAAAAAACa4Yx08pP2Dn9SnkPOs+Sv; _gcl_au=1.1.1914906969.1710987387; _ga=GA1.3.308807853.1701298993; _ga=GA1.4.308807853.1701298993; ASP.NET_SessionId=mdyats4fzai1yqbfph4iwb3j; _gid=GA1.2.821789585.1711105720; _ga_J4ZD36GZ4Z=GS1.2.1711105720.55.0.1711105720.60.0.0; _ga=GA1.1.308807853.1701298993; _ga_P7HXBG8L73=GS1.1.1711109996.57.0.1711109996.0.0.0; _ga_BB0F8LZZJ6=GS1.1.1711109996.2.0.1711109996.60.0.443245163; _gid=GA1.4.821789585.1711105720; _gat_UA-41550633-37=1; incap_ses_1340_2815840=qblKVFQBoyJOP6ZQ66OYEmt3/WUAAAAA9FOyfr457I8JGWJo7W5nQw==',
        'Host': 'apps.health.pa.gov',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }
    cookies = {
        '_ga_43SYEQBLV4': 'GS1.1.1701298993.1.1.1701299170.0.0.0',
        '_ga_Y97KNG0WT3': 'GS1.1.1702655416.2.0.1702655416.0.0.0',
        '_ga_EFBFYET3JS': 'GS1.1.1705532227.1.1.1705532239.0.0.0',
        'visid_incap_2815744': 'xjCHti1DRE+C+DecvMgYa1NbqGUAAAAAQUIPAAAAAABnHMKnuYDw6XcK4WUnuxn1',
        '_ga_5ETEHW2RE7': 'GS1.1.1705532245.1.0.1705532250.0.0.0',
        '_ga_45SCT2E2LM': 'GS1.2.1710243958.6.0.1710243958.60.0.0',
        '_ga_EVYRH4J3SP': 'GS1.1.1710697627.53.0.1710697627.0.0.0',
        '_ga_P7HXBG8L73': 'GS1.1.1710697627.55.0.1710697627.0.0.0',
        '_ga': 'GA1.2.308807853.1701298993',
        'ASP.NET_SessionId': 'oi0sjzi5oclme01dztvbmda0',
        '_gid': 'GA1.2.2087917036.1710934762',
        '_ga_J4ZD36GZ4Z': 'GS1.2.1710934762.53.0.1710934762.60.0.0',
        'ASPSESSIONIDSGCSTSCC': 'PBIMPPOAMDCLMMKCAGDCMGJD',
        'cookiesession1': '678B289230A0F4DA773BAF428CBD4812',
    }   
    params = {
        'csrf_token': '{07802E4E-E746-4A43-A339-978640700D82}',
    }
    testpoints = [
        'ltc-survey.asp?Facid=750301&PAGE=1&SurveyType=H', 'ltc-survey.asp?Facid=27171500&PAGE=1&SurveyType=H', 
        'ltc-survey.asp?Facid=061901&PAGE=1&SurveyType=H', 'ltc-survey.asp?Facid=195601&PAGE=1&SurveyType=H', 
        'ltc-survey.asp?Facid=120801&PAGE=1&SurveyType=H', 'ltc-survey.asp?Facid=22701501&PAGE=1&SurveyType=H', 
        'ltc-survey.asp?Facid=53020100&PAGE=1&SurveyType=H', 'ltc-survey.asp?Facid=24230101&PAGE=1&SurveyType=H'
    ]
    
    links = await async_getlinks(daac_url, headers=headers)
    unique_list = list(set(links))
    endpoints = get_endpoints(unique_list)
    
    #tasks = [scrape_pages(url, headers, cookies) for url in endpoints]  # Prepare coroutine list
    #results = await asyncio.gather(*tasks)  # Run concurrently
    
    batch_size = 10  # Number of concurrent requests
    delay_between_batches = 15  # Seconds

    for i in range(0, len(endpoints), batch_size):
        batch = endpoints[i:i+batch_size]
        tasks = [scrape_pages(url, headers, cookies, params) for url in endpoints]  # Prepare coroutine list
        results = await asyncio.gather(*tasks)
        save_json(results)
        await asyncio.sleep(delay_between_batches)  # Delay before the next batch
    
    # Save results to JSON files
    #for result in results:
        #save_json(result)
    
if __name__ == "__main__":
    start_time = time.time()  # record the start time
    asyncio.run(main())
    end_time = time.time()  # record the end time
    total_time = end_time - start_time  # calculate the execution time
    print(f"Total execution time: {total_time} seconds")  