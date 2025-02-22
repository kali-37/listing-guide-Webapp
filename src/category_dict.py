from dataclasses import dataclass
from enum import Enum
import asyncio


@dataclass
class Category:
    name: str
    u_code: int
    represent: str = ""

    def __post_init__(self):
        self.represent = "_".join(self.name.split(" "))

    def __str__(self):
        return f"{self.represent}_{self.u_code}"


@dataclass
class Query:
    category: Category
    seller: str
    offset_value: int

    def __str__(self):
        return f"https://www.watchcount.com/live/-/{self.category.__str__()}/all?minPrice=150&offset={self.offset_value}&seller={self.seller}"


@dataclass
class ScrapingTask:
    category: str
    url: str
    offset: int


categories = {
    "1": Category("antiques", 20081),
    "2": Category("art", 550),
    "3": Category("baby", 2984),
    "4": Category("books magazines", 267),
    "5": Category("business industrial", 12576),
    "6": Category("cameras photo", 625),
    "7": Category("cell phones accessories", 15032),
    "8": Category("clothing shoes accessories", 11450),
    "9": Category("coins paper money", 11116),
    "10": Category("collectibles", 1),
    "11": Category("computers tablets networking", 580581),
    "12": Category("consumer electronics", 293),
    "13": Category("crafts", 14339),
    "14": Category("dolls bears", 237),
    "15": Category("ebay motors", 6000),
    "16": Category("entertainment memorabilia", 45100),
    "17": Category("everything else", 99),
    "18": Category("gift cards coupons", 172008),
    "19": Category("health beauty", 26395),
    "20": Category("home garden", 11700),
    "21": Category("jewelry watches", 281),
    "22": Category("movies tv", 11232),
    "23": Category("music", 11233),
    "24": Category("musical instruments gear", 619),
    "25": Category("pet supplies", 1281),
    "26": Category("pottery glass", 870),
    "27": Category("real estate", 10542),
    "28": Category("specialty services", 316),
    "29": Category("sporting goods", 888),
    "30": Category("sports mem cards fan shop", 64482),
    "31": Category("stamps", 260),
    "32": Category("tickets experiences", 1305),
    "33": Category("toys hobbies", 220),
    "34": Category("travel", 3252),
    "35": Category("video games consoles", 1249),
}
