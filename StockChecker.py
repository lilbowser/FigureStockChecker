import requests  # pip3 install requests
from bs4 import BeautifulSoup  # pip3 install beautifulsoup4
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import time as time_p
import logging
import sys
import traceback
from distutils.util import strtobool
from datetime import time, timedelta, datetime, date

# Pushover
from chump import Application  # pip3 install chump

# For console manipulation.
from colorama import Fore, Back, Style, init
import click

# String Searching
#  http://chairnerd.seatgeek.com/fuzzywuzzy-fuzzy-string-matching-in-python/
from fuzzywuzzy import fuzz  # pip3 install fuzzywuzzy
from fuzzywuzzy import process

import re
from verbalexpressions import VerEx


class WebsiteData:

    def __init__(self, _website_xml):
        """
        This is a data type for holding and processing all info relating to a base webpage (AKA The root of a collection of search pages)
        @param _website_xml: An ElementTree holding all xml information regarding a base website.
        @type _website_xml: ElementTree
        @return: None
        @rtype: None
        """
        self._website_xml = _website_xml
        self._website_name = "Unknown"
        self._log = logging.getLogger(self.__class__.__name__)
        try:
            self._website_name = _website_xml.attrib['name']
            self._base_url = _website_xml.find("base_url").text

            self._sub_sites = []
            for sub_site_xml in self._website_xml.findall('sub_site'):
                self._sub_sites.append(SubSiteData(sub_site_xml))

            # for subSite in self._sub_sites:
                # print(self._base_url + subSite.url)
        except Exception as e:
            self._log.error("Could not load data for " + self._website_name + ". Error: " + str(e), exc_info=True)
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
        try:
            self._local_uri = self._xml.find('local').text
        except AttributeError:
            self._local_uri = None
        except KeyError:
            self._local_uri = None

        self._sub_site_description = self._xml.attrib['name']

        self.website_html = None
        self.old_figures = []
        self._figures = None
        self.figure_search_data = []
        self._discovered_figures = []
        self._deleted_figures = []

        # initialize the search parameters.
        for fig in self._xml.findall('figure'):
            self.figure_search_data.append(SearchParams(fig))

        self.frequency, self.time = self.parse_schedule()
        self.matched_reporting, self.unmatched_reporting = self.parse_reporting()


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
    def discovered_figures(self):
        """
        Storage for figures that we scrape from the website that we have deemed to be new.
        @return: List of New Figures
        @rtype: list[FigureData]
        """
        return self._discovered_figures

    @discovered_figures.setter
    def discovered_figures(self, value):
        self._discovered_figures = value

    @property
    def deleted_figures(self):
        """
        Storage for figures that we scrape from the website that we have deemed to be deleted.
        @return: List of Deleted Figures
        @rtype: list[FigureData]
        """
        return self._deleted_figures

    @deleted_figures.setter
    def deleted_figures(self, value):
        self._deleted_figures = value

    @property
    def url(self):
        """
        The url associated with a subsite.
        @return: Returns the url associated with a subsite.
        @rtype: str
        """
        return self._url

    @property
    def local_uri(self):
        """
        Returns the local URI from the xml (if any)
        @return: the local URI
        @rtype: (str | None)
        """
        return self._local_uri

    @property
    def description(self):
        """
        @return: The Descriptive name of the subsection
        @rtype: str
        """
        return self._sub_site_description

    def parse_schedule(self):
        frequency = None
        _time_date = None
        try:
            sch_xml = self._xml.find('schedule')

            try:
                freq_xml = sch_xml.find('frequency')
                _days = int(freq_xml.find('days').text)
                _hours = int(freq_xml.find('hours').text)
                _minutes = int(freq_xml.find('minutes').text)
                _seconds = int(freq_xml.find('seconds').text)

                frequency = timedelta(days=_days, hours=_hours, minutes=_minutes, seconds=_seconds)
            except AttributeError:
                pass
            except KeyError:
                pass

            try:
                str_time = sch_xml.find('time').text
                #  parse the time as a time object instead of a datetime object,
                #  as a datetime object would have an incorrect date
                _time = datetime.strptime(str_time, "%H:%M:%S").time()

                #  Convert the time object back into a datetime object with correct date.
                _time_date = datetime.combine(date.today(), _time)
                if _time_date < datetime.now():
                    #  we need to move the resume_time forward by one day
                    _time_date = _time_date + timedelta(days=1)

            except AttributeError:
                pass
            except KeyError:
                pass

        except AttributeError:
            pass
        except KeyError:
            pass

        return frequency, _time_date

    def parse_reporting(self):
        """

        @return: individually, group, or none
        @rtype: str, str
        """
        matched = None
        unmatched = None
        try:
            report_xml = self._xml.find('report')
            matched = report_xml.find('matched').text
            unmatched = report_xml.find('unmatched').text
        except:
            pass

        return matched, unmatched


