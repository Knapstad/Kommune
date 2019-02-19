# -*- coding: utf-8 -*-
"""
Created on Tue Jul 17 14:21:32 2018

@author: Bendik L Knapstad
"""

import os
import csv
import requests
import re
import time
from typing import Dict, List
from bs4 import BeautifulSoup as BS
import json
from datetime import date
from selenium import webdriver
from urllib.parse import urljoin as urljoin
from urllib3 import disable_warnings
from concurrent.futures import ThreadPoolExecutor

disable_warnings()

proxies = json.load(open("config_.json", "r"))["proxies"]

#helper fuctions
def load_files() -> None: #denne ble dum, finn en bedre løsning
    kommune = json.load(open("kommune.json", "r"))
    innsyn = json.load(open("innsyn.json", "r"))
    done = json.load(open("done.json","r"))
    pdf_log = json.load(open("pdf_log.json", "r"))
    pdf_crawl= json.load(open("pdf_crawl.json", "r"))
    sendt = json.load(open("sendt.json", "r"))
    pdf_set = json.load(open("pdf_set.json","r"))
    mote_set= json.load(open("mote_set.json","r"))
    kommuneliste= json.load(open("kommuneliste.json","r"))
    standard_kommune = json.load(open("standard_kommune.json","r"))
    nonstandard_kommune = json.load(open("nonstandard_kommune.json","r"))


def thisday() -> str:
    now = date.today()
    return (f"{now.day}-{now.month}-{now.year}")
           
# start Class

class PdfError(LookupError):
    '''raise this when there's a pdf error for my app'''


