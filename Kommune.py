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
from tqdm import tqdm

disable_warnings()

try:
    proxies = json.load(open("config_.json", "r"))["proxies"]
except FileNotFoundError:
    print("config_.json needs to be pressent in working directory")

#helper fuctions
kommune = json.load(open("kommune.json", "r"))
# innsyn = json.load(open("innsyn.json", "r"))
# done = json.load(open("done.json","r"))
pdf_log = json.load(open("pdf_log.json", "r"))
# pdf_crawl= json.load(open("pdf_crawl.json", "r"))
sendt = json.load(open("sendt.json", "r"))
pdf_set = json.load(open("pdf_set.json","r"))
mote_set = json.load(open("mote_set.json","r"))
kommuneliste = json.load(open("kommuneliste.json","r"))
standard_kommune = json.load(open("standard_kommune.json","r"))
nonstandard_kommune = json.load(open("nonstandard_kommune.json","r"))
direct_kommune = json.load(open("direct_kommune.json","r"))


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
        self.pensjon: list =["pensjonsordning", "pensjon", "tjenestepensjon",
                             "innskuddspensjon", "hybridpensjon", 
                             "pensjonsleverandør", "AFP", "Ny pensjonsordning", 
                             "ny pensjon"]
        self.treff: list =[]
        self.pdf_log: dict = {}
        try:
            self.pdf_log: dict = json.load(open("pdf_log.json", "r"))
        except FileNotFoundError:
            self.pdf_log: dict = {}
        try:
            self.pdf_set: list = json.load(open("pdf_set.json","r"))
        except FileNotFoundError:
            print("pdf_set.json needs to be pressent in working directory")
        try:
            self.mote_set: list = json.load(open("mote_set.json","r"))
        except FileNotFoundError:
            print("mote_set.json needs to be pressent in working directory")

    def __str__(self) -> str:
        representation = f"""
            {self.name} kommune
            url = {self.url}
            pdf = {self.pdf} pdf'er
            type = {self.type}"""
        return representation

    def get_url(self, url: str = None, re: int = 3) -> requests.models.Response:
        """gets url with proxysettings and returnes response"""
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
            resp = self.get_url(url=url)
            if str(resp) == "<Response [200]>":
                with open("temp.pdf", "wb") as file:
                    file.write(resp.content)
            else:
                self.pdf_log[url]["Bank"] = [str(resp,)+ "No pdf"]
                self.pdf_log[url]["Pensjon"] = [str(resp,)+ "No pdf"]
                raise PdfError("no pdf found")
        except Exception as E:
            return E

    def read_pdf(self):
        """uses pdftotext comandline to convert to text
        returnes text"""
        os.system("pdftotext temp.pdf")
        with open("temp.txt", "r") as f:
            tekst = f.read()
        return tekst

    def find_hits_bank(self, pdf_url: str)-> None:
        """Finds banking word in textconverted pdf via self.read_pdf()
            logs findings to self.pdf_log"""
        self.pdf_log.setdefault(pdf_url,{"Bank": [0], "Pensjon": [0]})
        try:
            tekst = self.read_pdf()
            for word in self.bank:
                if word.lower() in tekst.lower():
                    self.pdf_log[pdf_url]["Bank"][0]=1
                    self.pdf_log[pdf_url]["Bank"].append(word)
        except Exception as e:
            self.pdf_log[pdf_url].setdefault({"Bank": [0]})
            self.pdf_log[pdf_url]["Bank"]=[0, e]

    def find_hits_pensjon(self, pdf_url: str)-> None:
        """Finds pansjon word in textconverted pdf via self.read_pdf()"""
        self.pdf_log.setdefault(pdf_url,{"Bank": [0], "Pensjon": [0]})
        try:
            tekst = self.read_pdf()
            for word in self.pensjon:
                if word.lower() in tekst.lower():
                    self.pdf_log[pdf_url]["Pensjon"][0]=1
                    self.pdf_log[pdf_url]["Pensjon"].append(word)
        except Exception as e:
            self.pdf_log[pdf_url]["Pensjon"]=[0, e]

    def get_mote_url(self, resp: BS) -> list:
        """Asumes resp is a url with list of standars meetings,
        @returnes: list of links""" 
        elements: list = BS(resp.content, "lxml").findAll("a", href=True)
        links: list = [urljoin(resp.url, a.get("href")) for a in elements if sjekk_mote_url(urljoin(resp.url, a.get("href")))]
        return links

    def get_pdf_url(self, resp: BS) -> list:
        """Assumes resp is a meeting url, @returnes all pdf urls form reso"""
        elements: list = BS(resp.content, "lxml").findAll("a", href=True)
        links: list = [urljoin(resp.url, a.get("href")) for a in elements if sjekk_pdf_url(urljoin(resp.url, a.get("href")))]
        return links

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
    links: list = [urljoin(resp.url, a.get("href")) for a in elements if sjekk_mote_url(urljoin(resp.url, a.get("href")))]
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

def get_pdf_urls(links: list) -> bool:
    "Get all links if they match any string in pdf_set"
    pdfs: list = [link for link in links if sjekk_pdf_url(link)]
    return pdfs

def sjekk_mote_url(url: str):
    """Checks @param url for any match in mote_set returns bolean"""
    return any(sub in url for sub in mote_set)

def sjekk_pdf_url(url: str) -> list:
    """Checks url for any match in pdf_set returns bolean"""
    return any(sub in url for sub in pdf_set)

