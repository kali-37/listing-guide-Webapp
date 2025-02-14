from click import File
import httpx
import re
import os
import logging
from bs4 import BeautifulSoup
from bs4 import Tag
from typing import Optional
import re
from category_dict import Category, Query
from category_dict import categories
import asyncio
from asyncio import Task


class Colors:
    # grey = "\x1b[38;20m"
    # green = "\x1b[32;20m"
    # yellow = "\x1b[33;20m"
    # red = "\x1b[31;20m"
    # bold_red = "\x1b[31;1m"
    # reset = "\x1b[0m"
    
    # For Streamlit processes we need to use the following ANSI escape codes

    grey = ""
    green = ""
    yellow = ""
    red = ""
    bold_red = ""
    reset = ""

class FileHandler:
    def __init__(self, file_name):
        self.file_name = file_name
        self.init_file()
        self.file_data = []

    def init_file(self):
        with open(self.file_name, "w") as f:
            data = [
                "Price",
                "Shop Now Link",
                "Watchers",
                "Title",
                "Start Date",
                "End Date",
                "Running Time",
            ]
            f.write(",".join(data) + "\n")
        print("WRITETN TO FILE ",self.file_name)

    def write_to_file(self, data):
        # self.file_data.append(data)
        with open(self.file_name, "a") as f:
            f.write(",".join(data) + "\n")



class Logger:
    def __init__(self, file_name):
        self.logger = logging.getLogger(__name__)
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(self.formatter)
        if not file_name == "":
            self.file_handler = logging.FileHandler(
                file_name, mode="a", encoding="utf-8"
            )
            self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)

    def set_color_msg(self, info, message):
        return f"{info}{message}{Colors.reset}"

    def info(self, message):
        self.logger.info(self.set_color_msg(Colors.green, message))

    def debug(self, message):
        self.logger.debug(self.set_color_msg(Colors.grey, message))

    def error(self, message):
        self.logger.error(self.set_color_msg(Colors.red, message))

    def warning(self, message):
        self.logger.warning(self.set_color_msg(Colors.yellow, message))


from typing import Any


class AsyncScraper:
    def __init__(self):
        self.write_queue = asyncio.Queue()
        self.write_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(15)
        self.data_instance: Any | FileHandler= None
        self.logger = Logger("")

    async def csv_format(self, data_rows: dict):
        """Convert extracted data to CSV format."""
        if not data_rows:
            return []

        csv_row = [str(value) for value in data_rows.values()]

        return csv_row

    async def extract_data_rows(self, rows):

        for soup in rows:
            # Find the main listing div
            listing_div = soup.find("div", class_="find-results-new-item")

            # Extract price
            price = listing_div.find("div", class_="price").text.strip()

            # Extract shop now link
            shop_now_link = listing_div.find("div", class_="col bold-text").find(
                "a", href=True
            )["href"]

            # Extract watchers count
            watchers_text = listing_div.find("div", class_="text-center").text.strip()
            watchers = watchers_text.split("*")[0].replace("Watchers:", "").strip()

            # Extract title
            title = (
                listing_div.find("div", class_="general-info-container")
                .find("div", class_="row")
                .text.replace("Start: ", "")
                .strip()
            )

            # Extract start and end dates
            start_date = listing_div.find_all("div", class_="row normal-text")[
                0
            ].text.strip()
            end_date = (
                listing_div.find_all("div", class_="row normal-text")[1]
                .text.replace("End:  ", "")
                .strip()
            )

            # Extract running time
            running_time = (
                listing_div.find_all("div", class_="row normal-text")[2]
                .text.replace("Running for ", "")
                .strip()
            )
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

            # self.logger.info(f"Extracted data: {csv_formatted}")
            # file_obj.write_to_file(csv_formatted)

    async def parse_html(self, response_text: str, offset: int):
        """
        Parses the HTML response and returns the count of 'row' divs.

        Args:
            response_text (str): The HTML content to parse.

        Returns:
            int: The count of 'row' divs found.
        """
        soup = BeautifulSoup(response_text, "html.parser")

        # Find the main container
        data_soup: Optional[Tag] | Any = soup.find(
            "div", {"class": "find-results results"}
        )
        if not data_soup:
            self.logger.error(f"No data found after offset :{offset}")
            exit(0)

        # Find the sub-container
        data_containers: Optional[Tag] | Any = data_soup.find(
            "div", {"class": "container shrink-container"}
        )
        if not data_containers:
            self.logger.error("No data containers found in the HTML")
            raise ValueError("No data containers found")

        rows = data_containers.find_all("div", {"class": "row"}, recursive=False)
        await self.extract_data_rows(rows)

    async def check_end_of_results(self, response_text: str):
        soup = BeautifulSoup(response_text, "html.parser")
        soup = soup.find("div", class_="find-results-pagination row my-3")
        if soup is None:
            return False
        if "Next" in soup.text:
            return True
        return False

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
        self.logger.info(f"Requesting {url}")
        response = httpx.get(
            url,
            timeout=30,
        )
        match = re.search(r"([\d,]+) Result(s)* for", response.text)
        if not match:
            self.logger.error(f"Unable to find the total results for {category}")
            return
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
        response = await client.get(
            url,
            timeout=30,
        )
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
            self.logger.info(f"No results found for {category}")
            return
        # Create bulk task for all pages with max concurrency of 15
        # per page it has 20 listings
        # listing can be less or equal to 20 also ,
        # in that case we need to scrape only one time , else we need to scrape multiple times
        tasks = []
        client = httpx.AsyncClient()
        for i in range(0, total_number_of_pages, 20):
            if len(tasks) >= max_request:
                await asyncio.gather(*tasks)
                await asyncio.sleep(delay)
                tasks = []
            tasks.append(
                self.scrape_each_category_bulk(category, seller_name, client, i)
            )
        await asyncio.gather(*tasks)

    async def initallize_scraper(
        self,
        selected_category: list[Category],
        seller_list: list[str],
        file_name,
        log_file,
        max_requests,
        delay,
    ):
        self.logger = Logger(log_file)
        self.data_instance=FileHandler(file_name)
        writer_task = asyncio.create_task(self.writer_task())
        for seller in seller_list:
            self.logger.info(f"Scraping for seller: {seller}")
            for category in selected_category:
                await self.scraper(category, seller,max_requests,delay)
        await self.complete_writer_task(writer_task)
        return self.data_instance.file_data


