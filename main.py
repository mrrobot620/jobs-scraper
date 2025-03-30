import os
import csv
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from html2docx import html2docx
from htmldocx import HtmlToDocx
from docx import Document
from rich import print
from rich.panel import Panel

class Scraper:
    def __init__(self):
        print(f"[bold green]SUCCESS :[/] Initializing Scraper")
        self.job_urls = []

    async def start_scraping(self):
        urls = await self.get_post_category()
        await self.create_folders(urls)
        tasks = [self.scrape_jobs(url) for url in urls]
        await asyncio.gather(*tasks)
        print(f'[bold yellow]INFO:[/] Total Jobs Posting: {len(self.job_urls)}')
        tasks = [self.job_post_scraper(entry['url'], entry['category']) for entry in self.job_urls]
        await asyncio.gather(*tasks)
        print(Panel("[bold green]✅ Script Completed Successfully!! ✅[/]", expand=False))


    async def create_folders(self, urls):
        for url in urls:
            folder_name = url.split("/")[-1]
            if os.path.exists(folder_name):
                print(f"[bold yellow]INFO:[/] Folder {folder_name} already exists")
            else:
                print(f"[bold green]SUCCESS:[/] Folder {folder_name} created")
                os.mkdir(folder_name)

    async def csv_writer(self, data):
        with open("jobs.csv", 'w', newline="", encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Category", "url"])
            for item in data:
                writer.writerow([item['category'], item['url']])

    async def get_post_category(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://rsrglobal.org/") as response:
                if response.status == 200:
                    data = await response.text()
                    return await self.parse_section_url(data)
                else:
                    print(f'[bold red]ERROR:[/] Failed to get Job categories | Response: {response.status}')

    async def parse_section_url(self, html_content):
        soup = BeautifulSoup(html_content, 'lxml')
        urls = [item.find('a')['href'] for item in soup.find_all('div', class_="more mt-4 mb-4")]
        print(f'[bold yellow]INFO:[/] Found {len(urls)} urls in job section')
        return urls

    async def scrape_jobs(self, url):
        category = url.split("/")[-1]
        print(f'[bold yellow]INFO:[/] Starting Scraping Jobs for Category: {category}')
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.text()
                    await self.parse_jobs_urls(data, category)
                else:
                    print(f'[bold red]ERROR:[/] Failed to fetch Jobs for Category: {category}')

    async def check_and_add(self , url: dict):
        countries: list[str] = ['indian' , 'india' , 'uae' , 'emirates' , "bahrain" , 'kuwait'
                                , "oman" , 'qatar' , "saudi arabia" , 'arabia' , 'united arb emirates']
        for word in countries:
            if word.lower() in url['url'].lower():
                print(f'[bold yellow]INFO:[/] skipping job post as its from country: {word.lower()} | url: {url["url"]}')
                return
        print(f"[bold green]SUCCESS:[/] Adding Job to Main Instance | {url}")
        self.job_urls.append(url)
        

    async def parse_jobs_urls(self, html_content, category):
        soup = BeautifulSoup(html_content, 'lxml')
        for div in soup.find_all('div', class_="more"):
            url = div.find('a')['href']
            entry = {"category": category, "url": url}
            await self.check_and_add(entry)

    async def job_post_scraper(self, url, category):
        job_name = url.split("/")[-2]
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"[red]ERROR:[/] Failed to scrape job: {url} with status_code: {response.status}")
                    return
                data = await response.text()
                soup = BeautifulSoup(data, "lxml")
                elements = soup.find('div', class_="content")
                if not elements:
                    print(f'[red]ERROR:[/] Element is null')
                    return
                await self.html_parser(str(elements), job_name, category)

    async def html_parser(self, html_content, file_name, folder):
        try:
            document = Document()
            new_parser = HtmlToDocx()
            document.add_heading(file_name, 0)
            new_parser.add_html_to_document(html_content, document)
            file = os.path.join(folder, f"{file_name}.docx")
            document.save(file)
            print(f'[bold green]SUCCESS:[/] [bold blue]{file}[/] created in category: [underline blue]{folder}[/]')
        except Exception as e:
            print(f"[bold red]ERROR:[/] Failed to retrieve job: [red]{file_name}[/] with Exception: [red]{e}[/]")
            await self.fallback_parser(html_content, file_name, folder)

    async def fallback_parser(self, html_content, file_name, folder):
        try:
            file = os.path.join(folder, f"{file_name}.docx")
            buf = html2docx(html_content, title=file_name)
            with open(file, "wb") as f:
                f.write(buf.getvalue())
            print(f'[bold green]FALLBACK RETRY SUCCESS:[/] [bold blue]{file}[/] created in category: [underline blue]{folder}[/]')
        except Exception as e:
            print(f"[bold red]ERROR:[/] Fallback parser also failed for: [red]{file_name}[/] with Exception: [red]{e}[/]")


if __name__ == '__main__':
    scp = Scraper()
    asyncio.run(scp.start_scraping())