class FigureSearchData:

    def __init__(self, search_param_xml):
        self._xml = search_param_xml
        self.regEx_string = '(.*)'  # Initialize with detect all

        self.search_parameter = self._xml.text

        try:
            self.dependence = self._xml.attrib['dependence']
        except KeyError as e:
            self.dependence = 'optional'

        try:
            self.exactly = strtobool(self._xml.attrib['exactly'].strip())
        except KeyError as e:
            self.exactly = False


class SearchParams:

    def __init__(self, figure_xml):
        self._xml = figure_xml

        self._figure_name = self._xml.attrib['name']  # not actually needed.
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
        # First we be above a confidence threshold using a fuzzy search
        # Then we must find all of the mandatory parameters using regex
        if self.fuzzy_search == '':
            for param in self._search_parameters:
                self.fuzzy_search += param.search_parameter + " "

                if param.dependence == "mandatory":
                    # TODO: I do not think I am supposed to use escape likethis
                    if param.exactly:
                        param.regEx_string = r'\b' + re.escape(param.search_parameter) + r'\b'
                    else:
                        param.regEx_string = re.escape(param.search_parameter)

            # if self.regex_search is None:
            #     self.regex_search = param.regEx_string
            # else:
            #     self.regex_search += "|" + param.regEx_string
        result = fuzz.token_set_ratio(self.fuzzy_search, _figure.extended_name)
        if result > confidence:
            # Initial match
            for param in self._search_parameters:
                if re.search(param.regEx_string, _figure.extended_name) is None:
                    # if any of the mandatory strings are not found, return false
                    return False, result
        else:
            return False, result

        return True, result


class Figures:
    # TODO: Figure out a better way of doing this.
    # TODO: I not even sure we should have a Figures class as we are not really using it.
    # TODO: At the very least, the name should be changed to something more fitting...... Not sure what.
    # TODO: maybe Setup_Decoder.
    # TODO: and then we can call figures = Decoder(service).get_figures(html,url) in main
    # Currently this is being used to call get Figures from main. We are assigning self.figures to the sub-site figures
    # array instead of storing this object..... This is not useful.
    # we don't need this as a reference to the decoder, because I store a reference to the decoder in each FigureData
    # object

    def __init__(self, service, html, _url):

        self._url = _url
        self._service = service  # type: str
        self._html = html
        self._decoder = Decoder(self._service)
        self.figures = self._decoder.get_figures(self._html, self._url)  # type: list[FigureData]


class FigureData:

    def __init__(self, decoder, service, figure_html):
        self._service = service.lower()  # type: str
        self._decoder = decoder
        self._html = figure_html
        # self._parsed_html = BeautifulSoup(localHTML, 'html.parser')
        self._name = None  # type: str
        self.price = None  # type: str
        self.link = None  # type: str
        self.pic_link = None  # type: str
        self._condition = None  # type: str
        self._releaseStatus = None  # type: str
        self._extended_name = None  # type: str
        self._search_url = None  # type: str # TODO: This is currently unused
        self.TTL = 3 # type: int

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
        """
        @param value: the name of the figure
        @type value: str
        """
        self._name = value.strip()

    @property
    def extended_name(self):
        if self._extended_name is not None:
            return self._extended_name
        else:
            return self.name

    @extended_name.setter
    def extended_name(self, value):
        self._extended_name = value.strip()

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

    def get_extended_name(self):
        self._decoder.get_extended_name(self)

    @property
    def search_url(self):
        return self._search_url

    @search_url.setter
    def search_url(self, value):
        self._search_url = value


