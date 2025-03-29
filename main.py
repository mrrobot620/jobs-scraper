import requests
from bs4 import BeautifulSoup, element
import csv
from docx import Document
from htmldocx import HtmlToDocx
import os
from concurrent.futures import ThreadPoolExecutor
from rich import print
from html2docx import html2docx


class Scraper():
    def __init__(self):
        print(f"[bold green]SUCCESS :[/] Intializing Scraper")
        self.job_urls: list[dict[str,str]] = []


    def start_scraping(self):
        urls = self.get_post_category()
        self.create_folders(urls)
        for url in urls:
            self.scrape_jobs(url)
        self.csv_writer(self.job_urls)
        print(f'[bold yellow]INFO:[/] Total Jobs Posting: {len(self.job_urls)}')
        with ThreadPoolExecutor(max_workers=3) as exc:
            futures = [exc.submit(self.job_post_scraper, entry['url'], entry['category']) for entry in self.job_urls] 
            for future in futures:
                future.result()

    
    def create_folders(self, urls):
        for url in urls:
            folder_name = url.split("/")[-1]
            if os.path.exists(folder_name):
                print(f"[bold yellow]INFO:[/]  Folder {folder_name} already exists")
            else:
                print(f"[bold green]SUCCESS:[/] Folder {folder_name} created")
                os.mkdir(folder_name)

    def csv_writer(self , data: list[dict[str,str]]):
        with open("jobs.csv" , 'w' , newline="" , encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Category" , "url"])

            for item in data:
                writer.writerow([item['category'] , item['url']])

    def get_post_category(self) -> list[str]:
        response = requests.get("https://rsrglobal.org/")
        if response.status_code == 200:
            data = response.text
            urls = self.parse_section_url(data)
            return urls
        else:
            print(f'[bold red]ERROR:[/] Failed to get Job categories | Response: {response.status_code}')

    def parse_section_url(self , html_content: str) -> list[str]:
        soup = BeautifulSoup(html_content , 'lxml')
        more_jobs_divs = soup.find_all('div' , class_="more mt-4 mb-4")
        urls: list[str] = []
        for item in more_jobs_divs:
            url = item.find('a')
            urls.append(url['href'])
        print(f'[bold yellow]INFO:[/] Found {len(urls)} urls in job section')
        return urls
    
    def scrape_jobs(self , url: str):
        category = url.split("/")[-1]
        print(f'[bold yellow]INFO:[/] Starting Scraping Jobs for Category: {category}')
        response = requests.get(url)
        if response.status_code == 200:
            data = response.text
            self.parse_jobs_urls(html_content=data,
                                        category=category)
        else:
            print(f'[bold red]ERROR:[/] Failed to fetch Jobs for Category: {category}')

    def parse_jobs_urls(self, html_content: str, category: str):
        soup = BeautifulSoup(html_content , 'lxml')
        jobs_divs = soup.find_all('div' , class_ = "more")
        for div in jobs_divs:
            url = div.find('a')
            entry = {"category": category , "url": f"{url['href']}"}
            print(f"[bold green]SUCCESS:[/] Adding Job to Main Instance | {entry}")
            self.job_urls.append(entry)

    def job_post_scraper(self , url: str , category: str):
        job_name = url.split("/")[-2]
        response = requests.get(url)
        if response.status_code != 200:
            print(f"[red]ERROR:[/] Failed to scraped job: {url} with status_code: {response.status_code}")
            return
        data = response.text
        soup = BeautifulSoup(data, "lxml")
        elements = soup.find('div', class_="content")
        if not elements:
            print(f'[red]ERROR:[/] Element is null')
            return
        self.html_parser(str(elements) , job_name , category)
        

    def html_parser(self , html_content, file_name , folder):
        try:
            document = Document()
            new_parser = HtmlToDocx()
            document.add_heading(file_name , 0)
            new_parser.add_html_to_document(html_content , document)
            file = os.path.join(folder, f"{file_name}.docx")
            document.save(file)
            print(f'[bold green]SUCCESS:[/] [bold blue]{file}[/] created in category: [underline blue]{folder}[/]')
        except Exception as e:
            print(f"[bold red]ERROR:[/] Failed to retrieve job: [red]{file_name}[/] with Exception : [red]{e}[/]")
            self.fallback_parser(html_content, file_name, folder)

    def fallback_parser(self, html_content, file_name, folder):
        try:
            file = os.path.join(folder, f"{file_name}.docx")
            buf = html2docx(html_content, title=file_name)
            with open(file, "wb") as f:
                f.write(buf.getvalue())
            print(f'[bold green]FALLBACK RETRY SUCCESS:[/] [bold blue]{file}[/] created in category: [underline blue]{folder}[/]')
        except Exception as e:
            print(f"[bold red]ERROR:[/] Fallback parser also failed for: [red]{file_name}[/] with Exception: [red]{e}[/]")

scp = Scraper()
scp.start_scraping()



