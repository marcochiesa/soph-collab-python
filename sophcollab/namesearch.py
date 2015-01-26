from . import pubmed
import re

class NameParser(object):
    SPACE = " "
    COMMA = ","
    WHITESPACE_PATTERN = re.compile(r"\s+")
    NAME_CHAR = "[-a-zA-Z]"
    LAST_NAME_FIRST_PATTERN = re.compile("^(%s*) ?, ?(%s*)$" % (NAME_CHAR, NAME_CHAR))

    def __init__(self, name_parts):
        if name_parts is None:
            raise Exception("null name parts")

        # Clean name
        # Strip leading and trailing whitespace
        name_parts = name_parts.strip()
        # Condense multiple whitespace characters to one space
        name_parts = self.WHITESPACE_PATTERN.sub(self.SPACE, name_parts)

        last = ""
        rest = name_parts
        match = self.LAST_NAME_FIRST_PATTERN.match(name_parts)
        if match is not None:
            last = match.group(1).strip()
            rest = match.group(2).strip()

        self.name = rest
        if last:
            self.name += " " + last

    def get_name(self):
        return self.name

class PubmedNameSearch(object):

    # expects name_list to be a list of strings (no end of line characters)
    def __init__(self, name_list):
        if name_list is None:
            raise Exception("null name list")
        self.name_list = [NameParser(x.strip()).get_name() for x in name_list]

    def article_counts_by_name(self, progress_observer = None):
        m = pubmed.Runner(self.name_list).run(progress_observer)
        return {k:len(v) for k, v in m.items()}
