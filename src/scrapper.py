import httpx
import re
import logging
from bs4 import BeautifulSoup
from bs4 import Tag
from typing import Optional, Any
import asyncio
from asyncio import Task
from category_dict import Category, Query
from category_dict import categories


class Colors:
    grey = ""
    green = ""
    yellow = ""
    red = ""
    bold_red = ""
    reset = ""


class FileHandler:
    def __init__(self):
        self.file_data = []

    def write_to_file(self, data):
        self.file_data.append(data)


class Logger:
    def __init__(self, file_name=""):
        self.logger = logging.getLogger(__name__)
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.current_info_msg = ""
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(self.formatter)
        if file_name != "":
            self.file_handler = logging.FileHandler(file_name, mode="a", encoding="utf-8")
            self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)


    def set_color_msg(self, info, message):
        return f"{info}{message}{Colors.reset}"

    def info(self, message):
        self.current_info_msg = message
        self.logger.info(self.set_color_msg(Colors.green, message))
    
    def get_previous_info(self):
        return self.current_info_msg

    def debug(self, message):
        self.logger.debug(self.set_color_msg(Colors.grey, message))

    def error(self, message):
        self.logger.error(self.set_color_msg(Colors.red, message))

    def warning(self, message):
        self.logger.warning(self.set_color_msg(Colors.yellow, message))


