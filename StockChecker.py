import requests  # pip3 install requests
from bs4 import BeautifulSoup  # pip3 install beautifulsoup4
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import time
from chump import Application  # pip3 install chump
import re

from fuzzywuzzy import fuzz #  pip3 install fuzzywuzzy  #  http://chairnerd.seatgeek.com/fuzzywuzzy-fuzzy-string-matching-in-python/
from fuzzywuzzy import process

from verbalexpressions import VerEx

class WebsiteData:

    def __init__(self, website_xml):
        """
        This is a data type for holding and processing all info relating to a base webpage (AKA The root of a collection of search pages)
        @param website_xml: An ElementTree holding all xml information regarding a base website.
        @type website_xml: ElementTree
        @return: None
        @rtype: None
        """
        self._website_xml = website_xml
        self._website_name = "Unknown"
        try:
            self._website_name = website_xml.attrib['name']
            self._base_url = website_xml.find("base_url").text

            self._sub_sites = []  # type: list[SubSiteData]
            for sub_site_xml in self._website_xml.findall('sub_site'):
                self._sub_sites.append(SubSiteData(sub_site_xml))

            # for subSite in self._sub_sites:
                # print(self._base_url + subSite.url)
        except Exception as e:
            print("Could not load data for " + self._website_name + ". Error: " + str(e))
            self._website_xml = None
            self._base_url = ""
            self._sub_sites = None

    @property
    def website_name(self):
        """
        Returns the english name of the website held by this object
        @return: Website Name
        @rtype: str
        """
        return self._website_name

    @property
    def sub_sites(self):
        """

        @return: Returns a list of SubSiteData
        @rtype: list[SubSiteData]
        """
        return self._sub_sites

    @property
    def url(self):
        """
        The url associated with a subsite.
        @return: Returns the url associated with a subsite.
        @rtype: str
        """
        return self._base_url


class SubSiteData:

    def __init__(self, sub_site_xml):
        """
        This is a data type for holding and processing all info relating to a sub-site specified for a base webpage
        @param sub_site_xml: An ElementTree holding xml information regarding a sub website
        @type sub_site_xml: ElementTree
        @return: None
        @rtype: None
        """
        self._xml = sub_site_xml
        self._url = self._xml.find('url').text
        self.website_html = None
        self._figures = None
        self.figure_search_data = []

        # initialize the search parameters.
        for fig in self._xml.findall('figure'):
            self.figure_search_data.append(SearchParams(fig))

    @property
    def figures(self):
        """
        A collection of figure objects
        @return: list[FigureData]
        @rtype: list[FigureData]
        """
        return self._figures

    @figures.setter
    def figures(self, value):
        """
        A collection of figures scraped from a website

        @param value:
        @type value:
        """
        self._figures = value

    @property
    def url(self):
        """
        The url associated with a subsite.
        @return: Returns the url associated with a subsite.
        @rtype: str
        """
        return self._url


class FigureSearchData:

    def __init__(self, search_param_xml):
        self._xml = search_param_xml
        self.regEx_string = '(.*)'

        self.search_parameter = self._xml.text
        try:
            self.dependence = self._xml.attrib['dependence']
        except KeyError as e:
            print("ln 129: " + str(e))

        self.search_parameter_escaped = re.escape(self.search_parameter)
        self.tester = ver_ex.anything().find(self.search_parameter).anything().with_any_case(True)

        try:
            self.exactly = bool(self._xml.attrib['exactly'])
        except KeyError as e:
            self.exactly = False

        print(self.exactly)