def find_non_standard_kommune() -> list:
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
            print(kommune[-1], e)
            non_standard_kommune.append(kommune)
    return non_standard_kommune



def kjor_kommune(kommune_url: str, kommune_navn: str = None) -> None:
    """Takes kommune_url and kommune_navn finds kommune pdfs
    updates pdf_log with new findings and saves to pdf_log.json"""
    kommune: Kommune = Kommune(url=kommune_url, name=kommune_navn)
    mote_response  = kommune.get_url()
    moter: list = kommune.get_mote_url(resp=mote_response)
    for url in moter:
        pdf_response = kommune.get_url(url=url)
        pdfs: list = kommune.get_pdf_url(resp=pdf_response)
    for pdf in pdfs:
        kommune.get_pdf(url=pdf)
        kommune.read_pdf()
        kommune.find_hits_bank(pdf_url=pdf)
        kommune.find_hits_pensjon(pdf_url=pdf)
    pdf_log = json.load(open("pdf_log.json","r"))
    updated_pdf_log = {**pdf_log, **kommune.pdf_log}
    json.dump(updated_pdf_log, open("pdf_log.json","w"))

def kjor_direkte_kommune(kommune_url: str, kommune_name: str = None) -> None: 
    """Takes kommune_url and kommune_navn finds kommune pdfs
    updates pdf_log with new findings and saves to pdf_log.json""" 
    kommune: Kommune = Kommune(url=kommune_url, name=kommune_name)
    pdf_response  = kommune.get_url()
    pdfs: list = kommune.get_pdf_url(resp=pdf_response)
    for pdf in pdfs:
        kommune.get_pdf(url=pdf)
        kommune.read_pdf()
        kommune.find_hits_bank(pdf_url=pdf)
        kommune.find_hits_pensjon(pdf_url=pdf)
    pdf_log = json.load(open("pdf_log.json","r"))
    updated_pdf_log = {**pdf_log, **kommune.pdf_log}
    json.dump(updated_pdf_log, open("pdf_log.json","w"))

def finn_treff() -> list:
    """Itterates over pdf_log and returnes those that have hits
    and are not present in sendt"""
    treff =  []
    for i in pdf_log.keys():
        if pdf_log[i][0] != "0" and i not in sendt:
            #print(i)
            treff.append([i, pdf_log[i]])
    return treff

def finn_treff_bank() -> list:
    """Iterates over pdf_log and returnes those that have bank hits
    and are not present in sendt"""
    treff =  []
    for i in pdf_log.keys():
        if pdf_log[i]["Bank"][0] == "1" and i not in sendt:
            #print(i)
            treff.append([i, pdf_log[i]["Bank"]])
    return treff


def finn_treff_pensjon() -> list:
    """Iterates over pdf_log and returnes those that have bank hits
    and are not present in sendt"""
    treff =  []
    for i in pdf_log.keys():
        if pdf_log[i]["Pensjon"][0] == "1" and i not in sendt:
            #print(i)
            treff.append([i, pdf_log[i]])
    return treff

def add_to_sendt(file: list) -> None:
    """adds list to sendt"""
    for pdf_link in file:
       if pdf_link[0] not in sendt:
           sendt.append(pdf_link[0])


def print_treff_to_file(hit_list: list, name: str = None) -> None:
    """exports hit_list to csv"""
    with open(f"/files/kommune{name}{thisday()}.csv","w") as f:
        write = csv.writer(f)
        write.writerows(hit_list)


def save():
    """Saves all logs to disk"""
    # json.dump(pdf_crawl, open("pdf_crawl.json","w"))
    json.dump(sendt, open("sendt.json","w"))
    json.dump(pdf_log, open("pdf_log.json","w"))
    json.dump(kommune, open("kommune.json","w"))
    # json.dump(done, open("done.json","w"))
    # json.dump(innsyn, open("innsyn.json","w"))
    json.dump(pdf_set, open("pdf_set.json","w"))
    json.dump(mote_set, open("mote_set.json","w"))
    json.dump(standard_kommune, open("standard_kommune.json","w"))
    json.dump(nonstandard_kommune, open("nonstandard_kommune.json","w"))
    json.dump(direct_kommune, open("direct_kommune.json","w"))

if __name__=="__main__":
    #loads all nesecery logs and files from working directory
    kommune = json.load(open("kommune.json", "r"))
    pdf_log = json.load(open("pdf_log.json", "r"))
    sendt = json.load(open("sendt.json", "r"))
    pdf_set = json.load(open("pdf_set.json","r"))
    mote_set = json.load(open("mote_set.json","r"))
    kommuneliste = json.load(open("kommuneliste.json","r"))
    standard_kommune = json.load(open("standard_kommune.json","r"))
    nonstandard_kommune = json.load(open("nonstandard_kommune.json","r"))
    direct_kommune = json.load(open("direct_kommune.json","r"))
    starts program loop
     for kommunenavn in standard_kommune:
         kjor_kommune(kommune_url=kommunenavn[1], name=kommunenanvn)
    for kommunenavn in direct_kommune:
        kjor_direkte_kommune(kommune_url=direct_kommune[kommunenavn][1], kommune_name=kommunenavn)
    treff_bank = finn_treff_bank()
    treff_pensjon = finn_treff_pensjon()
    print_treff_to_file(treff_bank, "Bank")
    print_treff_to_file(treff_pensjon, "Pensjon")
    add_to_sendt(treff_bank + treff_pensjon)

