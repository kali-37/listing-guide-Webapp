import httpx
import logging
from bs4 import BeautifulSoup
from bs4 import Tag
from typing import Optional
import re
from category_dict import Query
from category_dict import categories
from category_dict import SetOffset
import asyncio 
from asyncio import Task



class Colors:
    grey = "\x1b[38;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"



class FileHandler:
    def __init__(self, file_name):
        self.file_name = file_name
        self.init_file()

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

    def write_to_file(self, data):
        with open(self.file_name, "a") as f:
            f.write(",".join(data) + "\n")


class Logger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(self.formatter)
        self.file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
        self.logger.addHandler(self.console_handler)
        self.logger.addHandler(self.file_handler)

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


logger = Logger()


class AsyncScraper:
    def __init__(self,max_concurrency:int):
        self.write_queue = asyncio.Queue()
        self.write_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(15)
        self.file_instance:FileHandler 


    async def writer_task(self) -> None:
        while True:
            try:
                data = await self.write_queue.get()
                async with self.write_lock:
                    self.file_instance.write_to_file(data)
                self.write_queue.task_done()
            except Exception as e:
                logger.error(f"Error in writer task: {str(e)}")

    async def complete_writer_task(self, writer_task: Task) -> None:
        await self.write_queue.join()
        writer_task.cancel()
        try:
            await writer_task
        except asyncio.CancelledError:
            pass




def csv_format(data_rows: dict):
    """Convert extracted data to CSV format."""
    if not data_rows:
        return []

    csv_row = list(data_rows.values())

    return csv_row


def extract_data_rows(rows, file_obj: FileHandler):

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
        csv_formatted = csv_format(data)
        # logger.info(f"Extracted data: {csv_formatted}")
        file_obj.write_to_file(csv_formatted)


def parse_html(response_text: str, offset: int, file_inst: FileHandler):
    """
    Parses the HTML response and returns the count of 'row' divs.

    Args:
        response_text (str): The HTML content to parse.

    Returns:
        int: The count of 'row' divs found.
    """
    soup = BeautifulSoup(response_text, "html.parser")

    # Find the main container
    data_soup: Optional[Tag] = soup.find("div", {"class": "find-results results"})
    if not data_soup:
        logger.error(f"No data found after offset :{offset}")
        exit(0)

    # Find the sub-container
    data_containers: Optional[Tag] = data_soup.find(
        "div", {"class": "container shrink-container"}
    )
    if not data_containers:
        logger.error("No data containers found in the HTML")
        raise ValueError("No data containers found")

    rows = data_containers.find_all("div", {"class": "row"}, recursive=False)
    csv_formatted = csv_format(extract_data_rows(rows, file_inst))


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
        logger.error("Invalid Category ")
        print("Choose a valid category in range 1-35")
        input()
        return get_category_info()
    for i in category.split(","):
        categorie.append(categories[f"{i}"])
    return categorie


def check_end_of_results(response_text: str):
    soup = BeautifulSoup(response_text, "html.parser")
    soup = soup.find("div", class_="find-results-pagination row my-3")
    print(soup.text)
    if soup is None:
        return False
    if "Next" in soup.text:
        return True
    return False


def main():
    seller_name = input(f"{Colors.green}Please Enter the Seller Name: {Colors.reset} ")
    selected_category = get_category_info()

    file_name = input(
        str(
            f"{Colors.green} Write a file name you want to save the resulting csv:{Colors.reset} "
        )
    )
    file_instance = FileHandler(file_name)
    def scrape(category, seller_name, file_instance):
        url = str(Query(category, seller_name))
        logger.info(f"Requesting {url}")
        response = httpx.get(
            url,
            timeout=30,
        )
        if "0 Results" in response.text:
            logger.error(f"Reached end of results {category}")
            return
        if not check_end_of_results(response.text):
            parse_html(response.text, SetOffset.offset, file_instance)
            logger.info(f"2: End of results reached for {category}")
            return
        parse_html(response.text, SetOffset.offset, file_instance)
        SetOffset.inc_offset(20)
        scrape(category, seller_name, file_instance)
    for category in selected_category:
        scrape(category, seller_name, file_instance)


if __name__ == "__main__":
    main()
