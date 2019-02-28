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
import json
import logging
import sys
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup as BS
from requests import Response
from datetime import date
from selenium import webdriver
from urllib.parse import urljoin as urljoin
from urllib3 import disable_warnings
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

def thisday() -> str:
    now = date.today()
    return (f"{now.day}-{now.month}-{now.year}")

logging.basicConfig(level=logging.DEBUG, filename=f"file/logs/{thisday()}KommuneLog.log", filemode="w", format="%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s")
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s")
inf = logging.FileHandler(f"file/logs/{thisday()}InfoKommuneLog.log")
err = logging.FileHandler(f"file/logs/{thisday()}ErrorKommuneLog.log")
inf.setLevel(logging.INFO)
err.setLevel(logging.ERROR)
inf.setFormatter(formatter)
err.setFormatter(formatter)
logger.addHandler(err)
logger.addHandler(inf)
disable_warnings()

try:
    logger.info("Loading Proxie settings")
    proxies = json.load(open("file/config_.json", "r"))["proxies"]
except FileNotFoundError:
    logger.exception("config_.json needs to be pressent in 'working directory/file'", exc_info=True)

#helper fuctions
# kommune = json.load(open("file/data/kommune.json", "r"))
# pdf_log = json.load(open("file/data/pdf_log.json", "r"))
# sendt = json.load(open("file/data/sendt.json", "r"))
# pdf_set = json.load(open("file/data/pdf_set.json","r"))
# mote_set = json.load(open("file/data/mote_set.json","r"))
# kommuneliste = json.load(open("file/data/kommuneliste.json","r"))
# standard_kommune = json.load(open("file/data/standard_kommune.json","r"))
# nonstandard_kommune = json.load(open("file/data/nonstandard_kommune.json","r"))
# direct_kommune = json.load(open("file/data/direct_kommune.json","r"))


# start Class

class PdfError(LookupError):
    '''raise this when there's a pdf error for my app'''