class AsyncScraper:
    def __init__(self):
        self.write_queue = asyncio.Queue()
        self.write_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(15)
        self.data_instance: Any | FileHandler = None
        self.logger = Logger("")
        self.destruct_current_flow = False # Flag to destruct the current flow

    async def csv_format(self, data_rows: dict):
        """Convert extracted data to CSV format."""
        if not data_rows:
            return []
        csv_row = [str(value) for value in data_rows.values()]
        return csv_row

    async def extract_data_rows(self, rows):
        for soup in rows:
            listing_div = soup.find("div", class_="find-results-new-item")
            if not listing_div:
                self.logger.error("Listing div not found.")
                continue

            try:
                price = listing_div.find("div", class_="price").text.strip()
                shop_now_link = listing_div.find("div", class_="col bold-text").find(
                    "a", href=True
                )["href"]
                watchers_text = listing_div.find("div", class_="text-center").text.strip()
                watchers = watchers_text.split("*")[0].replace("Watchers:", "").strip()
                if int(watchers) == 0:
                    self.destruct_current_flow = True
                    if self.logger.get_previous_info() != "Stopping the Scrapping flow as watchers are 0":
                        self.logger.info("Stopping the Scrapping flow as watchers are 0")
                    continue
                title = (
                    listing_div.find("div", class_="general-info-container")
                    .find("div", class_="row")
                    .text.replace("Start: ", "")
                    .strip()
                )
                start_date = listing_div.find_all("div", class_="row normal-text")[0].text.strip()
                end_date = (
                    listing_div.find_all("div", class_="row normal-text")[1]
                    .text.replace("End:  ", "")
                    .strip()
                )
                running_time = (
                    listing_div.find_all("div", class_="row normal-text")[2]
                    .text.replace("Running for ", "")
                    .strip()
                )
            except Exception as e:
                self.logger.error(f"Error extracting data rows: {e}")
                continue

            data = {
                "Price": price.replace(",", ""),
                "Shop Now Link": shop_now_link.replace(",", ""),
                "Watchers": watchers.replace(",", ""),
                "Title": title.replace(",", ""),
                "Start Date": re.sub(r"\s\(.*\)", "", start_date).replace(",", ""),
                "End Date": re.sub(r"\s\(.*\)", "", end_date).replace(",", ""),
                "Running Time": running_time.replace(",", ""),
            }
            csv_formatted = await self.csv_format(data)
            if csv_formatted:
                await self.write_queue.put(csv_formatted)

    async def parse_html(self, response_text: str, offset: int):
        """
        Parses the HTML response and processes the rows.
        """
        soup = BeautifulSoup(response_text, "html.parser")
        data_soup: Optional[Tag] | Any = soup.find("div", {"class": "find-results results"})
        if not data_soup:
            self.logger.error(f"No data found after offset: {offset}")
            return  

        data_containers: Optional[Tag] | Any = data_soup.find("div", {"class": "container shrink-container"})
        if not data_containers:
            self.logger.error("No data containers found in the HTML")
            return

        rows = data_containers.find_all("div", {"class": "row"}, recursive=False)
        await self.extract_data_rows(rows)

    async def check_end_of_results(self, response_text: str):
        soup = BeautifulSoup(response_text, "html.parser")
        pagination = soup.find("div", class_="find-results-pagination row my-3")
        if pagination is None:
            return False
        return "Next" in pagination.text

    async def complete_writer_task(self, writer_task: Task) -> None:
        await self.write_queue.join()
        writer_task.cancel()
        try:
            await writer_task
        except asyncio.CancelledError:
            pass

    async def writer_task(self) -> None:
        while True:
            try:
                data = await self.write_queue.get()
                async with self.write_lock:
                    self.data_instance.write_to_file(data)
                self.write_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error in writer task: {str(e)}")

    async def get_max_records(self, category: Category, seller_name: str):
        url = str(Query(category, seller_name, 0))
        self.logger.info(f"Requesting {url} to determine max records")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=60)
        except httpx.TimeoutException as exc:
            self.logger.error(f"Timeout while getting max records for {url}: {exc}")
            return None
        except httpx.RequestError as exc:
            self.logger.error(f"Request error while getting max records for {url}: {exc}")
            return None

        match = re.search(r"([\d,]+) Result(s)* for", response.text)
        if not match:
            self.logger.error(f"Unable to find the total results for {category} at {url}")
            return None
        return int(match.group(1).replace(",", ""))

    async def scrape_each_category_bulk(
        self,
        category: Category,
        seller_name: str,
        client: httpx.AsyncClient,
        offset_value: int,
    ):
        url = str(Query(category, seller_name, offset_value))
        self.logger.info(f"Requesting {url}")
        try:
            response = await client.get(url)
        except httpx.TimeoutException as exc:
            self.logger.error(f"Timeout error for {url}: {exc}")
            return  
        except httpx.RequestError as exc:
            self.logger.error(f"Request error for {url}: {exc}")
            return  

        await self.parse_html(response.text, offset_value)

    async def scraper(
        self,
        category: Category,
        seller_name: str,
        max_request=7,
        delay=3,
    ):
        total_number_of_pages = await self.get_max_records(category, seller_name)
        if not total_number_of_pages or total_number_of_pages == 0:
            self.logger.info(f"No results found for {category} and seller {seller_name}")
            return

        tasks = []
        client = httpx.AsyncClient(timeout=60)
        self.destruct_current_flow = False
        for i in range(0, min(total_number_of_pages, 2000), 20):
            if len(tasks) >= max_request:
                try:
                    await asyncio.gather(*tasks)
                except Exception as e:
                    self.logger.error(f"Error during bulk scraping tasks: {e}")
                await asyncio.sleep(delay)
                tasks = []
            if self.destruct_current_flow:
                break
            tasks.append(
                self.scrape_each_category_bulk(category, seller_name, client, i)
            )
        if tasks:
            await asyncio.gather(*tasks)
        await client.aclose()

    async def initallize_scraper(
        self,
        selected_category: list[Category],
        seller_list: list[str],
        max_requests,
        delay,
    ):
        self.logger = Logger()
        self.data_instance = FileHandler()
        writer_task = asyncio.create_task(self.writer_task())
        for seller in seller_list:
            self.logger.info(f"Scraping for seller: {seller}")
            for category in selected_category:
                await self.scraper(category, seller, max_requests, delay)
        await self.complete_writer_task(writer_task)
        return self.data_instance.file_data


async def scrape(seller_list, selected_category, max_requests, delay):
    async_obj = AsyncScraper()
    data_read = await async_obj.initallize_scraper(
        selected_category, seller_list, max_requests, delay
    )
    return data_read
