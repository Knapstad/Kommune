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
    if not url.startswith("http"):
        return False
    return any(sub in url for sub in mote_set) and not any(sub in url for sub in exclude)

def sjekk_pdf_url(url: str) -> bool:
    """Checks url for any match in pdf_set returns bolean"""
     if not url.startswith("http"):
        return False
    return any(sub in url for sub in pdf_set) and not any(sub in url for sub in exclude)

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