class SearchParams:

    def __init__(self, figure_xml):
        self._xml = figure_xml

        self._figure_name = self._xml.attrib['name']
        self._search_parameters = []

        for search_xml in self._xml.findall('search'):
            self._search_parameters.append(FigureSearchData(search_xml))

        self.fuzzy_search = ""
        self.regex_search = None

    @property
    def parameters(self):
        return self._search_parameters

    @parameters.setter
    def parameters(self, value):
        self._search_parameters = value

    def search(self, _figure, confidence):
        # we are using a two step matching system.
        # First we be above a confidence threashold using a fuzzy search
        # Then we must find all of the mandatory parameters using regex

        for param in self._search_parameters:
            self.fuzzy_search += param.search_parameter + " "

            if param.dependence == "mandatory":
                if param.exactly:
                    param.regEx_string = r'\b' + re.escape(param.search_parameter) + r'\b'
                else:
                    param.regEx_string = param.search_parameter

            # if self.regex_search is None:
            #     self.regex_search = param.regEx_string
            # else:
            #     self.regex_search += "|" + param.regEx_string

        if fuzz.token_set_ratio(self.fuzzy_search, figure.name) > confidence:
            # Initial match
            for param in self._search_parameters:
                if re.search(param.regEx_string, figure.name) is None:
                    # if any of the mandatory strings are not found, return false
                    return False
        else:
            return False

        return True


class Figures:
    # TODO: Figure out a better way of doing this.
    def __init__(self, service, html, iurl):

        self._url = iurl
        self._service = service.lower()  # type: str
        self._html = html
        self._decoder = Decoder(self._service)
        self.figures = self._decoder.get_figures(self._html, self._url)  # type: list[FigureData]


class FigureData:

    def __init__(self, service, figure_html):
        self._service = service.lower()  # type: str

        self._html = figure_html
        # self._parsed_html = BeautifulSoup(localHTML, 'html.parser')
        self._name = None  # type: str
        self.price = None  # type: str
        self.link = None  # type: str
        self.pic_link = None  # type: str
        self._condition = None  # type: str
        self._releaseStatus = None  # type: str

    @property
    def release_status(self):
        return self._releaseStatus

    @release_status.setter
    def release_status(self, value):
        self._releaseStatus = value

    @property
    def name(self):
        """
        Returns the name of the figure

        @return: Figure Name
        @rtype: str
        """
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def condition(self):
        """
        Returns the condition of the figure.

        @return: a condition string defined in Decoder
        @rtype: str
        """
        return self._condition

    @condition.setter
    def condition(self, value):
        if self._condition is None:
            self._condition = value
        else:
            raise ValueError("Can not change condition once condition has already been set.")


class Decoder:
    jungle = 'jungle'
    amiami = 'amiami'

    def __new__(cls, service, *arguments, **keyword):
        for subclass in Decoder.__subclasses__():
            if service.lower().startswith(subclass.service):
                return super(cls, subclass).__new__(subclass)#, *arguments)#, **keyword)
        raise Exception('Website not supported not supported')

    def _condition(self, value):
        raise NotImplementedError

    def _get_pages(self):
        raise NotImplementedError

    def get_figures(self, html=None, url=None):
        raise NotImplementedError


