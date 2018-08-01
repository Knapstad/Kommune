# -*- coding: utf-8 -*-
"""
Created on Tue Jul 17 14:21:32 2018

@author: Bendik Knapstad
"""

import os
import requests
import re
import time
from typing import Dict, List
from bs4 import BeautifulSoup as BS
import json
from datetime import date
from selenium import webdriver

requests.packages.urllib3.disable_warnings()

proxies = json.load(open("config_.json", "r"))["proxies"]

# helper funtions


def thisday() -> str:
    now = date.today()
    return(f"{now.day}-{now.month}-{now.year}")


pdfCrawl = {"http://93.89.112.77": ["DmbMeetingDetail", "document?"],
            "https://www.vadso.kommune.no": ["response=mote&", "dokid="],
            "http://www.alstahaug.kommune.no":
            ["offentlig-mote-kommunestyret", ".pdf"],
            "http://www.alta.kommune.no":
            ["offentlig-mote-kommunestyret", ".pdf"],
            "http://innsyn.ekommune.no": ["response=mote&", "dokid="],
            "http://www.asnes.kommune.no": ["response=mote&", "dokid="],
            "http://159.171.0.170": ["DmbMeetingDetail", "document?"],
            "http://innsyn.alesund.kommune.no": ["response=mote&", "dokid="],
            "http://einnsyn.fosendrift.no": ["DmbMeetingDetail", "document?"],
            "https://www.ostre-toten.kommune.no":
            ["response=mote&", "dokid="],
            "http://84.49.104.166": ["DmbMeetingDetail", "document?"],
            "http://www.vaaler-he.kommune.no": ["response=mote&", "dokid="],
            "http://www.varoy.kommune.no": ["response=mote&", "dokid="],
            "https://innsyn.ssikt.no": ["DmbMeetingDetail", "document?"],
            "http://94.139.92.229": ["DmbMeetingDetail", "document?"],
            "https://einnsyn.evps.no": ["DmbMeetingDetail", "document?"],
            "http://opengov.cloudapp.net": ["meetings/details", ".pdf"],
            "https://innsyn.ssikt.no": ["DmbMeetingDetail", "document?"],
            "http://159.171.48.136": ["DmbMeetingDetail", "document?"],
            "https://www.ulvik.kommune.no": ["response=mote&", "dokid="],
            "https://innsyn.trondheim.kommune.no": ["BYS","dokid="],
            "https://innsyn.tromso.kommune.no": ["KST", "dokid="],
            "http://www.tokke.kommune.no": [None, "/kommunestyret/"],
            
            
            
            
            }


# start Class


class PdfError(LookupError):
    '''raise this when there's a pdf error for my app'''