class Decoder:
    jungle = 'jungle'
    amiami = 'amiami'
    amiami_preowned = 'amiami_preowned'

    def __new__(cls, service, *arguments, **keyword):
        for subclass in Decoder.__subclasses__():
            if service.lower().startswith(subclass.service):
                return super(cls, subclass).__new__(subclass)  # , *arguments)#, **keyword)
        raise Exception('Website not supported not supported')

    def _condition(self, value):
        raise NotImplementedError

    def _get_next_page(self):
        """
        Scrapes the webpage for the next page URL and returns it if found. If it can not be found, return None
        @return: Next Page URL or None
        @rtype: str | None
        """
        raise NotImplementedError

    def get_figures(self, html=None, _url=None):
        raise NotImplementedError

    def get_extended_name(self, _figure, override=False):
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
        self._log = logging.getLogger(self.__class__.__name__)
        self._product_phtml = None
        self._parsed_html = None  # type: BeautifulSoup
        self._figures = []  # type: list[FigureData]

    def _condition(self, value):
        tmp = value[value.rindex('/') + 1:]
        return self.conditionDecode[tmp]

    def _get_next_page(self):
        """
        Scrapes the webpage for the next page URL and returns it if found. If it can not be found, return None
        @return: Next Page URL or None
        @rtype: str | None
        """
        if get_next_pages is False:
            return None
        paging_tags = self._parsed_html.find(id='paging')  #.find_all('span')  # type: list[tag]

        if paging_tags is not None:
            next_page_element = paging_tags.find('span', string='Next Page»') #_class='sp04_pl20')  #.find('a').get('href')
            if next_page_element is not None:
                next_page_url = next_page_element.find('a').get('href')
                return next_page_url

        return None

    def get_figures(self, html=None, _url=None):

        if html is not None and len(self._figures) < 1 and _url is not None:

            # Only parse if html is given and the figures array is empty
            more_figures = True
            next_page_url = None
            current_page = 1
            while more_figures:
                self._parsed_html = BeautifulSoup(html, 'html.parser')
                try:
                    next_page_url = self._get_next_page()
                    products_soup = self._parsed_html.find(id='products')
                    # TODO: Find a better way of determining that there are no products on the page
                    if products_soup is not None:
                        products_soup = products_soup.find_all("li")
                    else:
                        break
                    for figure_soup in products_soup:
                        tempFig = FigureData(self, Decoder.jungle, html)  # type: FigureData

                        tempFig.name = figure_soup.find(class_='wrapword').text  # type: str

                        tempFig.price = figure_soup.find(class_="price").text

                        tempFig.pic_link = figure_soup.find('img')['src']

                        tempFig.condition = self._condition(figure_soup.find('p').find_all('img')[1]['src'])

                        relURL = figure_soup.find('a').get('href')
                        tempFig.link = urljoin(_url, relURL)

                        tempFig._search_url = _url

                        self._figures.append(tempFig)

                except Exception as e:
                    print("Try Failed")
                    print(e)
                    print(traceback.format_exc())

                if next_page_url is not None:
                    # TODO: do not rely on outside function
                    current_page += 1
                    html = scrapeSite(next_page_url)
                    sys.stdout.write('\x1b[K')  # Clear the line
                    print("Retrieving page {}".format(current_page))
                    sys.stdout.write('\x1b[1A')  # Move cursor up 2 lines

                    if html is None:  # if we can not get the web page (probably error), do not go to next page.
                        more_figures = False
                        self._log.error("Unable to retrieve the next page.")
                else:
                    more_figures = False

        return self._figures

    def get_extended_name(self, _figure, override=False):
        result = re.search(re.escape(r"..."), _figure.name)
        if result is not None:
            # The entire name is not given on this page. We need  the item page to get it.
            self._log.info("need to get extended name for " + _figure.name)
            # TODO: Do not rely on outside function
            item_html = scrapeSite(_figure.link)
            if item_html is not None:
                try:
                    item_soup = BeautifulSoup(item_html, 'html.parser')
                    # TODO: Consider returning the extended name and setting it in the figure so extended_name is read only
                    _figure.extended_name = item_soup.find(class_="contentstitle").text
                    self._log.info("new Name: " + _figure.extended_name)
                except:
                    self._log.error("Unable to retrieve item detail page. Using truncated name.", exc_info=True)

            else:
                self._log.error("Unable to retrieve item detail page. Using truncated name.", exc_info=True)


