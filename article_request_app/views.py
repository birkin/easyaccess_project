# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime, json, logging, os, pprint, random
from article_request_app import settings_app
from django.conf import settings as project_settings
from django.contrib.auth import logout
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseServerError
from .classes.illiad_helper import IlliadHelper
from django.shortcuts import get_object_or_404, render
from django.utils.http import urlquote
from illiad.account import IlliadSession


log = logging.getLogger( 'access' )
ilog = logging.getLogger( 'illiad' )
ill_helper = IlliadHelper
# view_helper = ViewHelper()


def login( request ):
    """ Ensures user comes from correct 'findit' url;
        then forces login; then checks illiad for new-user or blocked;
        if happy, redirects to `illiad`, otherwise to `oops`. """

    ## check that request is from findit
    findit_check = False
    findit_illiad_check_flag = request.session.get( 'findit_illiad_check_flag', '' )
    findit_illiad_check_openurl = request.session.get( 'findit_illiad_check_openurl', '' )
    if findit_illiad_check_flag == 'good' and findit_illiad_check_openurl == request.META.get('QUERY_STRING', ''):
        findit_check = True
    log.debug( 'findit_check, `%s`' % findit_check )
    if findit_check is True:
        request.session['login_openurl'] = request.META.get('QUERY_STRING', '')
    elif findit_check is not True:
        log.warning( 'Bad attempt from source-url, ```%s```; ip, `%s`' % (
            request.META.get('HTTP_REFERER', ''), request.META.get('REMOTE_ADDR', '') ) )
        return HttpResponseBadRequest( 'See "https://library.brown.edu/easyaccess/" for example usage.`' )

    ## force login, by forcing a logout
    login_url = '%s://%s%s?%s' % ( request.scheme, request.get_host(), reverse('article_request:login_url'), request.session['login_openurl'] )  # for logout and login redirections
    log.debug( 'login_url, `%s`' % login_url )
    localdev = False
    shib_status = request.session.get('shib_status', '')
    log.debug( 'shib_status, `%s`' % shib_status )
    if request.get_host() == '127.0.0.1' and project_settings.DEBUG == True:  # eases local development
        localdev = True
    if not localdev and shib_status == '':  # let's force logout
        request.session['shib_status'] = 'will_force_logout'
        encoded_login_url = urlquote( login_url )  # django's urlquote()
        force_logout_redirect_url = '%s?return=%s' % ( settings_app.SHIB_LOGOUT_URL_ROOT, encoded_login_url )
        log.debug( 'force_logout_redirect_url, `%s`' % force_logout_redirect_url )
        return HttpResponseRedirect( force_logout_redirect_url )
    if not localdev and shib_status == 'will_force_logout':  # force login
        """ Note, fyi, normally a shib httpd.conf entry triggers login via a config line like `require valid-user`.
            This SHIB_LOGIN_URL setting, though, is a url like: `https://host/shib.sso/login?target=/this_url_path`
            ...so it's that shib.sso/login url that triggers the login, not this app login url.
            This app login url _is_ shib-configured, though to perceive shib headers if they exist. """
        request.session['shib_status'] = 'will_force_login'
        encoded_openurl = urlquote( request.session['login_openurl'] )
        force_login_redirect_url = '%s?%s' % ( settings_app.SHIB_LOGIN_URL, encoded_openurl )
        log.debug( 'force_login_redirect_url, `%s`' % force_login_redirect_url )
        return HttpResponseRedirect( force_login_redirect_url )

    ## get user info
    if not localdev and shib_status == 'will_force_login':
        eppn = request.META.get( 'Shibboleth-eppn', 'anonymous' )
    else:  # localdev
        shib_dct = settings_app.DEVELOPMENT_SHIB_DCT
        eppn = shib_dct['eppn']



    ## log user into illiad
    log.debug( 'about to initialize an illiad session' )
    ill_username = eppn.split('@')[0]
    log.debug( 'ill_username, `%s`' % ill_username )
    illiad_instance = IlliadSession( settings_app.ILLIAD_REMOTE_AUTH_URL, settings_app.ILLIAD_REMOTE_AUTH_HEADER, ill_username )
    log.debug( 'illiad_instance.__dict__, ```%s```' % pprint.pformat(illiad_instance.__dict__) )
    try:
        1/0
        illiad_session = illiad_instance.login()
    except Exception as e:
        log.error( 'Exception on illiad login, ```%s```' % unicode(repr(e)) )
        message = 'oops; a problem occurred'
        request.session['problem_message'] = message
        return HttpResponseRedirect( reverse('article_request:oops_url') )
    log.info( 'user %s established Illiad session_id: %s.' % (ill_username, illiad_session['session_id']) )
    log.debug( 'illiad_instance.__dict__ now, ```%s```' % pprint.pformat(illiad_instance.__dict__) )
    log.debug( 'illiad_session, ```%s```' % pprint.pformat(illiad_session) )
    if illiad_session['blocked'] is True:
        citation_json = request.session.get( 'citation', '{}' )
        message = ill_helper.make_illiad_blocked_message( firstname, lastname, json.loads(citation_json) )
        request.session['problem_message'] = message
        return HttpResponseRedirect( reverse('article_request:oops_url') )
    pass



    ## build redirect to illiad-landing-page for submit (if happy) or oops (on problem)
    illiad_landing_redirect_url = '%s://%s%s?%s' % ( request.scheme, request.get_host(), reverse('article_request:illiad_request_url'), request.session['login_openurl'] )
    log.debug( 'illiad_landing_redirect_url, `%s`' % illiad_landing_redirect_url )

    ## cleanup
    request.session['illiad_login_check_flag'] = 'good'
    request.session['findit_illiad_check_flag'] = ''
    request.session['findit_illiad_check_openurl'] = ''
    request.session['login_openurl'] = ''
    request.session['shib_status'] = ''

    ## redirect
    return HttpResponseRedirect( illiad_landing_redirect_url )

    # end def login()


def illiad_request( request ):
    ## check that we're here legitimately
    illiad_login_check_flag = request.session.get('illiad_login_check_flag', '')
    log.debug( 'illiad_login_check_flag, `%s`' % illiad_login_check_flag )
    if illiad_login_check_flag != 'good':
        log.warning( 'bad attempt from source-url, ```%s```; ip, `%s`' % (
            request.META.get('HTTP_REFERER', ''), request.META.get('REMOTE_ADDR', '') ) )
        return HttpResponseBadRequest( 'Bad request; see "https://library.brown.edu/easyaccess/" for example usage.`' )
    ## prep data
    citation_json = request.session.get( 'citation', '{}' )
    format = request.session.get( 'format', '' )
    context = { 'citation': json.loads(citation_json), 'format': format }
    ## cleanup
    request.session['citation'] = ''
    request.session['format'] = ''
    ## respond
    resp = render( request, 'article_request_app/request.html', context )
    return resp


def confirmation( request ):
    return HttpResponse( 'confirmation-coming' )


def logout( request ):
    return HttpResponse( 'logout-coming' )


def oops( request ):
    message = request.session.get( 'problem_message', 'sorry; a problem occurred' )
    return HttpResponse( message )