class Kommune:

    def __init__(self, url: str, name: str = None) -> None:
        logger.info(f"Initsiating kommume {name}")
        self.name = name
        self.url = url
        self.pdf: Optional[str] = None
        self.type: Optional[str] = None
        self.bank: list = ["Kommunal garanti", "Kommunal kausjon",
                           "Kommunalgaranti", "Kommunalkausjon",
                           "Simpel garanti ", "Simpel kausjon",
                           "Simpelgaranti", "Simpelkausjon",
                           "Selvskyldnergaranti", "Selvskyldner garanti",
                           "Selvskyldner kausjon", "Selvskyldnerkausjon",
                           "Lån ", "Lån.", "Lån,", "Gjeld ", "Gjeld.", 
                           "Gjeld,", "Lånepapir", "Lånedokument", "Gjeldsgrad",
                           "Gjeldsandel", "Avdrag"]
        self.pensjon: list =["pensjonsordning", "pensjon", "tjenestepensjon",
                             "innskuddspensjon", "hybridpensjon", 
                             "pensjonsleverandør", "AFP", "Ny pensjonsordning", 
                             "ny pensjon"]
        self.treff: list =[]
        self.pdf_log: dict = {}
        try:
            self.pdf_log: dict = json.load(open("file/data/pdf_log.json", "r"))
        except FileNotFoundError:
            logger.info("no pdf log file found")
            self.pdf_log: dict = {}
        try:
            self.pdf_set: list = json.load(open("file/data/pdf_set.json","r"))
        except FileNotFoundError:
            logger.info("pdf_set.json needs to be pressent in working directory")
        try:
            self.mote_set: list = json.load(open("file/data/mote_set.json","r"))
        except FileNotFoundError:
            logger.info("mote_set.json needs to be pressent in working directory")

    def __str__(self) -> str:
        representation = f"""
            {self.name} kommune
            url = {self.url}
            pdf = {self.pdf} pdf'er
            type = {self.type}"""
        return representation

    def get_url(self, url: str = None, re: int = 3) -> Response:
        """gets url with proxysettings and returnes response"""
        try:
            if url is None:
                url = self.url
            tries: int = 1
            while tries <= re:
                time.sleep(2)
                resp = requests.get(str(url), proxies=proxies, verify=False)
                if str(resp) == "<Response [200]>":
                    return resp
                tries += 1
            return resp
        except Exception as e:
            logger.exception(f"{url}, error: {e}")
            return None

    def get_html_selenium(self, url: str = None) -> str:
        """Gets and returnes html as a string using a chromium instance"""
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
        logger.info(f"Starting get pdf: {url}")
        try:
            resp = self.get_url(url=url)
            if str(resp) == "<Response [200]>":
                with open("file/pdf/temp.pdf", "wb") as file:
                    file.write(resp.content)
            else:
                self.pdf_log[url]["Bank"] = [str(resp,)+ "No pdf"]
                self.pdf_log[url]["Pensjon"] = [str(resp,)+ "No pdf"]
                raise PdfError("no pdf found")
        except Exception as E:
            logger.exception(f"{E}")

    def read_pdf(self) -> str:
        """Uses pdftotext comandline to convert to text
        returnes text"""
        logger.info(f"Reading pdf")
        os.system("pdftotext file/pdf/temp.pdf")
        with open("file/pdf/temp.txt", "r") as f:
            tekst = f.read()
        return tekst

    def find_hits_bank(self, pdf_url: str)-> None:
        """Finds banking word in textconverted pdf via self.read_pdf()
            logs findings to self.pdf_log"""
        logger.info("Setting default")
        self.pdf_log.setdefault(pdf_url,{"Bank": [0], "Pensjon": [0]})
        try:
            tekst = self.read_pdf()
            for word in self.bank:
                if word.lower() in tekst.lower():
                    logger.info(f"found hit {word}")
                    self.pdf_log[pdf_url]["Bank"][0]=1
                    self.pdf_log[pdf_url]["Bank"].append(word)
                    logger.info(f"{self.pdf_log[pdf_url]["Bank"].append(word)}")
        except Exception as e:
            logger.exception("Bankhits error: ")
            self.pdf_log[pdf_url]["Bank"]=[0, e]

    def find_hits_pensjon(self, pdf_url: str)-> None:
        """Finds pensjons words in text-converted pdf via self.read_pdf()"""
        logger.info("Setting default")
        self.pdf_log.setdefault(pdf_url,{"Bank": [0], "Pensjon": [0]})
        try:
            tekst = self.read_pdf()
            for word in self.pensjon:
                if word.lower() in tekst.lower():
                    logger.info(f"found hit {word}")
                    self.pdf_log[pdf_url]["Pensjon"][0]=1
                    self.pdf_log[pdf_url]["Pensjon"].append(word)
                    logger.info(f"{self.pdf_log[pdf_url]["Bank"].append(word)}")
        except Exception as e:
            logger.exception("Pensjonhits error: ")
            self.pdf_log[pdf_url]["Pensjon"]=[0, e]

    def get_mote_url(self, resp: BS) -> list:
        """Asumes resp is a url with list of standard meetings,
        @returnes: list of links""" 
        logger.info(f"Getting møte urls {self.name} : {resp.url}")
        elements: list = BS(resp.content, "lxml").findAll("a", href=True)
        links: list = [urljoin(resp.url, a.get("href")) for a in elements if sjekk_mote_url(urljoin(resp.url, a.get("href")))]
        return links

    def get_pdf_url(self, resp: BS) -> list:
        """Assumes resp is a meeting url, @returnes all pdf urls form resp"""
        logger.info(f"Getting pdf urls {self.name}: {resp.url}")
        elements: list = BS(resp.content, "lxml").findAll("a", href=True)
        links: list = [urljoin(resp.url, a.get("href")) for a in elements if sjekk_pdf_url(urljoin(resp.url, a.get("href")))]
        logger.info(f"Returning pdf urls {links}")
        return links

def get_url(url: str = None, re: int = 3) -> Response:
        """gets url with proxysettings and returnes response
        retries 're' times """
        logger.info(f"Getting url {url}")
        times = 0
        while times <= re:
            time.sleep(2)
            resp = requests.get(str(url), proxies=proxies, verify=False)
            if str(resp) == "<Response [200]>":
                return resp
            times += 1
        return resp


def get_html_selenium(url: str) -> Tuple[str, str]:
        """Gets and returnes html using a chromium instance"""
        logger.info(f"Starting chromium instance")
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(chrome_options=options)
        logger.info(f"Getting url: {url}")
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
        logger.info("Closing chromium instance")
        driver.quit()
        return (html, url)

def get_mote_url(resp: requests.models.Response) -> list:
    elements: list = BS(resp.content, "lxml").findAll("a", href=True)
    links: list = [urljoin(resp.url, a.get("href")) for a in elements if sjekk_mote_url(urljoin(resp.url, a.get("href")))]
    return links