class AmiAmiPreownedDecoder(Decoder):
    service = Decoder.amiami_preowned
    conditionBase = "http://amiami.co.jp"
    conditionS = "conditionicon_s_en.gif"
    conditionA = "conditionicon_a_en.gif"
    conditionB = "conditionicon_b_en.gif"
    conditionDecode = {conditionS: 'Sealed', conditionA: 'A', conditionB: 'B'}

    def __new__(cls, service):
        pass

    def __init__(self, service):
        self._log = logging.getLogger(self.__class__.__name__)
        self._product_phtml = None
        self._parsed_html = None
        self._figures = []  # type: list[FigureData]

    def _condition(self, value):
        # TODO: Standardise all _condition() functions
        """
        Deciphers the condition from the string passed to it. If the conditon is part of other pertinent data (such as
        the Figure name) we will return it.
        @param value: The string we need to get the condition from. (inside extended Name of figure)
        @type value: str
        @return: This version will return the name of the figure with the condition striped out.
        @rtype: str
        """

        #  (Pre-owned ITEM:A-/BOX:B)EX Cute Otogi no Kuni / Sleeping Beauty Lien Complete Doll(Released)
        # r'\(Pre-owned ITEM:(\S+)\/BOx:(\S+)\)\b'
        # extract the item condition and box condition
        condition = None
        extended_name = None
        try:
            item_condition, box_condition = re.search(r'\(Pre-owned ITEM:(.*)\/.*?BOx:(.*)\)(?=.)', value, re.I).groups()
            condition = ("Item : " + item_condition + " Box: " + box_condition)
            extended_name = re.sub(r'\(Pre-owned ITEM:(.*)\/.*?BOx:(.*)\)(?=.)', '', value, flags=re.I)
            return condition, extended_name
        except:
            self._log.error(traceback.format_exc())
            return condition, extended_name

    def _get_next_page(self, html_soup=None):
        """
        Scrapes the webpage for the next page URL and returns it if found. If it can not be found, return None
        @return: Next Page URL or None
        @rtype: str | None
        """
        if get_next_pages is False:
            return None
        product_tags = self._parsed_html.find(id='products')  # .find_all('span')  # type: list[tag]
        if product_tags is not None:
            next_page_element = product_tags.find('a', string='Next>>')  # _class='sp04_pl20')  #.find('a').get('href')
            if next_page_element is not None:
                next_page_url = next_page_element.get('href')
                return next_page_url
                # return None
        return None

    def _get_pages(self, html_soup=None, prototype_url=None, max_page_num=False, results=False):
        """
        Scrapes the webpage for the next page URL and returns it if found. If it can not be found, return None
        @return: Next Page URL or None
        @rtype: str | None
        """

        if html_soup is not None:
            product_tags = html_soup.find(id='products')  # .find_all('span')  # type: list[tag]
            if product_tags is not None:

                if max_page_num is False:
                    max_page_number = 0
                    for link in product_tags.find_all('a'):
                        page_num = re.search(r'^\[(\d{1,2})\]$', link)
                        if page_num is not None:
                            page_num = page_num.group(0)
                            if page_num > max_page_number:
                                max_page_number = page_num

                next_page_element = product_tags.find('a', string='Next>>')  # _class='sp04_pl20')  #.find('a').get('href')
                if next_page_element is not None:
                    next_page_url = next_page_element.get('href')
                    return next_page_url
                # return None
        return None

    def get_figures(self, html=None, _url=None):

        if html is not None and len(self._figures) < 1 and _url is not None:

            pages_html = [html]
            parsed_html = []

            # Only parse if html is given and the figures array is empty
            more_figures = True  # Flag indicating we still have more figs to parse
            next_page_url = None  # Stores the URL for the next page. Needs to be initialized to None.
            current_page = 1  # The current page number
            got_multiple_pages = False  # Flag indicating whether we scraped one page or multiple pages

            while True:
                parsed_html = BeautifulSoup(html, 'html.parser')
                next_page_url = self._get_pages(parsed_html)

                if next_page_url is not None:
                    # TODO: do not rely on outside function
                    current_page += 1
                    sys.stdout.write('\x1b[K')  # Clear the line
                    print("Retrieving page {}".format(current_page))
                    sys.stdout.write('\x1b[1A')  # Move cursor up 2 lines
                    try:
                        html = scrapeSite(next_page_url)
                    except requests.Timeout or requests.Timeout as e:
                        self._log.error("Getting next Amiami pre-owned page Failed", exc_info=True)

                        raise FigureDataCorrupt

            while more_figures:
                self._log.info("Parsing figures from page {0}.".format(current_page))
                #  Pares the HTML into soup
                try:
                    # TODO: Get pages first so we can multi-thread retrieval of websites.
                    next_page_url = self._get_next_page()
                    products_soup = self._parsed_html.find_all(class_="product_box")
                    # TODO: Find a better way of determining that there are no products on the page
                    if products_soup is None:
                        break

                    for figure_soup in products_soup:
                        tempFig = FigureData(self, Decoder.amiami_preowned, html)  # type: FigureData
                        tempFig.condition = ""

                        tmp = figure_soup.find(class_='product_name_list')
                        tmp2 = tmp.find('a')
                        tempFig.link = tmp2.get('href')
                        tempFig.name = tmp2.text  # figure_soup.find(class_='product_name_list').text  # type: str

                        if tempFig.name == "":  # Occasionally, amiami is missing product titles on the listing page
                            self.get_extended_name(tempFig, override=True)

                        tempPrice = figure_soup.find(class_="product_price").text.strip()

                        try:
                            tempPrice = re.search(r'\d{1,3}?,?\d{1,3}?,?\d{1,3} JPY', tempPrice)
                            if tempPrice is not None:
                                 tempFig.price = tempPrice.group(0)
                            else:
                                tempFig.price = " "
                        except Exception as e:
                            self._log.error('re search error: ', exc_info=True)

                        tempFig.pic_link = figure_soup.find('img')['src']

                        # The condition is not listed on the listing page, only the detail page.
                        # To prevent hammering AmiAmi, we will get condition data only if the item is a match.

                        tempFig._search_url = _url

                        self._figures.append(tempFig)

                # except requests.Timeout as e:

                except Exception as e:
                    self._log.error("Parsing Amiami pre-owned HTML Failed", exc_info=True)
                    # return None
                    raise FigureDataCorrupt

                if next_page_url is not None:
                    # TODO: do not rely on outside function
                    current_page += 1
                    sys.stdout.write('\x1b[K')  # Clear the line
                    print("Retrieving page {}".format(current_page))
                    sys.stdout.write('\x1b[1A')  # Move cursor up 2 lines
                    try:
                        html = scrapeSite(next_page_url)
                    except requests.Timeout or requests.Timeout as e:
                        self._log.error("Getting next Amiami pre-owned page Failed", exc_info=True)

                        raise FigureDataCorrupt
                        # return None

                    got_multiple_pages = True

                    if html is None:  # if we can not get the web page (unknown reason), do not go to next page and invalidate results.
                        more_figures = False
                        self._log.error("Unable to retrieve the next page.")
                        raise FigureDataCorrupt
                        # return None
                else:
                    more_figures = False
            if got_multiple_pages:
                # sys.stdout.write('\x1b[K')  # Clear the line Retrieving page line
                pass
        return self._figures


    def get_extended_name(self, _figure, override=False):
        result = None  # re.search(re.escape(r"..."), _figure.name)  # AMIAMI does not use shortened names.
        if result is not None or override is True:
            # The entire name is not given on this page. We need the item page to get it.
            self._log.info("Need to get extended name for " + _figure.name)
            # TODO: Do not rely on outside function

            item_html = scrapeSite(_figure.link)

            if item_html is not None:
                item_soup = BeautifulSoup(item_html, 'html.parser')
                # TODO: Consider returning the extended name and setting it in the figure so extended_name is read only
                try:
                    tmp_extended_name = item_soup.find(class_="heading_10").contents[0]#.text
                    # Remove (Released) from end of name
                    _figure.extended_name = re.sub(r'\(Released\)', '', tmp_extended_name)  # This call is safe
                    # TODO: I am setting the extended name here, but the condition in condition. Does this make sense?
                    # Remove the condition data from the figure and store it in the figure.

                    _figure._condition, _figure.extended_name = self._condition(_figure.extended_name)

                    self._log.info("New Name: " + _figure.extended_name)
                except Exception as e:
                    self._log.error("Unable to retrieve item detail page. Using truncated name.", exc_info=True)
            else:
                self._log.error("Unable to retrieve item detail page. Using truncated name.", exc_info=True)
            # We need to extract the condition data from the name.

    def get_condition(self, _figure):
        #  Condition data is held in the extended name
        self.get_extended_name(_figure, override=True)