class Kommune:

    def __init__(self, url: str, name: str = None) -> None:
        self.name: str = name
        self.url: str = url
        self.regex2: str = r"https?:[\/\/].+[\/]"
        self.regex: str = r"^https?:\/\/[^\/]+"
        self.base: str = (re.search(self.regex, self.url).group())
        self.base2: str = (re.search(self.regex2, self.url).group())        
        self.pdf: str = None
        self.type: str = None
        self.bank: list = ["Kommunal garanti", "Kommunal kausjon",
                           "Kommunalgaranti", "Kommunalkausjon",
                           "Simpel garanti ", "Simpel kausjon",
                           "Simpelgaranti", "Simpelkausjon",
                           "Selvskyldnergaranti", "Selvskyldner garanti",
                           "Selvskyldner kausjon", "Selvskyldnerkausjon",
                           "Lån ", "Lån.", "Lån,", "Gjeld ", "Gjeld.", 
                           "Gjeld,", "Lånepapir", "Lånedokument", "Gjeldsgrad",
                           "Gjeldsandel", "Avdrag"]
        self.pensjon: list =["pensjonsordning", "pensjon", "tjenestepensjon", "innskuddspensjon",
                             "hybridpensjon", "pensjonsleverandør", "AFP", "Ny pensjonsordning", 
                             "ny pensjon"]
        self.treff: list =[]
        self.pdf_log: dict = {}
        try:
            self.pdf_log: dict = json.load(open("pdf_log.json", "r"))
        except FileNotFoundError:
            self.pdf_log: dict = {}

    def __str__(self) -> str:
        representation = f"""
            {self.name} kommune
            url = {self.url}
            base = {self.base}
            pdf = {self.pdf} pdf'er
            type = {self.type}"""
        return representation

    def geturl(self, url: str = None, re: int = 3) -> requests.models.Response:
        """gets url with proxysettings and returnes response"""
        if not url:
            url = self.url
            tries = 1
            while tries <= re:
                time.sleep(2)
                resp = requests.get(str(url), proxies=proxies, verify=False)
                if str(resp) == "<Response [200]>":
                    return resp
                i += 1
            return resp

    def get_html_selenium(self, url: str = None) -> str:
        """Gets html and returnes using a chromium instance"""
        if not url:
            url = self.url
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(chrome_options=options)
        driver.get(url)
        accordion = driver.find_elements_by_class_name("accordion")
        #open all accordions
        if len(accordion) > 0:
            for i in accordion:
                try:
                    i.click()
                except:
                    pass
        html = driver.page_source
        return html

    def get_pdf(self, url: str = None) -> None:
        """Saves pdf from url"""
        try:
            resp = self.geturl(url)
            if str(resp) == "<Response [200]>":
                with open("temp.pdf", "wb") as file:
                    file.write(resp.content)
            else:
                self.pdf_log[url] = [str(resp,)+ "No pdf"]
                raise PdfError("no pdf found")
        except Exception as E:
            return E

    def read_pdf(self):
        """uses pdftotext comandline to convert to text"""
        os.system("pdftotext temp.pdf")
        with open("temp.txt", "r") as f:
            tekst = f.read()
        return tekst

    def get_html_selenium(self, url: str = None) -> str:

        """Gets url and returnes html using a chromium instance, assumes
        Chrome driver is pressent in path or in execution folder"""

        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(chrome_options=options)
        driver.get(url)
        time.sleep(2) #wait for xhr
        accordion = driver.find_elements_by_class_name("accordion")
        #open accordions if pressent
        if len(accordion) > 0:
            for i in accordion:
                try:
                    i.click()
                except:
                    pass
        html = driver.page_source
        driver.quit()
        return (html, url)

    # def find_hits(self, url=None) -> Dict:
    #     """Iterates over all pdf's and returnes a dictionary of link and
    #     keyword when bank-words are pressent in the pdf"""
    #     try:
    #         if not url:
    #             url = self.url
    #         if "//" in str(pdf_crawl[self.base][0]):
    #             for i in self.get_moter_selenium():
    #                 try:
    #                     for y in self.findPDFSel(i):
    #                         if str(y) in self.pdf_log:
    #                             #print("passing")
    #                             pass
    #                         else:
    #                             doc = self.get_pdf(y)
    #                             if doc == "no pdf found":
    #                                 self.pdf_log.setdefault(str(y), ["0",
    #                                                                 "no pdf error"])
    #                             else:
    #                                 self.pdf_log.setdefault(str(y), ["0"])
    #                                 tekst = self.read_pdf()
    #                                 for s in self.bank:
    #                                     if s.lower() in tekst.lower():
    #                                         self.pdf_log[str(y)][0] = "1"
    #                                         self.pdf_log[str(y)].append(s)
    #                 except:
    #                     with open("pdf_log.json", "w") as f:
    #                         json.dump(self.pdf_log, f)
    #         else:
    #             for i in self.getMoter():
    #                 try:
    #                     for y in self.findPDF(i):
    #                         if str(y) in self.pdf_log:
    #                            # print("passing")
    #                             pass
    #                         else:
    #                             if self.get_pdf(y) == "no pdf found":
    #                                 self.pdf_log.setdefault(str(y),
    #                                                        ["0",
    #                                                         "no pdf error"])
    #                             else:
    #                                 self.get_pdf(y)
    #                                 self.pdf_log.setdefault(str(y), ["0"])
    #                                 tekst = self.read_pdf()
    #                                 for s in self.bank:
    #                                     if s.lower() in tekst.lower():
    #                                         self.pdf_log[str(y)][0] = "1"
    #                                         self.pdf_log[str(y)].append(s)
    #                 except:
    #                     with open("pdf_log.json", "w") as f:
    #                         json.dump(self.pdf_log, f)
                       
    #         with open("pdf_log.json", "w") as f:
    #                 json.dump(self.pdf_log, f)
    #     except Exception as E:
    #         with open("pdf_log.json", "w") as f:
    #                         json.dump(self.pdf_log, f)
    #         print(E)
    #     if not url:
    #         url = self.url
    #     # if self.type == "einnsyn":
    #     if "//" in str(pdf_crawl[self.base][0]):
    #         for i in self.get_moter_selenium():
    #             try:
    #                 for y in self.findPDFSel(i):
    # #                    if "http" not in y:
    # #                        y = self.base+y
    # #                    if "http" not in y and "document.ashx" in y:
    # #                        y = self.base2+y
    #                     print(f"møte {i}, sak {y}")
    #                     if str(y) in self.pdf_log:
    #                         pass
    #                     else:
    #                         if self.get_pdf(y) == "no pdf found":
    #                             self.pdf_log.setdefault(str(y), ["0",
    #                                                             "no pdf error"])
    #                         else:
    #                             self.get_pdf(y)
    #                             self.pdf_log.setdefault(str(y), ["0"])
    #                             tekst = self.read_pdf()
    #                             for s in self.bank:
    #                                 if s.lower() in tekst.lower():
    #                                     self.pdf_log[str(y)][0] = "1"
    #                                     self.pdf_log[str(y)].append(s)
    #                                     print(i, s)
    #             except:
    #                 with open("pdf_log.json", "w") as f:
    #                     json.dump(self.pdf_log, f)
    #     else:
    #         for i in self.getMoter():
    #             try:
    #                 for y in self.findPDF(i):
    # #                    if "http" not in y:
    # #                        y = self.base+y
    # #                    if "http" not in y and "document.ashx" in y:
    # #                        y = self.base2+y
    #                     print(f"møte {i}, sak {y}")
    #                     if str(y) in self.pdf_log:
    #                         pass
    #                     else:
    #                         if self.get_pdf(y) == "no pdf found":
    #                             self.pdf_log.setdefault(str(y), ["0",
    #                                                             "no pdf error"])
    #                         else:
    #                             self.get_pdf(y)
    #                             self.pdf_log.setdefault(str(y), ["0"])
    #                             tekst = self.read_pdf()
    #                             for s in self.bank:
    #                                 if s.lower() in tekst.lower():
    #                                     self.pdf_log[str(y)][0] = "1"
    #                                     self.pdf_log[str(y)].append(s)
    #                                     print(i, s)
    #             except:
    #                 with open("pdf_log.json", "w") as f:
    #                     json.dump(self.pdf_log, f)
    #     with open("pdf_log.json", "w") as f:
    #             json.dump(self.pdf_log, f)


    # def getMoter(self) -> list:
    #     if pdf_crawl[self.base][0] is None:
    #         return [self.url]
    #     else:
    #         """Finds all meetings on meeting calender site and returnes them as a list"""
    #         resp: requests.models.Response = self.geturl()
    #         links: list = BS(self.geturl().content, "lxml").findAll("a", href=True)
    #         meetings: list = [urljoin(resp.url, a.get("href")) for a in links if
    #                           pdf_crawl[self.base][0].lower() in
    #                           a.get("href").lower()]
    #         return meetings


    def get_moter_selenium(self):
        if pdf_crawl[self.base][0] is None:
            return [None]
        else:
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            options.add_argument('--window-size=1920,1080')
            driver = webdriver.Chrome(chrome_options=options)
            driver.get(self.url)
            time.sleep(1)
            td = driver.find_elements_by_xpath(str(pdf_crawl[self.base][0]))
            ids = []
            if "prokomresources" in self.base:
                meetings: list = [i.get_attribute("href") for i in td]
                driver.quit()
                return meetings
            else:
                # remove this for loop to get all commities
                for i in td:
                    # ---
                    try:
                        ids.append(i.find_element_by_class_name("fc-content"))
                    except:
                        pass
                meetings: list = [self.url + "motedag?offmoteid=" +
                                  i.get_attribute("id") for i in ids]
                driver.quit()
                return meetings 

    # def finn_treff(self):
    #     self.treff =  []
    #     for i in pdf_log.keys():
    #         if pdf_log[i][0] == "1" and i not in sendt:
    #             #print(i)
    #             self.treff.append([i, pdf_log[i]])

    # def finn_treff(self):
    #     """Itterates over pdf_log and returnes those that have hits
    #     and are not present in sendt"""
    #     treff =  []
    #     for i in self.pdf_log.keys():
    #         if self.pdf_log[i][0] == "1" and i not in sendt:
    #             treff.append([i, pdf_log[i]])
    #     return treff

    # def print_treff(self, file: list):
    #     """exports file to csv"""
    #     with open(f"kommune{thisday()}.csv","w") as f:
    #         write = csv.writer(f)
    #         write.writerows(file)

    # def add_to_sendt(self, file: list):
    #     """adds list to sendt"""
    #     for pdf_link in file:
    #     if pdf_link[0] not in self.sendt:
    #         self.sendt.append(i[0])