def get_all_urls(html: str, url: str) -> list:
    """Returnes all links from given html-string
    url is used to join relative links to absolute links
    """
    soup = BS(html, "lxml")
    # divs = soup.findAll("div", class_="fc-content")
    elements: list = soup.findAll("a", href=True)
    links: list = [urljoin(url, a.get("href")) for a in elements]
    return links

def get_pdf_urls(links: list) -> list:
    "Get all links if they match any string in pdf_set"
    pdfs: list = [link for link in links if sjekk_pdf_url(link)]
    return pdfs

def sjekk_mote_url(url: str) -> bool:
    """Checks @param url for any match in mote_set returns bolean"""
    return any([sub in url for sub in mote_set])

def sjekk_pdf_url(url: str) -> bool:
    """Checks url for any match in pdf_set returns bolean"""
    return any(sub in url for sub in pdf_set)

def find_non_standard_kommune() -> list:
    """Iterates over kommuneliste and returns a list of
    all that does not pass the sjekk_mote_url check"""
    try:
        #checks if kommuneliste exists
        kommuneliste
    except NameError as e:
        #loads from json if not
        kommuneliste = json.load(open("file/data/kommuneliste.json","r"))
    non_standard_kommune = []
    for kommune in kommuneliste:
        try:
            moter = get_mote_url(get_url(kommune[-1]))
            if any([sjekk_mote_url(mote) for mote in moter]):
                pass
            else:
                non_standard_kommune.append(kommune)
        except Exception as e:
            logger.exception(f"{kommune[-1]}, {e}")
            non_standard_kommune.append(kommune)
    return non_standard_kommune



def kjor_kommune(kommune_url: str, kommune_name: str = None) -> None:
    """Takes kommune_url and kommune_name finds kommune pdfs
    updates pdf_log with new findings and saves to pdf_log.json"""

    logger.info(f"Starting kjor_kommune")
    kommune: Kommune = Kommune(url=kommune_url, name=kommune_name)
    mote_response  = kommune.get_url()
    moter: list = kommune.get_mote_url(resp=mote_response)
    logger.info(f"Møter length: {len(moter)}")
    pdfs = []
    for url in tqdm(moter, desc=f"Møter {kommune.name}: "):
        logger.info(f"Getting from : {len(pdfs)}")
        pdf_response = kommune.get_url(url=url)
        pdfs += kommune.get_pdf_url(resp=pdf_response)
        
        logger.info(f"{pdfs}")    
    for pdf in tqdm(pdfs, desc=f"Pdfs {kommune.name}: "):
        kommune.get_pdf(url=pdf)
        kommune.read_pdf()
        kommune.find_hits_bank(pdf_url=pdf)
        kommune.find_hits_pensjon(pdf_url=pdf)
    pdf_log = json.load(open("file/data/pdf_log.json","r"))
    updated_pdf_log = {**pdf_log, **kommune.pdf_log}
    logger.info("Writing pdf_log")
    logger.info(f"Oldsize: {len(pdf_log)}")
    logger.info(f"Newsize: {len(updated_pdf_log)}")
    json.dump(updated_pdf_log, open("file/data/pdf_log.json","w"))

def kjor_direkte_kommune(kommune_url: str, kommune_name: str = None) -> None: 
    """Takes kommune_url and kommune_name finds kommune pdfs
    updates pdf_log with new findings and saves to pdf_log.json""" 

    logger.info(f"Starting kjor_kommune")
    kommune: Kommune = Kommune(url=kommune_url, name=kommune_name)
    pdf_response  = kommune.get_url()
    pdfs: list = kommune.get_pdf_url(resp=pdf_response)
    try:
        pdfs
    except NameError as e:
        logger.exception(f"Pdf list error, {e}")
        pdfs=[]
    for pdf in tqdm(pdfs, desc=f"Pdfs {kommune.name}:"):
        kommune.get_pdf(url=pdf)
        kommune.read_pdf()
        kommune.find_hits_bank(pdf_url=pdf)
        kommune.find_hits_pensjon(pdf_url=pdf)
    logger.info("Writing pdf_log")
    pdf_log = json.load(open("file/data/pdf_log.json","r"))
    updated_pdf_log = {**pdf_log, **kommune.pdf_log}
    logger.info(f"Oldsize: {len(pdf_log)}")
    logger.info(f"Newsize: {len(updated_pdf_log)}")
    json.dump(updated_pdf_log, open("file/data/pdf_log.json","w"))

