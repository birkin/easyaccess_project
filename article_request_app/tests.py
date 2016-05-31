# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging, os, pprint
from .classes.login_helper import LoginHelper
from django.conf import settings
from django.http import HttpRequest
from django.test import Client, TestCase
from django.utils.module_loading import import_module


log = logging.getLogger( 'access' )
TestCase.maxDiff = None


class SessionHack(object):
    ## based on: http://stackoverflow.com/questions/4453764/how-do-i-modify-the-session-in-the-django-test-framework

    def __init__(self, client):
        ## workaround for issue: http://code.djangoproject.com/ticket/10899
        settings.SESSION_ENGINE = 'django.contrib.sessions.backends.file'
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()
        self.session = store
        client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key


class ViewsTest( TestCase ):
    """ Tests views via Client. """

    def setUp(self):
        self.client = Client()
        self.session_hack = SessionHack( self.client )

    def test_direct_login_no_session(self):
        """ If not from '/easyaccess/find/', should redirect to index page. """
        response = self.client.get( '/article_request/login_handler/?a=b', SERVER_NAME="127.0.0.1" )  # project root part of url is assumed
        self.assertEqual( 302, response.status_code )
        redirect_url = response._headers['location'][1]
        self.assertEqual( '/find/?a=b', redirect_url )

    def test_direct_login_good_session(self):
        """ If a good request, should redirect to display submission page. """
        # session = self.session_hack.session
        # session['last_path'] = '/easyaccess/find/'
        # session['last_querystring'] = 'foo'
        # session.save()
        response = self.client.get( '/article_request/login_handler/?citation_json=aa&format=bb&illiad_url=cc&querystring=the_querystring', SERVER_NAME="127.0.0.1" )  # project root part of url is assumed
        redirect_url = response._headers['location'][1]
        self.assertEqual( 'http://127.0.0.1/article_request/illiad/?the_querystring', redirect_url )

    def test_direct_article_request_no_session(self):
        """ If not from '/easyaccess/article_request/login_handler/', should redirect to index page. """
        ## without session
        response = self.client.get( '/article_request/illiad/?a=b', SERVER_NAME="127.0.0.1" )  # project root part of url is assumed
        self.assertEqual( 302, response.status_code )
        redirect_url = response._headers['location'][1]
        self.assertEqual( '/find/?a=b', redirect_url )

    def test_direct_article_request_good_session(self):
        """ If from '/easyaccess/article_request/login_handler/', should display page. """
        ## with session
        session = self.session_hack.session
        session['last_path'] = '/easyaccess/article_request/login_handler/'
        # session['last_querystring'] = 'isbn=123'
        session.save()
        response = self.client.get( '/article_request/illiad/?a=b', SERVER_NAME="127.0.0.1" )  # project root part of url is assumed
        self.assertEqual( 200, response.status_code )
        self.assertTrue( 'Please click submit to confirm.' in response.content )

    # end class ViewsTest()


class LoginHelper_Test( TestCase ):
    """ Tests classes.LoginHelper() """

    def setUp( self ):
        self.helper = LoginHelper()

    ## TODO: re-enable after rework

    # def test__check_referrer( self ):
    #     """ Tests whether referrer is valid. """
    #     ## empty request should fail
    #     client = Client()
    #     session = client.session
    #     meta_dict = {}
    #     self.assertEqual(
    #         ( False, '/find/?' ),  # ( referrer_ok, redirect_url )
    #         self.helper.check_referrer(session, meta_dict) )
    #     ## good request should return True
    #     client = Client()
    #     session = client.session
    #     # session['findit_illiad_check_flag'] = 'good'
    #     # session['findit_illiad_check_enhanced_querystring'] = 'querystring_a'
    #     # meta_dict = { 'QUERY_STRING': 'querystring_a' }
    #     session['last_path'] = '/easyaccess/find/'
    #     session['last_querystring'] = 'isbn=123'
    #     self.assertEqual(
    #         ( True, '' ),  # ( referrer_ok, redirect_url )
    #         self.helper.check_referrer(session, meta_dict) )

    # end class LoginHelper_Test