def get_url(url: str = None, re: int = 3) -> requests.models.Response:

        """gets url with proxysettings and returnes response
        retries 're' times """
        times = 0
        while times <= re:
            time.sleep(2)
            resp = requests.get(str(url), proxies=proxies, verify=False)
            if str(resp) == "<Response [200]>":
                return resp
            times += 1
        return resp


def get_html_selenium(url: str = None) -> str:
        
        """Gets html and returnes html using a chromium instance"""
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(chrome_options=options)
        driver.get(url)
        time.sleep(2) #wait for xhr
        accordion = driver.find_elements_by_class_name("accordion")
        #open accordions if pressent
        if len(accordion) > 0:
            for i in accordion:
                try:
                    i.click()
                except:
                    pass
        html = driver.page_source
        driver.quit()
        return (html, url)

def get_mote_url(resp: BS) -> list:
    elements: list = BS(resp.content, "lxml").findAll("a", href=True)
    links: list = [urljoin(resp.url, a.get("href")) for a in elements]
    return links

def get_all_urls(html: str, url: str) -> list:
    """Returnes all links from given html-string
    
    url is used to join relative links to absolute liks
    """
    
    soup = BS(html, "lxml")
    divs = soup.findAll("div", class_="fc-content")
    if len(divs) > 0:
        links: list = []
    # This is the standard way of getting the urls the if statements above
    # are to catch som of the weird javascript envoked links
    elements: list = soup.findAll("a", href=True)
    links: list = [urljoin(url, a.get("href")) for a in elements]
    return links

