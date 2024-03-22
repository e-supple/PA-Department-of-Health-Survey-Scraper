import os
from datetime import datetime
import requests
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup, NavigableString
import json
import csv
from tqdm import tqdm

def save_csv(data):
    fieldnames = ['eventid', 'date', 'data']
    facility_name = data.get('facility', 'unknown_facility').replace(' ', '_')
    survey_date = data.get('date', 'unknown_date').replace('/', '-')
    filename = f'survey_{facility_name}_{survey_date}'
    
    os.makedirs('./json', exist_ok=True)
    with open('./csv/survey_data{}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for survey in data:
            writer.writerow(survey)
            
def save_json(data):
    os.makedirs('./json', exist_ok=True)
    facility_name = data['facility'].replace(' ', '_').replace('/', '-').replace('<br>', '')
    
    # Start with the base filename, assuming no number appended
    filename = f'survey_{facility_name}'
    file_extension = '.json'
    file_path = f'./json/{filename}{file_extension}'
    counter = 0
    
    while os.path.exists(file_path):
        counter += 1
        file_path = f'./json/{filename}.{counter}{file_extension}'
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f'Data has been written to {file_path}.')
            
def get_endpoints(links):
    uri = 'https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/'
    endpoints = [link.replace(uri, '') for link in links]
    return endpoints

def contains_ad3m(text):
    text_lower = text.lower()
    return any(char in text_lower for char in ['a', 'd', '3', 'm'])

def contains_m(text):
    text_lower = text.lower()
    return any(char in text_lower for char in ['m'])

def get_links(url, headers):
    # url = f'https://apps.health.pa.gov/surveyspostedDAAC/DAAC-SurveysPosted_202402.aspx'
    page = requests.get(url, headers)
    soup = BeautifulSoup(page.content, "html.parser")
    content_container = soup.find('div', class_='content-container')
    table = content_container.find('table')
    rows =  table.find_all('tr')

    filterd_rows = [row for row in rows if len(row.find_all('td')) >= 4 and contains_m(row.find_all('td')[3].text)]
    # links = [[cell for cell in row.find_all('td')[1]] for row in filterd_rows]
    urls = [cell.find('a')['href'] for row in filterd_rows for cell in row.find_all('td', limit=2) if cell.find('a')]
    
    return urls

def scrape_pages(link, headers, cookies, data):
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
    response = requests.get(initial_page_url, headers=headers, cookies=cookies)
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
        options = select_element.find_all('option')
        options = filter_surveys_by_year(options)
        
        for option in options:
            eventid = option['value']
            date_txt = option.text.strip()
            # print(f"Processing {date_txt} with eventid {eventid}") #Debugg line
            survey_details = {'eventid': eventid, 'date': date_txt}
            
            survey_url = f"{base_url}ltc-survey.asp?facid={facid}&page=1&name=&SurveyType=H&eventid={eventid}" 
            survey_response = requests.get(survey_url, headers=headers, cookies=cookies, data=data)
            soup = BeautifulSoup(survey_response.content, 'html.parser')
            tables = soup.findAll('table')
            
            if len(tables) >= 5:
                data_tables = tables[5:-1]
                survey_details['data'] = ' '.join([table.text.strip() for table in data_tables])            
            survey_data.append(survey_details)
        all_survey_data['data'] = survey_data
        
        return all_survey_data  
    else:
        print("Couldn't find the survey list dropdown.")

def filter_surveys_by_year(options, years=[2023, 2024]):
    filtered_options = []
    for option in options:
        date_text = option.text.strip()
        try:
            survey_date = datetime.strptime(date_text, "%m/%d/%Y")
            if survey_date.year in years:
                filtered_options.append(option)
                print(f"Filtered Dates: Complete {filtered_options}")
        except ValueError:
            # Handle date format does not match or parsing fails
            print(f"Error parsing date for option: {date_text}")
    return filtered_options
 
def main():
    
    links = [
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=450501&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=234501&PAGE=1&SurveyType=H", # Wilkes Barre General
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=450501&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=22800101&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=200701&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=200801&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=340601&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=163301&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=196901&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=196901&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=234601&PAGE=1&SurveyType=H"
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=530201&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=50630101&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=072001&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/zCommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=072001&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=072001&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=421001&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=421001&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=421001&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=421001&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=123101&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=135101&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=135501&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=135501&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=135501&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=010901&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=101101&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=50670101&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=340801&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=21700101&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=440401&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=440601&PAGE=1&SurveyType=H",
        # "https://sais.health.pa.gov/CommonPOC/Content/PublicWeb/ltc-survey.asp?Facid=440601&PAGE=1&SurveyType=H",
    ]
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Cookie': '_ga_43SYEQBLV4=GS1.1.1701298993.1.1.1701299170.0.0.0; _ga_Y97KNG0WT3=GS1.1.1702655416.2.0.1702655416.0.0.0; _ga_EFBFYET3JS=GS1.1.1705532227.1.1.1705532239.0.0.0; visid_incap_2815744=xjCHti1DRE+C+DecvMgYa1NbqGUAAAAAQUIPAAAAAABnHMKnuYDw6XcK4WUnuxn1; _ga_5ETEHW2RE7=GS1.1.1705532245.1.0.1705532250.0.0.0; _ga_45SCT2E2LM=GS1.2.1710243958.6.0.1710243958.60.0.0; _ga_EVYRH4J3SP=GS1.1.1710697627.53.0.1710697627.0.0.0; _ga_P7HXBG8L73=GS1.1.1710697627.55.0.1710697627.0.0.0; _ga=GA1.2.308807853.1701298993; ASP.NET_SessionId=oi0sjzi5oclme01dztvbmda0; _gid=GA1.2.2087917036.1710934762; _ga_J4ZD36GZ4Z=GS1.2.1710934762.53.0.1710934762.60.0.0; ASPSESSIONIDSGCSTSCC=PBIMPPOAMDCLMMKCAGDCMGJD; cookiesession1=678B289230A0F4DA773BAF428CBD4812',
        'Host': 'sais.health.pa.gov',
        'Referer': 'https://sais.health.pa.gov/',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
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
    
    data = {
        'csrf_token': '{481D89AA-A17F-4BBE-96B3-C9EE3BBBB2DF}',
    }
    
    main_page_url = 'https://apps.health.pa.gov/surveyspostedDAAC/DAAC-SurveysPosted_202402.aspx'
    links = get_links(url=main_page_url, headers=headers)
    unique_list = list(set(links))    
    endpoints = get_endpoints(unique_list)
    # print(f'{endpoints}')
    for link in tqdm(endpoints, desc="Scraping Progress", unit="link"):
        data = scrape_pages(link, headers, cookies, data)
        if data is not None: 
            save_json(data)
        else:
            print(f"No data to save for link: {link}")
            
if __name__ == '__main__':
    main()