class FigureDataCorrupt(Exception):
    pass


def scrapeSite(_url, use_progress_bar=False, retry=10):
    """
    Safely retrieves and returns a website using passed URL.
    If error occurs during retrieval, None will be returned instead

    @param _url: The URL of the website that will be scraped
    @type _url: str
    @param retry: Indicates How many retries are left. Starts at 10 by default.
    @type retry: int
    @return: website html if successful, otherwise None
    @rtype: str | None | requests.Response
    """

    logging.info("Scraping " + _url)
    try:
        website = requests.get(_url)
    except requests.Timeout as e:
        logging.error(e)
        logging.error(traceback.format_exc())
        website = None

        if retry > 0:
            logging.warning("Retry #{}".format(11 - retry))
            time_p.sleep(0.25 * (11 - retry))
            retry_scrape = scrapeSite(_url, retry=(retry - 1))
            try:
                data = retry_scrape.text
            except:
                data = retry_scrape
            return data
        else:
            raise requests.Timeout
    except Exception as error:
        logging.error(error)
        logging.error(traceback.format_exc())
        website = None
        # printTKMSG("Uncaught Exception in scrapePlex", traceback.format_exc())

        if retry > 0:
            logging.warning("Retry #{}".format(11 - retry))
            time_p.sleep(0.25 * (11 - retry))
            retry_scrape = scrapeSite(_url, retry=(retry - 1))
            try:
                data = retry_scrape.text
            except:
                data = retry_scrape

            return data
        else:
            raise requests.RequestException

    if website is not None:
        website_data = website.text
    else:
        website_data = None

    return website_data


