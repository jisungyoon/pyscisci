import os
import json
import gzip

import pandas as pd
import numpy as np
from nameparser import HumanName
import requests
from lxml import etree

from pyscisci.datasource.readwrite import load_preprocessed_data, load_int, load_float, load_html_str
from pyscisci.database import BibDataBase

class DBLP(BibDataBase):
    """
    Base class for DBLP interface.

    The DBLP comes as a single xml file.

    There is no citation information!

    Explain downloading etc.

    """

    def __init__(self, path2database = '', keep_in_memory = False):

        self.path2database = path2database
        self.keep_in_memory = keep_in_memory

        self._affiliation_df = None
        self._pub_df = None
        self._author_df = None
        self._pub2year = None
        self._pub2ref_df = None
        self._pub2refnoself_df = None
        self._author2pub_df = None
        self._paa_df = None

        self.PublicationIdType = int
        self.AffiliationIdType = int
        self.AuthorIdType = str

    def _blank_dblp_publication(self, PublicationId = 0):
        record = {}
        record['PublicationId'] = PublicationId
        record['Title'] = ''
        record['Year'] = 0
        record['Volume'] = 0
        record['Number'] = ''
        record['Pages'] = ''
        record['JournalId'] = 0
        record['Doi'] = ''
        record['DOI'] = ''
        record['TeamSize'] = 0
        record['Month'] = 1

        return record

    def _clear_element(element):
        """Free up memory for temporary element tree after processing the element"""
        element.clear()
        while element.getprevious() is not None:
            del element.getparent()[0]

    def preprocess(self, file_name = 'dblp.xml.gz', process_name = True, num_file_lines=10**7):
        """
        Bulk preprocess the DBLP raw data.

        """

        ACCEPT_DOCTYPES = set(['article', 'inproceedings', 'proceedings', 'book', 'incollection', 'phdthesis', 'mastersthesis'])
        REGJECT_DOCTYPES = set(['www'])
        DATA_ITEMS = ['title', 'booktitle', 'year', 'journal', 'ee',' url', 'month', 'mdate', 'isbn', 'publisher']
        SKIP_FIELDS = ['note', 'cite', 'cdrom', 'crossref', 'editor',  'series', 'tt', 'school', 'chapter', 'address']

        doctype = {'article': 'j', 'book':'b', '':'', 'phdthesis':'phd', 'proceedings':'c', 'inproceedings':'c',
        'mastersthesis':'ms'}

        html_format_keys = ['<sub>', '</sub>', '<sup>', '</sup>', '<i>', '</i>']


        if not os.path.exists(os.path.join(self.path2database, 'publication')):
            os.mkdir(os.path.join(self.path2database, 'publication'))

        if not os.path.exists(os.path.join(self.path2database, 'author')):
            os.mkdir(os.path.join(self.path2database, 'author'))

        if not os.path.exists(os.path.join(self.path2database, 'publicationauthor')):
            os.mkdir(os.path.join(self.path2database, 'publicationauthor'))

        with gzip.open(os.path.join(self.path2database, file_name), 'r') as infile:
            xml_file = infile.read()
        xml_file = gzip.decompress(xml_file).decode('ISO-8859-1')

        publication_df = []
        author_df = []
        paa_df = []
        journal_df = []

        PublicationId = 1
        AuthorId = 1
        aname2aid = {}
        author_columns = ['AuthorId', 'FullName']
        if process_name:
            author_columns += ['LastName', 'FirstName', 'MiddleName']
        JournalId = 1
        jname2jid = {}

        pub_record = self._blank_dblp_publication(PublicationId)
        pub_authors = []

        ifile = 0

        # extract the desired fields from the XML tree
        xmltree = etree.iterparse(xml_file, dtd_validation=True, load_dtd=True)

        for event, elem in xmltree:
            if elem.tag == 'title' or elem.tag == 'booktitle':
                pub_record['Title'] = load_html_str(elem.text)

            elif elem.tag == 'year':
                pub_record['Year'] = load_int(elem.text)

            elif elem.tag == 'month':
                pub_record['Month'] = load_int(elem.text)

            elif elem.tag == 'volume':
                pub_record['Volume'] = clean_number(elem.text)

            elif elem.tag == 'number':
                pub_record['Number'] = load_html_str(elem.text)

            elif elem.tag == 'pages':
                pub_record['Pages'] = load_html_str(elem.text)

            elif elem.tag == 'journal':
                pub_record['JournalId'] = load_html_str(elem.text)

            elif elem.tag == 'url':
                pub_record['URL'] = load_html_str(elem.text)

            elif elem.tag == 'ee':
                pub_record['Doi'] = load_html_str(elem.text)

            elif elem.tag == 'author':
                AuthorCount += 1
                fullname = load_html_str(elem.text)
                if aname2aid.get(fullname, None) is None:
                    if process_name:
                        hname = HumanName(fullname)
                        author_df.append([AuthorId, fullname, hname.last, hname.first, hname.middle])
                    else:
                        author_df.append([AuthorId, fullname])
                    aname2aid[fullname] = AuthorId
                    AuthorId += 1

                pub_authors.append([PublicationId, aname2aid[fullname], AuthorCount])

            elif elem.tag in ACCEPT_DOCTYPES:
                pub_record['TeamSize'] = AuthorCount
                pub_record['DocType'] = doctype[load_html_str(elem.tag)]

                publication_df.append(pub_record)
                paa_df.extend(pub_authors)
                PublicationId += 1
                pub_record = self._blank_dblp_publication(PublicationId)
                AuthorCount = 0
                pub_authors = []

                if num_file_lines > 0 and (PublicationId % num_file_lines) == 0:

                    publication_df = pd.DataFrame(publication_df)
                    publication_df.to_hdf( os.path.join(path2database,'publication', 'publication{}.hdf'.format(ifile)), key = 'pub', mode='w')

                    author_df = pd.DataFrame(author_df, columns = author_columns)
                    author_df.to_hdf( os.path.join(path2database,'author', 'author{}.hdf'.format(ifile)), key = 'author', mode='w')

                    paa_df = pd.DataFrame(paa_df, columns = ['PublicationId', 'AuthorId', 'AuthorOrder'])
                    paa_df.to_hdf( os.path.join(path2database,'publicationauthor', 'publicationauthor{}.hdf'.format(ifile)), key = 'pa', mode='w')

                    ifile += 1

                    publication_df = []
                    author_df = []
                    paa_df = []

            elif elem.tag in REJECT_DOCTYPES:
                # the record was from a rejected category so reset record
                pub_record = self._blank_dblp_publication(PublicationId)
                AuthorCount = 0
                pub_authors = []

            elif elem.tag in SKIP_FIELDS:
                pass

        publication_df = pd.DataFrame(publication_df)
        publication_df.drop_duplicates(keep='first', inplace=True)
        publication_df.to_hdf( os.path.join(path2database,'publication', 'publication{}.hdf'.format(ifile)), key = 'pub', mode='w')

        author_df = pd.DataFrame(author_df, columns = author_columns)
        author_df.drop_duplicates(keep='first', inplace=True)
        author_df.to_hdf( os.path.join(path2database,'author', 'author{}.hdf'.format(ifile)), key = 'author', mode='w')

        paa_df = pd.DataFrame(paa_df, columns = ['PublicationId', 'AuthorId', 'AuthorOrder'])
        paa_df.drop_duplicates(keep='first', inplace=True)
        paa_df.to_hdf( os.path.join(path2database,'publicationauthor', 'publicationauthor{}.hdf'.format(ifile)), key = 'pa', mode='w')




    def download_from_source(self, source_url='https://dblp.uni-trier.de/xml/', file_name = 'dblp.xml.gz'):

        with gzip.open(os.path.join(self.path2database, file_name), "w") as outfile:
            outfile.write(requests.get(os.path.join(source_url, file_name)).content)

    def parse_affiliations(self, preprocess = False):
        raise NotImplementedError("DBLP is stored as a single xml file.  Run preprocess to parse the file.")

    def parse_authors(self, preprocess = False, process_name = True, num_file_lines = 5*10**6):
        raise NotImplementedError("DBLP is stored as a single xml file.  Run preprocess to parse the file.")

    def parse_publications(self, preprocess = False, num_file_lines=10**7):
        raise NotImplementedError("DBLP is stored as a single xml file.  Run preprocess to parse the file.")

    def parse_references(self, preprocess = False, num_file_lines=10**7):
        raise NotImplementedError("DBLP does not contain reference or citation information.")

    def parse_publicationauthoraffiliation(self, preprocess = False, num_file_lines=10**7):
        raise NotImplementedError("DBLP is stored as a single xml file.  Run preprocess to parse the file.")

    def parse_fields(self, preprocess = False, num_file_lines=10**7):
        raise NotImplementedError("DBLP does not contain field information.")