class JungleDecoder(Decoder):
    service = Decoder.jungle
    conditionBase = "http://jungle-scs.co.jp/sale_en/wp-content/themes/jungle_2013en/images/"
    conditionS = "conditionicon_s_en.gif"
    conditionA = "conditionicon_a_en.gif"
    conditionB = "conditionicon_b_en.gif"
    conditionDecode = {conditionS: 'Sealed', conditionA: 'A', conditionB: 'B'}

    def __new__(cls, service):
        pass

    def __init__(self, service):
        self._product_phtml = None
        self._parsed_html = None  # type: BeautifulSoup
        self._figures = []  # type: list[FigureData]


        # if self.product_phtml is None:

    def _condition(self, value):
        tmp = value[value.rindex('/') + 1:]
        return self.conditionDecode[tmp]

    def _get_pages(self):
        paging_tags = self._parsed_html.find(id='paging')  #.find_all('span')  # type: list[tag]

        if paging_tags is not None:
            next_page_element = paging_tags.find('span', string='Next Page»') #_class='sp04_pl20')  #.find('a').get('href')
            if next_page_element is not None:
                next_page_url = next_page_element.find('a').get('href')
                print("getting " + next_page_url)
                return next_page_url

        return None

    def get_figures(self, html=None, url=None):

        if html is not None and len(self._figures) < 1 and url is not None:

            # Only parse if html is given and the figures array is empty
            more_figures = True
            next_page_url = None
            while more_figures:
                self._parsed_html = BeautifulSoup(html, 'html.parser')
                try:
                    next_page_url = self._get_pages()

                    products_soup = self._parsed_html.find(id='products').find_all("li")

                    for figure_soup in products_soup:
                        tempFig = FigureData(Decoder.jungle, html)

                        tempFig.name = figure_soup.find(class_='wrapword').text

                        tempFig.price = figure_soup.find(class_="price").text

                        tempFig.pic_link = figure_soup.find('img')['src']

                        tempFig.condition = self._condition(figure_soup.find('p').find_all('img')[1]['src'])

                        relURL = figure_soup.find('a').get('href')
                        tempFig.link = urljoin(url, relURL)

                        self._figures.append(tempFig)
                    #
                except Exception as e:
                    print("Try Failed")
                    print(e)

                if next_page_url is not None:
                    html = requests.get(next_page_url).text
                    print("got next page")
                else:
                    more_figures = False

        return self._figures


class AmiAmiDecoder(Decoder):
    service = Decoder.amiami
    conditionBase = "http://amiami.co.jp"
    conditionS = "conditionicon_s_en.gif"
    conditionA = "conditionicon_a_en.gif"
    conditionB = "conditionicon_b_en.gif"
    conditionDecode = {conditionS: 'Sealed', conditionA: 'A', conditionB: 'B'}

    def __new__(cls, service):
        pass

    def __init__(self, service):
        self._product_phtml = None
        self._parsed_html = None
        self._figures = [] # type: list[FigureData]

    def _condition(self, value):
        raise NotImplementedError
        # return self.conditionDecode[value]

    def _get_pages(self):
        raise NotImplementedError

    def get_figures(self, html=None):
        raise NotImplementedError


def scrapeSite(_url):
    """

    @param _url: The URL of the website that will be scraped
    @type _url: str
    @return: Success flag, website data
    @rtype: (bool, string)
    """
    was_scrape_successful = True
    print("Scraping " + _url)
    try:
        website = requests.get(_url)
    except requests.Timeout as e:
        print(e)
        website = None
        was_scrape_successful = False
    except Exception as error:
        print(error)
        website = None
        # printTKMSG("Uncaught Exception in scrapePlex", traceback.format_exc())

    website_data = website.text

    # return was_scrape_successful, website_data
    return website_data


if __name__ == '__main__':
    push_app = Application("***REMOVED***")
    push_User = push_app.get_user("***REMOVED***")

    ver_ex = VerEx()

    tree = ET.parse('sources.xml')
    xmlData = tree.getroot()
    websites = []  # type: list [WebsiteData]

    # Parse XML Config
    for website_xml in xmlData:
        websites.append(WebsiteData(website_xml))

    # Scrape all websites and convert them to soup
    for site in websites:
        if site.sub_sites is not None:

            for sub_site in site.sub_sites:
                url = site.url + sub_site.url
                sub_site.website_html = scrapeSite(site.url + sub_site.url)
                sub_site.figures = Figures(site.website_name, sub_site.website_html, url).figures

    for site in websites:
        if site.sub_sites is not None:
            for sub_site in site.sub_sites:
                for figure in sub_site.figures:
                    for search_data in sub_site.figure_search_data:
                        fig_found = search_data.search(figure, 60)
                        # if search_data.tester.match(figure.name):
                        #     print("we matched " + figure.name)
                        #     break
                        # result = fuzz.token_set_ratio(searchString, figure.name)
                        # if result > 40:
                        if fig_found:
                            print("Matched figure " + figure.name) # + " with " + str(result) + "% confidence against " + searchString )


    #Search for Items

    input("Press any key to exit")

