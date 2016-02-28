import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from chump import Application  # pip3 install chump
import click
import sys
from colorama import Fore, Back, Style, init
import logging


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

    def get_figures(self, html=None):
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
        next_page_element = paging_tags.find('span', string='Next Page»') #_class='sp04_pl20')  #.find('a').get('href')
        if next_page_element is not None:
            next_page_url = next_page_element.find('a').get('href')
            print("getting " +next_page_url)
            return next_page_url
        else:
            return None

    def get_figures(self, html=None):

        if html is not None and len(self._figures) < 1:
            #Only parse if html is given and the figures array is empty
            more_figures = True
            next_page_url = None
            while(more_figures):
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
                        tempFig.link = urljoin(siteURL, relURL)

                        self._figures.append(tempFig)

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


class Figures:

    def __init__(self, service, html):
        self._service = service.lower()  # type: str
        self._html = html
        self.decoder = Decoder(self._service)
        self.figures = self.decoder.get_figures(self._html)  # type: list[FigureData]

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




def scrape():

    push_app = Application("***REMOVED***")
    push_User = push_app.get_user("***REMOVED***")
    # message = push_User.send_message("Test MSG")

    sites = ["http://jungle-scs.co.jp/sale_en/?page_id=116&cat=313&vw=nk",
             "http://jungle-scs.co.jp/sale_en/?page_id=116&cat=383&vw=nk"]

    siteURL = "http://jungle-scs.co.jp/sale_en/?page_id=116&cat=313&vw=nk"
    # localSite = "test.html"
    localURL = "Jungle.html"
    firstRun = True
    #

    # new_figures = []  # type: list[FigureData]
    old_figures = []  # type: list[FigureData]

    count = 1

    run = True
    while run:

        sys.stdout.write('\x1b[K')  # Clear the line
        print("Scraping Jungle... Scrape# " + str(count))
        count += 1

        siteHTML = requests.get(siteURL).text
        # soup = BeautifulSoup(siteHTML, 'html.parser')

        figures = Figures(Decoder.jungle, siteHTML).figures

        # localHTML = open(localURL, 'r', encoding='UTF8').read()
        # soup = BeautifulSoup(localHTML, 'html.parser')

        # product_soup = soup.find(id='products')

        if firstRun is False:
            # print("Number of figures: " + str(len(figures)))
            for figure in figures:
                figNew = True
                for oldFigure in old_figures:
                    if oldFigure.name == figure.name:
                        figNew = False

                if figNew:
                    message = push_User.send_message(
                        title="New Figure Availible",
                        message='<a href="' + figure.link + '">' + figure.name + '</a>' + " in stock. Price: " + figure.price + " Condition: " + figure.condition,
                        html=True,
                        url=figure.pic_link,
                        url_title="Picture"
                        )
                    logging.warning("Figure " + figure.name + " is new!")

                # if old_figures.count(figure) < 1:
                #     #  figure not found!!
                #     print("Figure " + figure.name + " is new!")

        old_figures[:] = figures[:]
        firstRun = False

        # Display a progress bar during sleep.
        sys.stdout.write('\x1b[K')  # Clear the line
        iterable = range(3 * 60 * 1000)
        with click.progressbar(iterable) as bar:
            for i in bar:  # wait 5 seconds before next request to avoid hammering web servers.
                time.sleep(0.001)
        sys.stdout.write('\x1b[2A')  # Move cursor up 2 lines

    input("Press enter to exit")



if __name__ == '__main__':
    init()
    logging.basicConfig(format='%(asctime)s %(message)s', filename='altChecker.log', level=logging.WARNING)
    logging.warning("altchecker.py has started")
    scrape()
