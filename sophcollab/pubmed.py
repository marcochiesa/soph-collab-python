from suds.client import Client
import urllib.parse
import logging
import time

logging.basicConfig(level=logging.WARN)
logging.getLogger('suds.client').setLevel(logging.WARN)
logging.getLogger('suds.transport').setLevel(logging.WARN)

class Runner(object):
    def __init__(self, names):
        if names is None:
            raise Exception("null name list")
        self.names = names

    def run(self):
        results = {}
        for name in self.names:
            results[name] = ESearch().search_author(name).item_list()
            #sleep half second to throttle requests per service usage guidelines
            time.sleep(0.5)
        return results

class Entrez(object):
    ENTREZ_WSDL_URL = "http://www.ncbi.nlm.nih.gov/soap/v2.0/eutils.wsdl"
    ENTREZ_ENDPOINT_URL = "http://eutils.ncbi.nlm.nih.gov/soap/v2.0/soap_adapter_2_0.cgi"

    @classmethod
    def get_wsdl_url(cls):
        return cls.ENTREZ_WSDL_URL

    @classmethod
    def get_endpoint_url(cls):
        return cls.ENTREZ_ENDPOINT_URL

    @classmethod
    def build_client(cls):
        return Client(cls.get_wsdl_url(), location=cls.get_endpoint_url())

    @classmethod
    def print_service_methods(cls):
        client = Client(cls.get_wsdl_url())
        print(cls.build_client())

class ESearch(object):
    PUBMED_DB = "pubmed"

    def __init__(self):
        pass

    def search_author(self, name):
        return self.search(name, "author")

    def search(self, termy, fieldy):
        client = Entrez.build_client()
        args = dict(
            db = self._escape(self.PUBMED_DB),
            term = self._escape(termy),
#WebEnv = self._escape(""),
#QueryKey = self._escape("0"),
#usehistory = self._escape("n"),
#tool = self._escape(""),
#email = self._escape(""),
            field = self._escape(fieldy),
#reldate = self._escape("1000"),
#mindate = self._escape("2000"),
#maxdate = self._escape("2014"),
#datetype = self._escape("pdat"),
#RetStart = self._escape("0"),
            RetMax = self._escape("1000"),
#rettype = self._escape("uilist"),
            sort = self._escape("pub date")
            )
        result=client.service.run_eSearch(**args)
#print(result)
        return ESearchResults(result)

    @classmethod
    def _escape(cls, str):
        return urllib.parse.quote_plus(str)

class ESearchResults(object):
    def __init__(self, suds_result):
        if suds_result is None:
            raise Exception("null suds result")
        self.suds_result = suds_result

    # Returns the total number of results in the database regardless of how many
    # results were returned for this service query (returned results subject to
    # RetMax value in request)
    def total(self):
        return int(str(self.suds_result.Count))

    def pagination_start(self):
        return int(str(self.suds_result.RetStart))

    def pagination_size(self):
        return int(str(self.suds_result.RetMax))

    def query_string(self):
        return str(self.suds_result.QueryTranslation)

    def translation_set(self):
        return str(self.suds_result.TranslationSet)

    def print_translation_stack(self):
        return print(self.suds_result.TranslationStack)

    # Returns a generator object to iterate through the translated results
    # (string entries instead of objects representing xml text element)
    def items(self):
        lst = []
        if self.total() > 0:
            lst = self.suds_result.IdList.Id
        return (str(x) for x in lst)

    # Returns a translated, populated list of the results
    def item_list(self):
        return list(self.items())

    def __str__(self):
        return "query: '%s' - total results: %d" % (self.query_string(), self.total())
