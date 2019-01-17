# -*- coding: utf-8 -*-
"""
Created on Tue Jul 17 14:21:32 2018

@author: Bendik Knapstad
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
import urllib.parse
import _pickle
from urllib3 import disable_warnings

from concurrent.futures import ThreadPoolExecutor



disable_warnings()
proxies = json.load(open("config_.json", "r"))["proxies"]


# helper funtions
#ndriv = webdriver.Chrome()
kommune = json.load(open("kommune.json", "r"))
innsyn = json.load(open("innsyn.json", "r"))
done = json.load(open("done.json","r"))
pdfLog = json.load(open("pdfLog.json", "r"))
pdfCrawl= json.load(open("pdfCrawl.json", "r"))
sendt = json.load(open("sendt.json", "r"))
pdf_set = json.load(open("pdf_set.json","r"))
mote_set= json.load(open("mote_set.json","r"))
kommuneliste= json.load(open("kommuneliste.json","r"))
#with open('behandlede_kommuner.pickle', 'rb') as handle:
#    behandlede_kommuner = _pickle.load(handle)

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
        self.cash: list = ["Kommunal garanti", "Kommunal kausjon",
                           "Kommunalgaranti", "Kommunalkausjon",
                           "Simpel garanti ", "Simpel kausjon",
                           "Simpelgaranti", "Simpelkausjon",
                           "Selvskyldnergaranti", "Selvskyldner garanti",
                           "Selvskyldner kausjon", "Selvskyldnerkausjon",
                           "Lån ", "Lån.", "Lån,", "Gjeld ", "Gjeld.", 
                           "Gjeld,", "Lånepapir", "Lånedokument", "Gjeldsgrad",
                           "Gjeldsandel", "Avdrag"]
        self.treff=[]
        self.pdfLog: dict = {}
        
        try:
            self.pdfLog: dict = json.load(open("pdfLog.json", "r"))
        except FileNotFoundError:
            self.pdfLog: dict = {}

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
        resp = requests.get(str(url), proxies=proxies, verify=False)
        if str(resp) == "<Response [200]>":
            return resp
        else:
            i = 1
            while i < re + 1:
                time.sleep(2)
                resp = requests.get(str(url), proxies=proxies, verify=False)
                if str(resp) == "<Response [200]>":
                    return resp
                i += 1
            return resp

    def get_html_selenium(self, url: str = None) -> str:
        if not url:
            url = self.url
        """Gets html and returnes using a chromium instance"""
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

    def findPDFSel(self, url: str = None) -> List:
        if not url:
            url = self.url
        """Finds all pdfs on site and returnes them as a list"""
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(chrome_options=options)
        driver.get(url)
        time.sleep(1)
        links: list = driver.find_elements_by_xpath(pdfCrawl[self.base][1])
        pdf: list = [i.get_attribute("href") for i in links]
        return pdf

    def findPDF(self, url: str = None) -> List:
        if not url:
            url = self.url
        if "https://" not in url.lower() and "http://" not in url.lower():
            url = self.base + url
        if "https://" not in url.lower() and "http://" not in url.lower() and \
        "innsyn.e-kommne" in url.lower():
            url =self.base2 + url    
        resp: requests.models.Response = self.geturl(url)
        if str(resp) == "<Response [200]>":
            links: list = BS(self.geturl(url).text, "lxml").findAll("a",
                                                                    href=True)
            pdf: list = [urllib.parse.urljoin(resp.url, a.get("href")) for a in links if ".pdf"
                         in a.get("href").lower() or pdfCrawl[self.base][1]
                             .lower()
                         in a.get("href").lower()]
            if not self.pdf:
                self.pdf = str(len(pdf))
            else:
                self.pdf = str(int(self.pdf) + len(pdf))
        else:
            pdf: list = [str(url), str(resp)]
        return pdf

    def getPDF(self, url: str = None) -> None:
        """Saves pdf from url"""
        if not url:
            url = self.url
              
        if "https://" not in url.lower() and "http://" not in url.lower() and \
                        "document.ash" in url.lower():
            url =self.base2 + url

        if "https://" not in url.lower() and "http://" not in url.lower():
            url = self.base + url
       
        try:
            resp = self.geturl(url)
            if str(resp) == "<Response [200]>":
                with open("temp.pdf", "wb") as file:
                    file.write(resp.content)
            else:
                self.pdfLog[url] = [str(resp,)+ "No pdf"]
                raise PdfError("no pdf found")
        except Exception as E:
            print(str(E))
            return E

    def readPDF(self):
        """uses pdftotext comandline to convert to text"""
        os.system("pdftotext temp.pdf")
        with open("temp.txt", "r") as f:
            tekst = f.read()
        return tekst

    def findcash(self, url=None) -> Dict:
        """Iterates over all pdf's and returnes a dictionary of link and
        keyword when cash-words are pressent in the pdf"""
        try:
            if not url:
                url = self.url
            if "//" in str(pdfCrawl[self.base][0]):
                for i in self.getMoterSel():
                    try:
                        for y in self.findPDFSel(i):
                            if str(y) in self.pdfLog:
                                #print("passing")
                                pass
                            else:
                                doc = self.getPDF(y)
                                if doc == "no pdf found":
                                    self.pdfLog.setdefault(str(y), ["0",
                                                                    "no pdf error"])
                                else:
                                    self.pdfLog.setdefault(str(y), ["0"])
                                    tekst = self.readPDF()
                                    for s in self.cash:
                                        if s.lower() in tekst.lower():
                                            self.pdfLog[str(y)][0] = "1"
                                            self.pdfLog[str(y)].append(s)
                    except:
                        with open("PdfLog.json", "w") as f:
                            json.dump(self.pdfLog, f)
            else:
                for i in self.getMoter():
                    try:
                        for y in self.findPDF(i):
                            if str(y) in self.pdfLog:
                               # print("passing")
                                pass
                            else:
                                if self.getPDF(y) == "no pdf found":
                                    self.pdfLog.setdefault(str(y),
                                                           ["0",
                                                            "no pdf error"])
                                else:
                                    self.getPDF(y)
                                    self.pdfLog.setdefault(str(y), ["0"])
                                    tekst = self.readPDF()
                                    for s in self.cash:
                                        if s.lower() in tekst.lower():
                                            self.pdfLog[str(y)][0] = "1"
                                            self.pdfLog[str(y)].append(s)
                    except:
                        with open("PdfLog.json", "w") as f:
                            json.dump(self.pdfLog, f)
                       
            with open("PdfLog.json", "w") as f:
                    json.dump(self.pdfLog, f)
        except Exception as E:
            with open("PdfLog.json", "w") as f:
                            json.dump(self.pdfLog, f)
            print(E)
        if not url:
            url = self.url
        # if self.type == "einnsyn":
        if "//" in str(pdfCrawl[self.base][0]):
            for i in self.getMoterSel():
                try:
                    for y in self.findPDFSel(i):
    #                    if "http" not in y:
    #                        y = self.base+y
    #                    if "http" not in y and "document.ashx" in y:
    #                        y = self.base2+y
                        print(f"møte {i}, sak {y}")
                        if str(y) in self.pdfLog:
                            pass
                        else:
                            if self.getPDF(y) == "no pdf found":
                                self.pdfLog.setdefault(str(y), ["0",
                                                                "no pdf error"])
                            else:
                                self.getPDF(y)
                                self.pdfLog.setdefault(str(y), ["0"])
                                tekst = self.readPDF()
                                for s in self.cash:
                                    if s.lower() in tekst.lower():
                                        self.pdfLog[str(y)][0] = "1"
                                        self.pdfLog[str(y)].append(s)
                                        print(i, s)
                except:
                    with open("PdfLog.json", "w") as f:
                        json.dump(self.pdfLog, f)
        else:
            for i in self.getMoter():
                try:
                    for y in self.findPDF(i):
    #                    if "http" not in y:
    #                        y = self.base+y
    #                    if "http" not in y and "document.ashx" in y:
    #                        y = self.base2+y
                        print(f"møte {i}, sak {y}")
                        if str(y) in self.pdfLog:
                            pass
                        else:
                            if self.getPDF(y) == "no pdf found":
                                self.pdfLog.setdefault(str(y), ["0",
                                                                "no pdf error"])
                            else:
                                self.getPDF(y)
                                self.pdfLog.setdefault(str(y), ["0"])
                                tekst = self.readPDF()
                                for s in self.cash:
                                    if s.lower() in tekst.lower():
                                        self.pdfLog[str(y)][0] = "1"
                                        self.pdfLog[str(y)].append(s)
                                        print(i, s)
                except:
                    with open("PdfLog.json", "w") as f:
                        json.dump(self.pdfLog, f)
        with open("PdfLog.json", "w") as f:
                json.dump(self.pdfLog, f)


    def getMoter(self):
        if pdfCrawl[self.base][0] is None:
            return [self.url]
        else:
            """Finds all meetings on meeting calender site and returnes them as a list"""
            resp: requests.models.Response = self.geturl()
            links: list = BS(self.geturl().content, "lxml").findAll("a", href=True)
            meetings: list = [urllib.parse.urljoin(resp.url, a.get("href")) for a in links if
                              pdfCrawl[self.base][0].lower() in
                              a.get("href").lower()]
            return meetings


    def getMoterSel(self):
        if pdfCrawl[self.base][0] is None:
            return [None]
        else:
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            options.add_argument('--window-size=1920,1080')
            driver = webdriver.Chrome(chrome_options=options)
            driver.get(self.url)
            time.sleep(1)
            td = driver.find_elements_by_xpath(str(pdfCrawl[self.base][0]))
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


    def finn_treff(self):
        self.treff =  []
        for i in pdfLog.keys():
            if pdfLog[i][0] == "1" and i not in sendt:
                #print(i)
                self.treff.append([i, pdfLog[i]])


def get_url(url: str = None, re: int = 3) -> requests.models.Response:

        """gets url with proxysettings and returnes response
        retries 're' times """
        try:
            resp = requests.get(str(url), proxies=proxies, verify=False)
        except:
            resp = None
            if str(resp) == "<Response [200]>":
                return resp
            else:
                i = 0
                while i < re:
                    time.sleep(2)
                    try:
                         resp = requests.get(str(url), proxies=proxies, verify=False)
                    except:
                        resp = None
                    if str(resp) == "<Response [200]>":
                        return resp
                    i += 1
                return resp

def get_html_selenium(url: str = None) -> str:
        
        """Gets html and returnes html using a chromium instance"""
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

def get_mote_url(resp: BS) -> list:
    elements: list = BS(resp.content, "html").findAll("a", href=True)
    links: list = [urllib.parse.urljoin(resp.url, a.get("href")) for a in elements]
    return links

def get_all_urls(html: str) -> list:
    """Returned all links from given html-string
     """
    soup = BS(html, "lxml")
    divs = soup.findAll("div", class_="fc-content")
    if len(divs) > 0:
        links: list = []
    # This is the standard way of getting the urls the ifstatements above
    # are to catch the exceptions and the weird javascript envoked links
    elements: list = soup.findAll("a", href=True)
    links: list = [a.get("href") for a in elements] #Todo remember to add base url
    return links

def get_pdf(links: list) -> list:
    pdfs: list = [link for link in links if sjekk_pdf_url(link)]
    return pdfs

def sjekk_mote_url(url: str) -> list:
    return any(sub in url for sub in mote_set)

def sjekk_pdf_url(url: str) -> list:
    return any(sub in url for sub in pdf_set)

def find_non_standard_kommune():
    non_standard_kommune = []
    for kommune in kommuneliste:
        moter = get_mote_url(kommune[-1])
        if any([sjekk_mote_url(mote) for mote in moter]):
            pass
        else:
            non_standard_kommune.append(kommune)
    return non_standard_kommune
            


def kjor() -> None:
    for i in kommune:
        if "http" in kommune[i][2]:
            a=Kommune(kommune[i][2], i)
            a.findcash()
            a.finn_treff()


def finn_treff():
    treff =  []
    for i in pdfLog.keys():
        if pdfLog[i][0] == "1" and i not in sendt:
            #print(i)
            treff.append([i, pdfLog[i]])
    return treff


def add_to_sendt(file):
   for i in file:
       if i[0] not in sendt:
           sendt.append(i[0])


def print_treff(file):
    with open(f"kommune{thisday()}.csv","w") as f:
        write = csv.writer(f)
        write.writerows(file)


def save():
        json.dump(pdfCrawl, open("pdfCrawl.json","w"))
        json.dump(sendt, open("sendt.json","w"))
        json.dump(pdfLog, open("pdfLog.json","w"))
        json.dump(kommune, open("kommune.json","w"))
        json.dump(pdfCrawl, open("pdfCrawl.json","w"))
        json.dump(pdfCrawl, open("pdfCrawl.json","w"))
        json.dump(done, open("done.json","w"))
        json.dump(innsyn, open("innsyn.json","w"))
        json.dump(pdf_set, open("pdf_set.json","w"))
        json.dump(mote_set, open("mote_set.json","w"))
