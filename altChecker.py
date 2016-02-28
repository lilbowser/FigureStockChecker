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

    def condition(self, value):
        raise NotImplementedError


class JungleDecoder(Decoder):

    conditionBase = "http://jungle-scs.co.jp/sale_en/wp-content/themes/jungle_2013en/images/"
    conditionS = "conditionicon_s_en.gif"
    conditionA = "conditionicon_a_en.gif"
    conditionB = "conditionicon_b_en.gif"
    conditionDecode = {conditionS: 'Sealed', conditionA: 'A', conditionB: 'B'}

    def condition(self, value):
        return self.conditionDecode[value]


class FigureData:

    def __init__(self):
        self.name = None  # type: str
        self.price = None  # type: str
        self.link = None    # type: str
        self.pic_link = None  # type: str
        self._condition = None  # type: str


    @property
    def condition(self):
        return self._condition

    @condition.setter
    def condition(self, value):
        if self._condition is None:
            tmp = value[value.rindex('/') + 1:]
            self._condition = JungleDecoder.conditionDecode[tmp]
        else:
            raise ValueError("Can not set condition once condition has already been set.")




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

    new_figures = []  # type: list[FigureData]
    old_figures = []  # type: list[FigureData]

    count = 1
    # print("Scraping Jungle...")
    while(True):

        sys.stdout.write('\x1b[K')  # Clear the line
        print("Scraping Jungle... Scrape# " + str(count))
        count+=1
        siteHTML = requests.get(siteURL).text

        soup = BeautifulSoup(siteHTML, 'html.parser')

        # localHTML = open(localURL, 'r', encoding='UTF8').read()
        # soup = BeautifulSoup(localHTML, 'html.parser')

        product_soup = soup.find(id='products')

        try:
            test = product_soup.find_all("li")
        except AttributeError as e:
            print(e)
            test = []

        for figure_soup in test:
            tempFig = FigureData()
            tempFig.name = figure_soup.find(class_='wrapword').text
            # print(tempFig.name)

            tempFig.price = figure_soup.find(class_="price").text
            # print(tempFig.price)

            tempFig.pic_link = figure_soup.find('img')['src']
            # print(tempFig.pic_link)

            relURL = figure_soup.find('a').get('href')
            tempFig.link = urljoin(siteURL, relURL)
            # print(tempFig.link)

            tempFig.condition = figure_soup.find('p').find_all('img')[1]['src']

            # print(tempFig.condition)

            if firstRun:
                old_figures.append(tempFig)
                new_figures.append(tempFig)
            else:
                new_figures.append(tempFig)
            # print('')

        for figure in new_figures:
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

        old_figures[:] = new_figures[:]

        firstRun = False

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