async def scrape(seller_list, selected_category,file_name, log_file,max_requests,delay):
    async_obj = AsyncScraper()
    data_read = await async_obj.initallize_scraper(
         selected_category, seller_list,file_name,log_file,max_requests, delay
    )
    os.remove(log_file)
    print(data_read)
    return data_read

# print(asyncio.run(scrape(["humble.2"],[categories["2"],categories["3"]], "output.csv", "log.log")))

















#  DUMPED  CODE
'''
def get_category_info():
    print(
        f"""
    {Colors.green}
    Categories:
      {Colors.reset}  1. {Colors.bold_red}   Antiques [#20081]
      {Colors.reset}  2. {Colors.bold_red}   Art [#550]
      {Colors.reset}  3. {Colors.bold_red}   Baby [#2984]
      {Colors.reset}  4. {Colors.bold_red}   Books & Magazines [#267]
      {Colors.reset}  5. {Colors.bold_red}   Business & Industrial [#12576]
      {Colors.reset}  6. {Colors.bold_red}   Cameras & Photo [#625]
      {Colors.reset}  7. {Colors.bold_red}   Cell Phones & Accessories [#15032]
      {Colors.reset}  8. {Colors.bold_red}   Clothing, Shoes & Accessories [#11450]
      {Colors.reset}  9. {Colors.bold_red}   Coins & Paper Money [#11116]
      {Colors.reset}  10.{Colors.bold_red}   Collectibles [#1]
      {Colors.reset}  11.{Colors.bold_red}   Computers/Tablets & Networking [#580581]
      {Colors.reset}  12.{Colors.bold_red}   Consumer Electronics [#293]
      {Colors.reset}  13.{Colors.bold_red}   Crafts [#14339]
      {Colors.reset}  14.{Colors.bold_red}   Dolls & Bears [#237]
      {Colors.reset}  15.{Colors.bold_red}   eBay Motors [#6000]
      {Colors.reset}  16.{Colors.bold_red}   Entertainment Memorabilia [#45100]
      {Colors.reset}  17.{Colors.bold_red}   Everything Else [#99]
      {Colors.reset}  18.{Colors.bold_red}   Gift Cards & Coupons [#172008]
      {Colors.reset}  19.{Colors.bold_red}   Health & Beauty [#26395]
      {Colors.reset}  20.{Colors.bold_red}   Home & Garden [#11700]
      {Colors.reset}  21.{Colors.bold_red}   Jewelry & Watches [#281]
      {Colors.reset}  22.{Colors.bold_red}   Movies & TV [#11232]
      {Colors.reset}  23.{Colors.bold_red}   Music [#11233]
      {Colors.reset}  24.{Colors.bold_red}   Musical Instruments & Gear [#619]
      {Colors.reset}  25.{Colors.bold_red}   Pet Supplies [#1281]
      {Colors.reset}  26.{Colors.bold_red}   Pottery & Glass [#870]
      {Colors.reset}  27.{Colors.bold_red}   Real Estate [#10542]
      {Colors.reset}  28.{Colors.bold_red}   Specialty Services [#316]
      {Colors.reset}  29.{Colors.bold_red}   Sporting Goods [#888]
      {Colors.reset}  30.{Colors.bold_red}   Sports Mem, Cards & Fan Shop [#64482]
      {Colors.reset}  31.{Colors.bold_red}   Stamps [#260]
      {Colors.reset}  32.{Colors.bold_red}   Tickets & Experiences [#1305]
      {Colors.reset}  33.{Colors.bold_red}   Toys & Hobbies [#220]
      {Colors.reset}  34.{Colors.bold_red}   Travel [#3252]
      {Colors.reset}  35.{Colors.bold_red}   Video Games & Consoles [#1249]

        {Colors.reset}
    """
    )
    category = input(
        f"{Colors.green}Please Enter the Category: {Colors.reset} "
    ).strip()
    categorie = []
    list_of_categories = [int(i) for i in category.split(",")]
    if not all(i in range(1, 36) for i in list_of_categories):
        Logger("").error("Invalid Category ")
        print("Choose a valid category in range 1-35")
        input()
        return get_category_info()
    for i in category.split(","):
        categorie.append(categories[f"{i}"])
    return categorie


def get_seller_info():
    seller_name = input(
        f"{Colors.green}Please Enter the Seller Name: {Colors.reset} "
    ).strip()
    seller_list = [i.strip() for i in seller_name.split(",") if i != ""]
    return seller_list
'''
