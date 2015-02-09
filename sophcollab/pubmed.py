import urllib
import urllib.parse
import urllib.request
import xml.etree.ElementTree
import logging
import time
#import namesearch
from . import namesearch

DEBUG = False
TRACE = False

logging.basicConfig(level=logging.WARN)
logging.getLogger('suds.client').setLevel(logging.WARN)
logging.getLogger('suds.transport').setLevel(logging.WARN)

URL_SEPARATOR = "/"
QUERY_SEPARATOR = "?"
PUBMED_DB = "pubmed"

class Runner(object):
    PROGRESS_UPDATE_BATCH_SIZE = 1

    def __init__(self, names):
        if names is None:
            raise Exception("null name list")
        self.names = names

    def run(self, author_container = None, progress_observer = None):
        results = {}
        loop = 0
        for name in self.names:
            loop += 1
            results[name] = self.run_name(name, author_container)
            if loop >= self.PROGRESS_UPDATE_BATCH_SIZE and progress_observer is not None:
                progress_observer(len(results), len(self.names))
                loop = 0
            #sleep half second to throttle requests per service usage guidelines
            time.sleep(0.5)
        return results

    def run_name(self, name, author_container):
        pass

# Builds dictionary of name (string) to list of article IDs 
class ArticleCountByNameRunner(Runner):
    def run_name(self, name, author_container):
        return ESearch().search_author(name).items()

# Builds name (string) to Author dictionary
class BuildAuthorGraphRunner(Runner):
    PUBMED_ARTICLE_SET_TAG = "PubmedArticleSet"
    PUBMED_ARTICLE_TAG = "PubmedArticle"
    PMID_TAG = "PMID"
    ARTICLE_TAG = "Article"
    ARTICLE_TITLE_TAG = "ArticleTitle"
    ABSTRACT_TAG = "Abstract"
    ABSTRACT_TEXT_TAG = "AbstractText"
    AUTHOR_LIST_TAG = "AuthorList"
    AUTHOR_TAG = "Author"
    LAST_NAME_TAG = "LastName"
    FORE_NAME_TAG = "ForeName"
    AFFILIATION_INFO_TAG = "AffiliationInfo"
    AFFILIATION_TAG = "Affiliation"

    def run_name(self, name, author_container):
        author = author_container.get_author(name)
        article_id_list = ESearch().search_author(author.name).items()
        for article_id in article_id_list:
            article_xml = EFetch().search_article(article_id)
            self.parse_xml_article(article_xml, author_container)
        return author

    def parse_xml_article(self, article_set_xml, author_container):
        xml_root = xml.etree.ElementTree.fromstring(article_set_xml) #root element
        if xml_root.tag != self.PUBMED_ARTICLE_SET_TAG:
            raise Exception("invalid xml content: " + article_xml)

        for pubmed_article_tag in xml_root.findall(self.PUBMED_ARTICLE_TAG):
            pmid_tag = pubmed_article_tag.find(".//"+self.PMID_TAG)
            article_id = pmid_tag.text
            article_tag = pubmed_article_tag.find(".//"+self.ARTICLE_TAG)
            title = article_tag.find(self.ARTICLE_TITLE_TAG).text
            abstract = ""
            abstract_tag = article_tag.find(self.ABSTRACT_TAG)
            if abstract_tag is not None:
                for abstract_text_tag in abstract_tag.findall(self.ABSTRACT_TEXT_TAG):
                    abstract += abstract_text_tag.text
            article = namesearch.Article(article_id, title, abstract)
            for author_tag in article_tag.find(self.AUTHOR_LIST_TAG).findall(self.AUTHOR_TAG):
                fore_name_tag = author_tag.find(self.FORE_NAME_TAG)
                first_name = fore_name_tag.text if fore_name_tag is not None else ""
                last_name_tag = author_tag.find(self.LAST_NAME_TAG)
                last_name = last_name_tag.text if last_name_tag is not None else ""
                author = author_container.get_author(first_name + " " + last_name)
                affiliation_tag = author_tag.find("./" + self.AFFILIATION_INFO_TAG + "/" + self.AFFILIATION_TAG)
                if affiliation_tag is not None and not author.affiliation:
                    author.set_affiliation(affiliation_tag.text)
                article.add_author(author)
            
            
