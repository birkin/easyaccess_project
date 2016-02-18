# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json, logging, pprint
from django.conf import settings
from django.http import QueryDict
from django.test import Client, TestCase
from findit.classes.citation_form_helper import CitationFormHelper


log = logging.getLogger('access')
TestCase.maxDiff = None


class CitationFormHelperTest( TestCase ):
    """ Checks helper functions. """

    def setUp(self):
        self.helper = CitationFormHelper()
        self.qdct = QueryDict( '', mutable=True )

    ## make_form_dct() checks ##

    def test_make_form_dct__oclc_value(self):
        """ Checks removal of accessionnumber tags. """
        dct = { 'some_oclc_key': '<accessionnumber>1234</accessionnumber>' }
        self.qdct.update(dct)
        self.assertEqual(
            # { 'some_oclc_key': '1234' },
            {u'volume': u'', u'some_oclc_key': u'1234', u'issue': u'', u'atitle': u'Unknown' },
            self.helper.make_form_dct( self.qdct )
            )

    def test_make_form_dct__id_and_doi(self):
        """ Checks removal of 'doi' from value. """
        dct = { 'id': 'doi:1234' }
        self.qdct.update(dct)
        self.assertEqual(
            {u'volume': u'', u'issue': u'', u'id': u'1234', u'atitle': u'Unknown'},
            self.helper.make_form_dct( self.qdct )
            )

    def test_make_form_dct__doi_key(self):
        """ Checks conversion of doi-key to id-key. """
        dct = { 'doi': '1234' }
        self.qdct.update(dct)
        self.assertEqual(
            {u'atitle': u'Unknown', u'id': u'1234', u'issue': u'', u'volume': u''},
            self.helper.make_form_dct( self.qdct )
            )

    def test_make_form_dct__simple_isbn(self):
        """ Checks plain isbn. """
        dct = { 'isbn': '1234' }
        self.qdct.update(dct)
        self.assertEqual(
            { 'isbn': '1234' }, self.helper.make_form_dct( self.qdct )
            )

    def test_make_form_dct__book_openurl(self):
        """ Checks large openurl. """
        dct = {
            'aufirst': 'T\u014dichi',
            'aulast': 'Yoshioka',
            'date': '1978',
            'genre': 'book',
            'id': '',
            'pid': '6104671<fssessid>0</fssessid><edition>1st ed.</edition>',
            'req_dat': '<sessionid>0</sessionid>',
            'rfe_dat': '6104671',
            'rfr_id': 'info:sid/firstsearch.oclc.org:WorldCat',
            'rft.aufirst': 'T\u014dichi',
            'rft.aulast': 'Yoshioka',
            'rft.btitle': 'Zen',
            'rft.date': '1978',
            'rft.edition': '1st ed.',
            'rft.genre': 'book',
            'rft.place': 'Osaka  Japan',
            'rft.pub': 'Hoikusha',
            'rft_id': 'info:oclcnum/6104671',
            'rft_val_fmt': 'info:ofi/fmt:kev:mtx:book',
            'sid': 'FirstSearch:WorldCat',
            'title': 'Zen',
            'url_ver': 'Z39.88-2004'}
        self.qdct.update(dct)
        self.assertEqual(
            {u'au': u'Yoshioka, T\u014dichi',
             u'aufirst': u'T\u014dichi',
             u'aulast': u'Yoshioka',
             u'date': u'1978',
             u'genre': u'book',
             u'id': u'',
             u'pid': u'6104671<fssessid>0</fssessid><edition>1st ed.</edition>',
             u'req_dat': u'<sessionid>0</sessionid>',
             u'rfe_dat': u'6104671',
             u'rfr_id': u'info:sid/firstsearch.oclc.org:WorldCat',
             u'rft.aufirst': u'T\u014dichi',
             u'rft.aulast': u'Yoshioka',
             u'rft.btitle': u'Zen',
             u'rft.date': u'1978',
             u'rft.edition': u'1st ed.',
             u'rft.genre': u'book',
             u'rft.place': u'Osaka  Japan',
             u'rft.pub': u'Hoikusha',
             u'rft_id': u'info:oclcnum/6104671',
             u'rft_val_fmt': u'info:ofi/fmt:kev:mtx:book',
             u'sid': u'FirstSearch:WorldCat',
             u'title': u'Zen',
             u'url_ver': u'Z39.88-2004'}, self.helper.make_form_dct( self.qdct )
            )

    # end class CitationFormHelperTest


class CitationFormClientTest( TestCase ):
    """ Checks citation form via Client. """

    def setUp(self):
        self.client = Client()

    def test_plain_get(self):
        """ Checks plain form. """
        response = self.client.get( '/find/citation_form/' )  # project root part of url is assumed
        self.assertEqual( 200, response.status_code )
        self.assertEqual( True, '<input type="radio" name="form" value="article">Article' in response.content.decode('utf-8') )
        for key in ['article_form', 'book_form', 'csrf_token', 'form_type', 'messages', 'problem_link' ]:
            self.assertTrue( key in response.context.keys(), 'key `%s` not found' % key )

    def test_get_isbn_parameter(self):
        """ Checks incorporation of param into form. """
        response = self.client.get( '/find/citation_form/?isbn=9780439339117' )  # project root part of url is assumed
        # print response.content
        self.assertEqual( 200, response.status_code )
        self.assertEqual( True, '9780439339117' in response.content.decode('utf-8') )
        self.assertEqual( 'book', response.context['form_type'] )
        # pprint.pformat( response.context )
        for key in ['article_form', 'book_form', 'csrf_token', 'form_type', 'messages', 'problem_link' ]:
            self.assertTrue( key in response.context.keys(), 'key `%s` not found' % key )

    def test_get_doi_parameter(self):
        """ Checks incorporation of param into form. """
        response = self.client.get( '/find/citation_form/?doi=12611747' )  # project root part of url is assumed
        # print response.content
        self.assertEqual( 200, response.status_code )
        self.assertEqual( True, '12611747' in response.content.decode('utf-8') )
        self.assertEqual( 'article', response.context['form_type'] )
        pprint.pformat( response.context )
        for key in ['article_form', 'book_form', 'csrf_token', 'form_type', 'messages', 'problem_link' ]:
            self.assertTrue( key in response.context.keys(), 'key `%s` not found' % key )

    # end class CitationFormClientTest
