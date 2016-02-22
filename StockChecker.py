import requests # pip3 install requests
from bs4 import BeautifulSoup  # pip3 install beautifulsoup4
import xml.etree.ElementTree as ET

class WebsiteData:

    def __init__(self, website_xml):
        """
        This is a data type for holding and processing all info relating to a webpage
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

            self._sub_sites = []  # type: list [SubSiteData]
            for sub_site_xml in self._website_xml.findall('sub_site'):
                self._sub_sites.append(SubSiteData(sub_site_xml))

            for subSite in self._sub_sites:
                print(self._base_url + subSite.url)

        except Exception as e:
            print("Could not load data for " + self._website_name + ". Error: " + str(e))
            self._website_xml = None
            self._base_url = ""
            self._sub_sites = None

    @property
    def sub_sites(self):
        """

        @return: Returns a list of SubSiteData
        @rtype: list [SubSiteData]
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
        self._xml = sub_site_xml
        self._url = self._xml.find('url').text

        self._website_data = None
        self._website_soup = None
        self.product_soup = None
        self.figure_soup = None

        self._figures = []

        for fig in self._xml.findall('figure'):
            self._figures.append(Figure(fig))

        self._scraped_figures = []

    @property
    def figures(self):
        """
        A collection of figure objects
        @return: list[Figure]
        @rtype: list[Figure]
        """
        return self._figures

    @property
    def url(self):
        """
        The url associated with a subsite.
        @return: Returns the url associated with a subsite.
        @rtype: str
        """
        return self._url
    @property
    def website_data(self):
        """
        Returns all HTML data scraped from the website
        @return: Website associated with subsite url
        @rtype: str | None
        """
        return self._website_data
    @website_data.setter
    def website_data(self, value):
        """
        Stores the website HTML data and computes the soup from it
        @param value: Website HTML
        @type value: str
        @return:
        @rtype:
        """
        self._website_data = value
        if self._website_data is not None:
            self._website_soup = BeautifulSoup(self._website_data, "html.parser")
        else:
            self._website_soup = None

    @property
    def website_soup(self):
        """
        Returns all HTML soup from the website
        @return: Website Soup associated with subsite url
        @rtype: BeautifulSoup | None
        """
        return self._website_soup

    # @property
    # def new_figure(self):
    #     """
    #     creates a
    #     @return: Website associated with subsite url
    #     @rtype: str | None
    #     """
    #     return self._website_data
    # @new_figure.setter
    # def new_figure(self, value):
    #     """
    #     Stores the website HTML data and computes the soup from it
    #     @param value: Website HTML
    #     @type value: str
    #     @return:
    #     @rtype:
    #     """
    #     self._website_data = value

    def new_figure(self, name=None, link=None, price=None, picture_link=None):
        """
        Creates a new scraped figure from soup and adds it to the database.

        @return:
        @rtype:
        """
        self._scraped_figures.append(ScrapedFigure(name, link, price, picture_link))



class ScrapedFigure:
    def __init__(self, figure_name=None, link=None, price=None, picture_link=None):
        self._figure_name = figure_name
        self._link = link
        self._price = price
        self._picture_link = picture_link


class Figure:

    def __init__(self, figure_xml):
        self._xml = figure_xml

        self._figure_name = self._xml.attrib['name']
        self._search_parameters = []

        for search_xml in self._xml.findall('search'):
            self._search_parameters.append(SearchParam(search_xml))


    @property
    def figure_name(self):
        """
        The name of the figure we are searching for
        @return: figure name
        @rtype: str
        """
        return self._figure_name


class SearchParam:

    def __init__(self, search_param_xml):
        self._xml = search_param_xml
        self.search_parameter = self._xml.text
        self.dependence = self._xml.attrib['dependence']


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
                sub_site.website_data = scrapeSite(site.url + sub_site.url)
                products_soup = []
                if sub_site.website_soup is not None:
                    sub_site.product_soup = sub_site.website_soup.find(id="products")
                    sub_site.figure_soup = sub_site.product_soup.find_all('li')
                    for figure in sub_site.figure_soup:
                        sub_site.new_figure(name=figure.find(class_="wrapword").text,
                                            price=figure.find(class_="price").text

                                            )
                        temp=figure.find(class_="left").find(itemprop="img")
                        print("woo")


    #Search for Items





    input("Press any key to exit")

