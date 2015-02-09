from . import pubmed
#import pubmed
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
        name_parts = self.collapse_string(name_parts)

        match = self.LAST_NAME_FIRST_PATTERN.match(name_parts)
        if match is not None:
            last = match.group(1).strip()
            rest = match.group(2).strip()
        else:
            arr = name_parts.split(self.SPACE)
            last = arr[-1]
            rest = self.SPACE.join(arr[:-1])

        arr = rest.split(self.SPACE)
        first = arr[0]
        rest = self.SPACE.join(arr[1:])

        self.first_name = first
        self.middle_name = rest
        self.last_name = last
        self.name = self.collapse_string(self.SPACE.join([first, rest, last]))

    def full_name(self):
        return self.name

    def short_name(self):
        return self.collapse_string(self.SPACE.join([self.first_name, self.last_name]))
        
    @classmethod
    def collapse_string(cls, s):
        # Strip leading and trailing whitespace
        s = s.strip()
        # Condense multiple whitespace characters to one space
        s = cls.WHITESPACE_PATTERN.sub(cls.SPACE, s)
        return s

class PubmedNameSearch(object):

    # expects name_list to be a list of strings (no end of line characters)
    def __init__(self, name_list):
        if name_list is None:
            raise Exception("null name list")
        self.name_list = [NameParser(x.strip()).name for x in name_list]
        self.author_container = AuthorContainer()

    def article_counts_by_name(self, progress_observer = None):
        m = pubmed.ArticleCountByNameRunner(self.name_list).run(self.author_container, progress_observer)
        return {k:len(v) for k, v in m.items()}

    def build_author_graph(self, progress_observer = None):
        m = pubmed.BuildAuthorGraphRunner(self.name_list).run(self.author_container, progress_observer)
        return m

    def collaboration_report(self, progress_observer = None):
        author_graph = self.build_author_graph(progress_observer)
        data = {}
        for name, author in author_graph.items():
            article_count = author.get_article_count()
            collaborators = author.get_collaborators()
            collaborator_count = len(collaborators)
            num_soph = 0
            num_uab = 0
            num_other = 0
            num_unknown = 0
            for collaborator in collaborators:
                if author.is_soph():
                    num_soph += 1 
                if author.is_uab():
                    num_uab += 1
                if author.is_other():
                    num_other += 1
                if author.is_unknown():
                    num_unknown += 1
            data[name] = [article_count, collaborator_count, num_uab, num_soph, num_other, num_unknown]

        labels = ["Num of Articles", "Num of Collaborators", "Num from UAB", "Num from UAB SoPH", "Num from Other Institutions", "Num with Unknown Affiliation"]
        return {"data": data, "labels": labels}

class AuthorContainer(object):
    def __init__(self):
        self.authors = {}

    def get_author(self, name):
        parser = NameParser(name)
        full = parser.full_name()
        short = parser.short_name()
        if full in self.authors:
            author = self.authors[full]
        elif short in self.authors:
            author = self.authors[short]
        else:
            author = Author(full)
            self.authors[full] = author

        return author

    def get_authors(self):
        return dict(self.authors)


class Author(object):
    def __init__(self, name):
        self.name = name
        self.articles = set()
        self.affiliation = ""

    def get_article_count(self):
        return len(self.articles)

    def get_articles(self):
        return set(self.articles)

    def add_article(self, article):
        self.articles.add(article)

    def set_affiliation(self, affiliation):
        self.affiliation = affiliation

    def get_collaborators(self):
        collaborators = set()
        for article in self.articles:
            for author in article.get_authors():
                if author != self:
                    collaborators.add(author)
        return collaborators

    def is_uab(self):
        return "University of Alabama at Birmingham" in self.affiliation

    def is_soph(self):
        return "School of Public Health" in self.affiliation

    def is_other(self):
        return self.affiliation and not self.is_soph() and not self.is_uab()

    def is_unknown(self):
        return not self.affiliation


class Article(object):
    def __init__(self, article_id, title, abstract):
        self.article_id = article_id
        self.title = title
        self.abstract = abstract
        self.authors = set()

    def add_author(self, author):
        author.add_article(self)
        self.authors.add(author)

    def get_author_count(self):
        return len(self.authors)

    def get_authors(self):
        return set(self.authors)

def main():
    pubmed.DEBUG = True

    """
    article_counts = PubmedNameSearch(["Stephen Mennemeyer"]).article_counts_by_name()
    for name, count in article_counts.items():
        print(name, count)
    """

#name_search = PubmedNameSearch(["Allison DB"])
    name_search = PubmedNameSearch(["Stephen Mennemeyer"])
    author_list = name_search.build_author_graph()
#for name, author in name_search.author_container.get_authors().items():
    for name, author in author_list.items():
        print(author.name + (" - UAB" if author.is_uab() else ""))
        if author.affiliation:
            print(author.affiliation)
        collaborators = author.get_collaborators()
        print("  collaborator count: " + str(len(collaborators)))
        for collaborator in collaborators:
            print("    " + collaborator.name)
        article_count = author.get_article_count()
        print("  article count: " + str(article_count))
        if article_count > 0:
            print("  articles:")
        for article in author.get_articles():
            print("    " + article.article_id + " - " + article.title)
            author_count = article.get_author_count()
            print("      author count: " + str(author_count))
            for collaborator in article.get_authors():
                print("      " + collaborator.name, end="")
                if collaborator == author:
                    print(" (author)")
                elif collaborator.is_soph():
                    print(" (SoPH)")
                elif collaborator.is_uab():
                    print(" (UAB)")
                else:
                    print("(N/A)")

if __name__ == '__main__':
    main()