class Entrez(object):
    ENTREZ_HOST = "eutils.ncbi.nlm.nih.gov"
    ENTREZ_PATH = "entrez/eutils"
    ENTREZ_SCHEME = "http://"

    @classmethod
    def get_endpoint_url(cls, script):
        return cls.ENTREZ_SCHEME + cls.ENTREZ_HOST + URL_SEPARATOR + cls.ENTREZ_PATH + URL_SEPARATOR + str(script)

    # args should be a dictionary of query string parameters
    @classmethod
    def query_endpoint(cls, query_url, args):
        global DEBUG
        global TRACE
        data = urllib.parse.urlencode(args)
        if DEBUG:
            print("***query data: " + data)
        response = urllib.request.urlopen(query_url + QUERY_SEPARATOR + data)
        result = response.read()
        if TRACE:
            print(result)
        return result

class ESearch(object):
    ESEARCH_SCRIPT = "esearch.fcgi"

    def __init__(self):
        pass

    def search_author(self, name):
        return self.search(name, "author")

    def search(self, termy, fieldy):
        url = Entrez.get_endpoint_url(self.ESEARCH_SCRIPT)
        args = dict(
            db = PUBMED_DB,
            term = termy,
#WebEnv = "",
#QueryKey = "0",
#usehistory = "n",
#tool = "",
#email = "",
            field = fieldy,
#reldate = "1000",
#mindate = "2000",
#maxdate = "2014",
#datetype = "pdat",
#RetStart = "0",
            RetMax = "1000",
#rettype = "uilist",
            sort = "pub date"
            )

        return ESearchResults(Entrez.query_endpoint(url, args))


class ESearchResults(object):

    RESULT_TAG = "eSearchResult"
    COUNT_TAG = "Count"
    RET_START_TAG = "RetStart"
    RET_MAX_TAG = "RetMax"
    QUERY_TRANSLATION_TAG = "QueryTranslation"
    ID_LIST_TAG = "IdList"
    ID_TAG = "Id"

    def __init__(self, xml_text):
        if xml_text is None:
            raise Exception("null suds result")
        self.xml = xml.etree.ElementTree.fromstring(xml_text) #root element
        if self.xml.tag != self.RESULT_TAG:
            raise Exception("invalid response: " + xml_text)

    # Returns the total number of results in the database regardless of how many
    # results were returned for this service query (returned results subject to
    # RetMax value in request)
    def total(self):
        return int(str(self.xml.find(self.COUNT_TAG).text))

    def pagination_start(self):
        return int(str(self.xml.find(self.RET_START_TAG).text))

    def pagination_size(self):
        return int(str(self.xml.find(self.RET_MAX_TAG).text))

    def query_string(self):
        return str(self.xml.find(self.QUERY_TRANSLATION_TAG).text)

    # Returns a list of string values (pubmed database IDs)
    def items(self):
        result = []
        if self.total() > 0:
            lst = self.xml.find(self.ID_LIST_TAG).findall(self.ID_TAG)
            result = [x.text for x in lst]
        return result

    def __str__(self):
        return "query: '%s' - total results: %d" % (self.query_string(), self.total())


class EFetch(object):
    EFETCH_SCRIPT = "efetch.fcgi"

    def __init__(self):
        pass

    def search_article(self, article_id):
        url = Entrez.get_endpoint_url(self.EFETCH_SCRIPT)
        args = dict(
            db = PUBMED_DB,
            id = article_id,
            retmode = "xml"
            )

        return Entrez.query_endpoint(url, args)