def get_pdf(links: list) -> list:
    "Get all links if they match any string in pdf_set"
    pdfs: list = [link for link in links if sjekk_pdf_url(link)]
    return pdfs

def sjekk_mote_url(url: str) -> list:
    """Checks @param url for any match in mote_set returns bolean"""
    return any(sub in url for sub in mote_set)

def sjekk_pdf_url(url: str) -> list:
    """Checks url for any match in pdf_set returns bolean"""
    return any(sub in url for sub in pdf_set)

def find_non_standard_kommune():
    """Iterates over kommuneliste and returns a list of
    all that does not pass the sjekk_mote_url check"""
    non_standard_kommune = []
    for kommune in kommuneliste:
        try:
            moter = get_mote_url(get_url(kommune[-1]))
            if any([sjekk_mote_url(mote) for mote in moter]):
                pass
            else:
                non_standard_kommune.append(kommune)
        except Exception as e:
            print(kommune[-1])
            non_standard_kommune.append(kommune)
    return non_standard_kommune



def kjor() -> None:
    for line in kommune:
        if "http" in kommune[line][2]:
            a=Kommune(kommune[line][2], line)
            a.find_hits()


def finn_treff():
    """Itterates over pdf_log and returnes those that have hits
    and are not present in sendt"""
    treff =  []
    for i in pdf_log.keys():
        if pdf_log[i][0] == "1" and i not in sendt:
            #print(i)
            treff.append([i, pdf_log[i]])
    return treff


def add_to_sendt(file: list):
    """adds list to sendt"""
    for pdf_link in file:
       if pdf_link[0] not in sendt:
           sendt.append(i[0])


def print_treff(file: list):
    """exports file to csv"""
    with open(f"kommune{thisday()}.csv","w") as f:
        write = csv.writer(f)
        write.writerows(file)


def save():
    """Saves all logs to disk"""
    json.dump(pdf_crawl, open("pdf_crawl.json","w"))
    json.dump(sendt, open("sendt.json","w"))
    json.dump(pdf_log, open("pdf_log.json","w"))
    json.dump(kommune, open("kommune.json","w"))
    json.dump(done, open("done.json","w"))
    json.dump(innsyn, open("innsyn.json","w"))
    json.dump(pdf_set, open("pdf_set.json","w"))
    json.dump(mote_set, open("mote_set.json","w"))
    json.dump(standard_kommune, open("standard_kommune.json","w"))
    json.dump(nonstandard_kommune, open("nonstandard_kommune.json","w"))


