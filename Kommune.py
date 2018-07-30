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

requests.packages.urllib3.disable_warnings()

proxies = json.load(open("config_.json", "r"))["proxies"]

# helper funtions


def thisday() -> str:
    now = date.today()
    return(f"{now.day}-{now.month}-{now.year}")

pdfDict = {"http://93.89.112.77" : "document?",
           "https://www.vadso.kommune.no" : "dokid="
           }


meetingDict ={"http://93.89.112.77" : "DmbMeetingDetail",
              "https://www.vadso.kommune.no" : "response=mote&",
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
                         in a.get("href").lower() or pdfDict[self.base] in
                         a.get("href").lower()]
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
        """Finds all meetings on einnsyn site and returnes them as a list"""
        links: list = BS(self.geturl().content, "lxml").findAll("a", href=True)
        meetings: list = [self.base + a.get("href") for a in links if
                          meetingDict[self.base] in a.get("href")]
        return meetings