def finn_treff() -> list:
    """Itterates over pdf_log and returnes those that have hits
    and are not present in sendt"""

    logger.info("Initiating finn_treff")
    treff =  []
    for i in pdf_log.keys():
        if pdf_log[i][0] != "0" and i not in sendt:
            treff.append([i, pdf_log[i]])
    return treff

def finn_treff_bank() -> list:
    """Iterates over pdf_log and returnes those that have bank hits
    and are not present in sendt"""

    logger.info("Initiating finn_treff_bank")
    treff =  []
    for i in pdf_log.keys():
        if pdf_log[i]["Bank"][0] == "1" and i not in sendt:
            treff.append([i, pdf_log[i]["Bank"]])
    return treff


def finn_treff_pensjon() -> list:
    """Iterates over pdf_log and returnes those that have bank hits
    and are not present in sendt"""

    logger.info("Initiating finn_treff_pensjon")
    treff =  []
    for i in pdf_log.keys():
        if pdf_log[i]["Pensjon"][0] == "1" and i not in sendt:
            treff.append([i, pdf_log[i]])
    return treff

def add_to_sendt(hit_list: list) -> None:
    """adds list to sendt"""
    logger.info("Initiating add_to_sendt")
    for pdf_link in hit_list:
       if pdf_link[0] not in sendt:
           sendt.append(pdf_link[0])


def print_treff_to_file(hit_list: list, name: str = None) -> None:
    """exports hit_list to csv"""

    logger.info("Initiating print_treff_to_file")
    with open(f"file/out/kommune{name}{thisday()}.csv","w") as f:
        write = csv.writer(f)
        write.writerows(hit_list)


def save():
    """Saves all logs to disk"""

    json.dump(sendt, open("file/data/sendt.json","w"))
    json.dump(pdf_log, open("file/data/pdf_log.json","w"))
    json.dump(kommune, open("file/data/kommune.json","w"))
    json.dump(pdf_set, open("file/data/pdf_set.json","w"))
    json.dump(mote_set, open("file/data/mote_set.json","w"))
    json.dump(standard_kommune, open("file/data/standard_kommune.json","w"))
    json.dump(nonstandard_kommune, open("file/data/nonstandard_kommune.json","w"))
    json.dump(direct_kommune, open("file/data/direct_kommune.json","w"))

if __name__=="__main__":
    try:
        logger.info("starting progam Kommune")
        #loads all nesecery logs and files from working directory
        logger.info("loading file kommune.json")
        kommune = json.load(open("file/data/kommune.json", "r"))
        logger.info("loading file pdf_log.json")
        pdf_log = json.load(open("file/data/pdf_log.json", "r"))
        logger.info("loading file sendt.json")
        sendt = json.load(open("file/data/sendt.json", "r"))
        logger.info("loading file pdf_set.json")
        pdf_set = json.load(open("file/data/pdf_set.json","r"))
        logger.info("loading file mote_set.json")
        mote_set = json.load(open("file/data/mote_set.json","r"))
        logger.info("loading file kommuneliste.json")
        kommuneliste = json.load(open("file/data/kommuneliste.json","r"))
        logger.info("loading file standard_kommune.json")
        standard_kommune = json.load(open("file/data/standard_kommune.json","r"))
        logger.info("loading file nonstandard_kommune.json")
        nonstandard_kommune = json.load(open("file/data/nonstandard_kommune.json","r"))
        logger.info("loading file direct_kommune.json")
        direct_kommune = json.load(open("file/data/direct_kommune.json","r"))
    except Exception as e:
        logger.exception(f"File load error: {e}")
        sys.exit(0)
    
    
    # starts program loop
    logger.info("starting programloop")
    for kommunenavn in tqdm(standard_kommune, desc="Standardkommuner: "):
        kjor_kommune(kommune_url=standard_kommune[kommunenavn][1], kommune_name=kommunenavn)
    for kommunenavn in tqdm(direct_kommune, desc="Directkommuner"):
        kjor_direkte_kommune(kommune_url=direct_kommune[kommunenavn][1], kommune_name=kommunenavn)
    treff_bank = finn_treff_bank()
    treff_pensjon = finn_treff_pensjon()
    print_treff_to_file(treff_bank, "Bank")
    print_treff_to_file(treff_pensjon, "Pensjon")
    add_to_sendt(treff_bank + treff_pensjon)