def load_config(URI="keys.yaml"):
    import yaml

    with open(URI, 'r') as stream:
        try:
            _config = yaml.load(stream)
            return _config
        except yaml.YAMLError:
            logging.exception("Error loading yaml config")


if __name__ == '__main__':
    firstRun = True  # Switch to false to prevent pre-loading of history arrays
    get_next_pages = True  # Disable scraping the next page
    init()  # Init colorama
    logging.basicConfig(format="[%(asctime)s] %(name)s: %(funcName)s:%(lineno)d %(levelname)s: %(message)s", filename='StockChecker.log', level=logging.WARNING)  #

    logging.warning("StockChecker.py has started")
    push_keys = load_config()
    push_app = Application(push_keys["AppKey"])
    push_User = push_app.get_user(push_keys["UserKey"])

    ver_ex = VerEx()

    tree = ET.parse('sources.xml')
    xmlData = tree.getroot()
    websites = []  # type: list [WebsiteData]

    old_figures = []  # type: list[FigureData]
    resume_freq = None
    resume_time = None

    running = True
    count = 0
    sleep_time = 0.13  # in minutes
    # Parse XML Config
    for website_xml in xmlData:
        websites.append(WebsiteData(website_xml))

    while running:
        # Scrape all websites and convert them to Figures
        # sys.stdout.write('\x1b[J')  # Clear the Screen
        click.clear()  # Clear the Screen.
        count += 1

        for site in websites:

            if site.sub_sites is not None:
                for sub_site in site.sub_sites:

                    # TODO: We need to figure out a way of utilising the resume data from all subsites
                    resume_freq = sub_site.frequency
                    resume_time = sub_site.time

                    url = site.url + sub_site.url

                    sys.stdout.write('\x1b[1A')  # Move cursor up 1 lines
                    sys.stdout.write('\x1b[K')  # Clear the line
                    print("Scraping " + sub_site.description + "... Scrape# " + str(count))

                    if sub_site.local_uri is not None:
                        sub_site.website_html = open(sub_site.local_uri, 'r', encoding='UTF8').read()
                    else:
                        sub_site.website_html = scrapeSite(url)
                    try:
                        # TODO: call sub_site.figures = Decoder(service).get_figures(site.website_name, sub_site.website_html, url)
                        sub_site.figures = Figures(site.website_name, sub_site.website_html, url).figures
                        sub_site.discovered_figures = []  # Clear the array
                    except FigureDataCorrupt:
                        if firstRun:
                            raise RuntimeError(
                                    "FATAL ERROR: Figure data was corrupt on the first run. Can not continue.")
                        continue  # continue on with the next subsite
                    if firstRun is False:  # if this is not the first time running, Search for different figures.
                        # print("Number of figures: " + str(len(figures)))

                        # New Figure Detection
                        for figure in sub_site.figures:
                            figNew = True
                            for oldFigure in sub_site.old_figures:
                                if oldFigure.name == figure.name:
                                    figNew = False

                            if figNew:
                                figure.get_extended_name()
                                sub_site.discovered_figures.append(figure)

                        # Deleted Figure Detection
                        for oldFigure in sub_site.old_figures:
                            figDeleted = True
                            for figure in sub_site.figures:
                                if oldFigure.name == figure.name:
                                    figDeleted = False

                            if figDeleted:
                                if oldFigure.TTL > 0:
                                    # only re-store the figure if the time to live has not reached 0

                                    logging.info("Figure: {} @ {} was deleted. TTL: {}".format(oldFigure.name,
                                                                                               sub_site.description,
                                                                                               oldFigure.name))
                                    oldFigure.TTL -= 1
                                    sub_site.deleted_figures.append(oldFigure)
                                    sub_site.figures.append(oldFigure)

                                # logging.info("Figure " + figure.extended_name + " is new!")

                            # if old_figures.count(figure) < 1:
                            #     #  figure not found!!
                            #     print("Figure " + figure.name + " is new!")

                    if len(sub_site.discovered_figures) > 50:
                        #  Some sort of failure has occurred as a massive number of figures were just detected
                        # TODO: Work out a more robust method of detecting / avoiding this bug. OR JUST FIX IT!
                        logging.error("Too many new figures detected on {}. # of new figs: {}.".format(
                                sub_site.description, len(sub_site.discovered_figures)))
                        sub_site.discovered_figures = []
                    sub_site.old_figures[:] = sub_site.figures[:]

        firstRun = False  # We have scraped once and the arrays have been pre-loaded. Flip firstRun flag to
        #                   enable scanning.

        for site in websites:
            if site.sub_sites is not None:
                for sub_site in site.sub_sites:
                    found_fig_count = 0
                    ignored_new_figures = []

                    push_msgs = []
                    num_of_msgs = 0
                    push_msgs.append('')
                    for figure in sub_site.discovered_figures:
                        fig_found = False

                        for search_data in sub_site.figure_search_data:
                            fig_found, reported_confidence = search_data.search(figure, 60)
                            # if search_data.tester.match(figure.name):
                            #     print("we matched " + figure.name)
                            #     break
                            # result = fuzz.token_set_ratio(searchString, figure.name)
                            # if result > 40:
                            if fig_found:
                                found_fig_count += 1
                                if sub_site.matched_reporting == "individually":
                                    message = push_User.send_message(
                                        title="New Figure From {} Available".format(sub_site.description),
                                        message='<a href="' + figure.link + '">' + figure.extended_name + '</a>' +
                                                " in stock. Price: " + figure.price + " Condition: " + figure.condition,
                                        html=True,
                                        url=figure.pic_link,
                                        url_title="Picture",
                                        priority=2
                                        )
                                    logging.warning("Matched figure " + figure.extended_name + " with " +
                                                    str(reported_confidence) + "% confidence against " +
                                                    search_data.fuzzy_search)
                                elif sub_site.matched_reporting == "group":
                                    tmp_msg = "" + '<a href="' + figure.link + '">' + figure.extended_name + '</a>' + "\n"
                                    if (len(push_msgs[num_of_msgs]) + len(tmp_msg)) > 1023:
                                        num_of_msgs += 1
                                        push_msgs.append('')

                                    push_msgs[num_of_msgs] += tmp_msg

                                break  # No need to keep trying to match the figure
                        if not fig_found:
                            ignored_new_figures.append(figure)

                    if sub_site.matched_reporting == "group":
                        try:
                            for msg in push_msgs:
                                safeURL = urljoin(site.url, sub_site.url)
                                message = push_User.send_message(
                                    title="New Matched Figures From {} Available!".format(sub_site.description),
                                    message=msg,
                                    html=True,
                                    priority=-1,
                                    url=safeURL.encode(encoding='UTF-8', errors='strict'),
                                    url_title=sub_site.description,
                                    )
                                logging.warning(msg)
                        except:
                            pass

                    if len(sub_site.discovered_figures) > 0:
                        logging.warning(str(len(sub_site.discovered_figures) - found_fig_count) +
                                        " Other New Figures From {} Detected.".format(sub_site.description))
                        if sub_site.unmatched_reporting == 'group':
                            push_msgs = []
                            num_of_msgs = 0
                            push_msgs.append('')
                            for figure in ignored_new_figures:

                                tmp_msg = "" + '<a href="' + figure.link + '">' + figure.extended_name + '</a>' + "\n"
                                if (len(push_msgs[num_of_msgs]) + len(tmp_msg)) > 1023:
                                    num_of_msgs += 1
                                    push_msgs.append('')

                                push_msgs[num_of_msgs] += tmp_msg

                            for msg in push_msgs:
                                try:
                                    safeURL = urljoin(site.url, sub_site.url)
                                    message = push_User.send_message(
                                        title="New Figures Available from {} that did not match the search criteria"
                                            .format(sub_site.description),
                                        message=msg,
                                        html=True,
                                        priority=-1,
                                        url=safeURL.encode(encoding='UTF-8', errors='strict'),
                                        url_title=sub_site.description,
                                        )
                                    logging.warning(msg)

                                except:
                                    pass
                        elif sub_site.unmatched_reporting == 'individually':
                            pass

        # print("sleeping")
        # time_p.sleep(1)
        # sys.stdout.write('\x1b[K')  # Clear the line
        # iterable = range(int(sleep_time * 60 * 1000))
        # with click.progressbar(iterable) as bar:
        #     for i in bar:  # wait 5 seconds before next request to avoid hammering web servers.
        #         time.sleep(0.001)
        # sys.stdout.write('\x1b[2A')  # Move cursor up 2 lines

        # We need to wait for a bit before the next series of requests to avoid hammering web servers.
        if resume_time is None:
            if resume_freq is not None:
                resume_time = datetime.now() + resume_freq
            else:
                resume_time = datetime.now() + timedelta(minutes=sleep_time)

        pause = True
        while pause:
            time_remaining = resume_time - datetime.now()
            if time_remaining.total_seconds() < 0:
                pause = False
            else:
                hours, remainder = divmod(time_remaining.total_seconds(), 60*60)
                minutes, seconds = divmod(remainder, 60)
                sys.stdout.write('\x1b[1A')  # Move cursor up 1 lines
                sys.stdout.write('\x1b[K')  # Clear the line
                print("{0:1.0f} Hours, {1:1.0f} Minutes, and {2:1.0f} Seconds left until the next update."
                      .format(hours, minutes, seconds))
                time_p.sleep(1)

    input("Press any key to exit")