class Kommune:

    def __init__(self, url: str, name: str = None) -> None:
        self.name: str = name
        self.url: str = url
        self.regex: str = r"^https?:\/\/[^\/]+"
        self.base: str = (re.search(self.regex, self.url).group())
        self.pdf: str = None
        self.type: str = None
        self.cash: list = ["Kommunal garanti", "Kommunal kausjon",
                           "Kommunalgaranti", "Kommunalkausjon",
                           "Simpel garanti ", "Simpel kausjon",
                           "Simpelgaranti", "Simpelkausjon",
                           "Selvskyldnergaranti", "Selvskyldner garanti",
                           "Selvskyldner kausjon", "Selvskyldnerkausjon",
                           "Lån", "Gjeld"]
        self.pdfLog: dict = {}
        self.type: str = None
        try:
            self.pdfLog: dict = json.load(open("PdfLog.json", "r"))
        except FileNotFoundError:
            self.pdfLog: dict = {}


    def __str__(self) -> str:
        representation = f"""
            {self.name}kommune
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

    def findPDF(self, url: str = None) -> List:
        if not url:
            url = self.url
        """Finds all pdfs on site and returnes them as a list"""
        resp: requests.models.Response = self.geturl(url)
        if str(resp) == "<Response [200]>":
            links: list = BS(self.geturl(url).text, "lxml").findAll("a",
                            href=True)
            pdf: list = [a.get("href") for a in links if ".pdf"
                         in a.get("href").lower() or pdfCrawl[self.base][1]
                         .lower()
                         in a.get("href").lower()]
            if not self.pdf:
                self.pdf = str(len(pdf))
            else:
                self.pdf = str(int(self.pdf) + len(pdf))
        else:
            pdf: list = [str(url), str(resp)]
            try:
                with open("error.json", "r") as f:
                    error = json.load(f)
            except FileNotFoundError:
                error = {}
            error.setdefault(thisday, [])
            error[thisday].append(pdf)
            with open("error.json", "w") as f:
                json.dump(error, f)
        return pdf

    def getPDF(self, url: str = None) -> None:
        """Saves pdf from url"""
        if not url:
            url = self.url
        if "https://" not in url and "http://" not in url:
            url = self.base + url
        try:
            resp = self.geturl(url)
            if str(resp) == "<Response [200]>":
                with open("temp.pdf", "wb") as file:
                    file.write(resp.content)
            else:
                raise PdfError("no pdf found")
        except Exception as E:
            return(str(E))

    def readPDF(self):
        """uses pdftotext comandline to convert to text"""
        os.system("pdftotext temp.pdf")
        with open("temp.txt", "r") as f:
            tekst = f.read()
        return tekst

    def findcash(self, url=None) -> Dict:
        """Iterates over all pdf's and returnes a dictionary of link and
        keyword when cash-words are pressent in the pdf"""

        gold = {}
        if not url:
            url = self.url
        #if self.type == "einnsyn":
        for i in self.getMoter():
            for y in self.findPDF(i):
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
                            if s in tekst:
                                gold.setdefault(str(y), [])
                                self.pdfLog[str(y)][0] = "1"
                                self.pdfLog[str(y)].append(s)
                                print(i, s)
                                gold[str(y)].append(s)
#        else:
#            for i in self.findPDF(url):
#                print(i)
#                if str(i) in self.pdfLog:
#                    pass
#                else:
#                    if self.getPDF(y) == "no pdf found":
#                            self.pdfLog.setdefault(str(y), ["0",
#                                                   "no pdf error"])
#                    else:
#                        self.pdfLog.setdefault(str(i), ["0"])
#                        tekst = self.readPDF()
#                        for s in self.cash:
#                            if s in self.readPDF():
#                                gold.setdefault(str(y), [])
#                                self.pdfLog[str(i)][0] = "1"
#                                self.pdfLog[str(i)].append(s)
#                                print(i, s)
#                                gold[str(y)].append(s)

        with open("PdfLog.json", "w") as f:
            json.dump(self.pdfLog, f)
        return gold

    def getMoter(self):
        if pdfCrawl[self.base][0] is None:
            pass
        else:
            """Finds all meetings on meeting calender site and returnes them as a list"""
            links: list = BS(self.geturl().content, "lxml").findAll("a", href=True)
            meetings: list = [self.base + a.get("href") for a in links if
                              pdfCrawl[self.base][1].lower() in
                              a.get("href").lower]
            return meetings

    def getMoterSel(self):
        if pdfCrawl[self.base][0] is None:
            pass
        
        else:
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            options.add_argument('--window-size=1920,1080')
            driver = webdriver.Chrome(chrome_options=options)
            driver.get(self.url)
            time.sleep(1)
            utval = pdfCrawl[self.base][0]
            td = driver.find_elements_by_xpath(f"//td[@data-utvalg='{utval}']")
            ids = []
            for i in td:
                try:
                    ids.append(i.find_element_by_class_name("fc-content"))
                except:
                    pass
            print(len(ids))
            meetings: list = [self.url + "motedag?offmoteid=" +
                              i.get_attribute("id") for i in ids]
            
            return meetings



#for i in kommune:
#    try:
#        print("pass check")
#        if len(kommune[i][2]) >= 11:
#            print("willpass")
#        else:
#            try:
#                a = geturl(kommune[i][0]+"innsyn")
#                print(a, "checked url")
#            except:
#                a= "noresponse"
#                print(a)
#            
#            if str(a) == "<Response [200]>":
#                print("valid response, appending url")
#                kommune[i][2] = a.url
#            else:
#                print("innvalid response, appending response")
#                kommune[i][2] = a
#            
#    except:
#        print("long")
#        
           