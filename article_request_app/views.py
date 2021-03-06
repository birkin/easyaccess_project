import json, logging, pprint

import markdown
from .classes.illiad_helper import IlliadUrlBuilder, IlliadArticleSubmitter, IlliadApiHelper
from .classes.illiad_helper import NewIlliadHelper  # still used for problem message; TODO, merge into other class.
from .classes.login_helper import LoginHelper
from .classes.shib_helper import ShibLoginHelper
from article_request_app import settings_app
from bul_link.models import Resource as B_L_Resource
from django.conf import settings as project_settings
from django.contrib.auth import logout
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.http import urlquote


log = logging.getLogger( 'access' )
ilog = logging.getLogger( 'illiad' )
shib_login_helper = ShibLoginHelper()


def shib_login( request ):
    """ Builds the SP login and target-return url; redirects to the SP login, which then lands back at the login_handler() url.
        Called when views.availability() returns a Request button that's clicked.
        Session cleared and info put in url due to revproxy resetting session. """
    # log.debug( f'TEMP article_request_app initial hit; request.__dict__, ```{pprint.pformat(request.__dict__)}```' )
    log.debug( f'request.GET.keys(), ```{ sorted(request.GET.keys()) }```' )
    log_id = request.session.get( 'log_id', '' )
    shortkey = request.GET['shortkey']
    log.debug( '`{id}` article_request shib_login() starting session.items(), ```{val}```'.format(id=log_id, val=pprint.pformat(request.session.items())) )

    ## store vars we're gonna need
    citation_json = request.session.get( 'citation_json', '{}' )
    format = request.session.get( 'format', '' )
    # illiad_url = request.session.get( 'illiad_url', '' )
    querystring = request.META.get('QUERY_STRING', '')

    ## clear session so non-rev and rev work same way
    # for key in request.session.keys():
    #     del request.session[key]
    for key in list( request.session.keys() ):
        del request.session[key]

    ## check if localdev
    if '127.0.0.1' in request.get_host() and project_settings.DEBUG2 is True:  # eases local development
        log.debug( 'localdev, so redirecting right to article_request_app.views.login_handler' )
        # querystring = shib_login_helper.build_localdev_querystring( citation_json, format, illiad_url, querystring, log_id )
        querystring = shib_login_helper.build_localdev_querystring( shortkey, citation_json, format, querystring, log_id )
        redirect_url = '%s?%s' % ( reverse('article_request:login_handler_url'), querystring )
    else:
        log.debug( 'not localdev, so building target-return url (to article_request_app.views.login_handler), and redirecting to shib SP login url' )
        # querystring = shib_login_helper.build_shib_sp_querystring( citation_json, format, illiad_url, querystring, log_id )
        querystring = shib_login_helper.build_shib_sp_querystring(
            reverse('article_request:login_handler_url'),
            shortkey,
            citation_json,
            format,
            # illiad_url,
            querystring,
            log_id
            )
        redirect_url = '%s?%s' % ( settings_app.SHIB_LOGIN_URL, querystring )
    return HttpResponseRedirect( redirect_url )

    ## end def shib_login()


def login_handler( request ):
    """ Ensures user comes from correct 'findit' url;
        then grabs shib info;
        then checks illiad for new-user or blocked;
        if happy, redirects to views.illiad_request() for confirmation, otherwise to `message` with error info. """

    log_id = request.GET.get( 'ezlogid', '' )
    login_helper = LoginHelper( log_id )

    illiad_api_helper = IlliadApiHelper()

    ## check referrer
    # ( referrer_ok, redirect_url ) = login_helper.check_referrer( request.session, request.META )
    # if referrer_ok is not True:
    #     request.session['last_path'] = request.path
    #     return HttpResponseRedirect( redirect_url )
    log.debug( '`{id}` request.GET.keys(), ```{val}```'.format(id=log_id, val=pprint.pformat(request.GET.keys())) )
    # for key in [ 'citation_json', 'format', 'illiad_url', 'querystring' ]:
    for key in [ 'citation_json', 'format', 'querystring' ]:
        if key not in request.GET.keys():
            redirect_url = '{main}?{qs}'.format( main=reverse('findit:findit_base_resolver_url'), qs=request.META.get('QUERY_STRING', '') )
            log.debug( 'referrer-check failed, redirecting to, ```{}```'.format(redirect_url) )
            return HttpResponseRedirect( redirect_url )
    request.session['last_path'] = request.path
    # request.session['login_openurl'] = request.META.get('QUERY_STRING', '')

    ## rebuild session (revproxy can destroy it, so all info must be in querystring)
    request.session['shortkey'] = request.GET['shortkey']
    request.session['log_id'] = log_id
    request.session['citation_json'] = request.GET['citation_json']
    request.session['format'] = request.GET['format']
    # request.session['illiad_url'] = request.GET['illiad_url']
    # request.session['login_openurl'] = request.GET['querystring']
    log.debug( 'session.items() after rebuild, ```{}```'.format(pprint.pformat(request.session.items())) )

    ## get user info
    # shib_dct = login_helper.grab_user_info( request, localdev_check, shib_status )  # updates session with user info
    localdev_check = False
    if '127.0.0.1' in request.get_host() and project_settings.DEBUG2 is True:  # eases local development
        localdev_check = True
    shib_dct = login_helper.grab_user_info( request, localdev_check )  # updates session with user info

    ## check if authorized
    ( is_authorized, redirect_url, message ) = login_helper.check_if_authorized( shib_dct )
    if is_authorized is False:
        log.info( '`{id}` user, `{val}` not authorized; redirecting to shib-logout-url, then message-url'.format(id=log_id, val=shib_dct.get('eppn', 'no_eppn')) )
        request.session['message'] = message
        return HttpResponseRedirect( redirect_url )

    ## prep title -- so if next illiad-step has a problem, a message with the title can be generated
    citation_json = request.session.get( 'citation_json', '{}' )
    citation_dct = json.loads( citation_json )
    if citation_dct.get( 'title', '' ) != '':
        title = citation_dct['title']
    else:
        title = citation_dct.get('source', 'title_unavailable')

    ## check illiad user
    illiad_user_check_dct = illiad_api_helper.manage_illiad_user_check( shib_dct, title )
    if illiad_user_check_dct['success'] is not True:
        request.session['message'] = illiad_user_check_dct['error_message']
        log.debug( 'message put in session, redirecting to message-url' )
        return HttpResponseRedirect( reverse('article_request:message_url') )  # handles blocked or failed-user-registration problems

    ## build redirect to illiad-landing-page for submit
    # illiad_landing_redirect_url = '%s://%s%s?%s' % ( request.scheme, request.get_host(), reverse('article_request:illiad_request_url'), request.session['login_openurl'] )
    illiad_landing_redirect_url = f'{request.scheme}://{request.get_host()}{reverse("article_request:illiad_request_url")}?shortkey={request.GET["shortkey"]}'
    log.debug( f'illiad_landing_redirect_url, `{illiad_landing_redirect_url}`' )

    ## cleanup
    # login_helper.update_session( request )

    ## redirect
    return HttpResponseRedirect( illiad_landing_redirect_url )

    ## end def login_handler()


def illiad_request( request ):
    """ Gives users chance to confirm their request via clicking 'Submit'.
        Gets here from views.login_handler()
        After 'Submit' button is hit, redirects to views.illiad_handler() """

    log.debug( f'request.GET.keys(), ```{ pprint.pformat(request.GET.keys()) }```' )
    log.debug( f'request.session.keys(), ```{ pprint.pformat(request.session.keys()) }```' )
    new_ill_helper = NewIlliadHelper()  # TO REMOVE

    ## check that we're here legitimately
    # ( referrer_ok, redirect_url ) = ill_helper.check_referrer( request.session, request.META )
    ( referrer_ok, redirect_url ) = new_ill_helper.check_referrer( request.session, request.META )
    if referrer_ok is not True:
        request.session['last_path'] = request.path
        return HttpResponseRedirect( redirect_url )
    request.session['last_path'] = request.path
    # request.session['illiad_request_openurl'] = request.META.get('QUERY_STRING', '')

    ## prep data
    citation_json = request.session.get( 'citation_json', '{}' )
    format = request.session.get( 'format', '' )
    context = { 'citation': json.loads(citation_json), 'format': format }
    log.debug( 'context, ```{}```'.format(pprint.pformat(context)) )

    ## cleanup
    request.session['format'] = ''
    # request.session['illiad_login_check_flag'] = ''
    log.debug( 'request.session.items(), ```{}```'.format(pprint.pformat(request.session.items())) )

    ## respond
    resp = render( request, 'article_request_app/request.html', context )
    return resp


def illiad_handler( request ):
    """ Processes the confirmation 'Submit' button behind-the-scenes by submitting the request to illiad and reading the result.
        Then redirects user (behind-the-scenes) to views.shib_logout() for the SP shib-logout ( which will then direct user to views.message() )
        """

    log.debug( f'request.GET.keys(), ```{ pprint.pformat(request.GET.keys()) }```' )
    log.debug( f'request.session.keys(), ```{ pprint.pformat(request.session.keys()) }```' )

    illiad_url_builder = IlliadUrlBuilder()
    illiad_submitter = IlliadArticleSubmitter()
    new_ill_helper = NewIlliadHelper()  # TO REMOVE

    ## get necessary data
    try:
        ## get illiad openurl
        shortkey = request.session['shortkey']
        # shortkey = request.GET['shortkey']  # it's a post
        rsrc = B_L_Resource.objects.get( shortlink=shortkey )
        item_dct = json.loads( rsrc.item_json )
        log.debug( f'item_dct, ```{pprint.pformat(item_dct)}```' )
        original_querystring = item_dct['querystring_original']
        enhanced_querystring = item_dct['enhanced_querystring']
        permalink = item_dct['permalink']
        ## get shib_dct
        shib_dct = json.loads( request.session['user_json'] )
        if 'eppn' not in shib_dct.keys():
            raise Exception()
    except:
        log.exception( 'problem getting necessary data; traceback follows; problem screen will be shown' )
        log.warning( f'`{illiad_submitter.log_id}` - bad attempt from source-url, ```{request.META.get("HTTP_REFERER", "")}```; ip, `{request.META.get("REMOTE_ADDR", "")}`' )
        request.session['message'] = new_ill_helper.problem_message
        request.session['last_path'] = request.path
        return HttpResponseRedirect( reverse('article_request:message_url') )

    ## build illiad-querystring
    illiad_url = illiad_url_builder.make_illiad_url( original_querystring, enhanced_querystring, request.scheme, request.get_host(), permalink )

    ## submit to illiad
    # illiad_url = submitter.enhance_if_necessary( illiad_url )
    submission_dct = illiad_submitter.prepare_submit_params( shib_dct, illiad_url )  # prepare parameters
    submission_result_dct = illiad_submitter.submit_request( submission_dct )  # send request to illiad
    if submission_result_dct['success'] is True:
        illiad_transaction_number = submission_result_dct['transaction_number']
    else:
        request.session['message'] = submission_result_dct['error_message']
        log.debug( 'illiad-submission error-message put in session, redirecting to message-url' )
        return HttpResponseRedirect( reverse('article_request:message_url') )  # will display helpful problem-message to user

    ## update db eventually

    ## send email
    citation_json = request.session.get( 'citation_json', '{}' )
    citation_dct = json.loads( citation_json )
    log.debug( f'citation_dct, ```{pprint.pformat(citation_dct)}```' )
    if citation_dct.get( 'title', '' ) != '':
        citation_title = citation_dct['title']
    elif illiad_url_builder.bib_title:
        citation_title = illiad_url_builder.bib_title
    else:
        citation_title = citation_dct.get('source', 'title_unavailable')
    # if citation_dct.get( 'title', '' ) != '':
    #     citation_title = citation_dct['title']
    # else:
    #     citation_title = citation_dct.get('source', 'title_unavailable')
    #
    subject = 'easyAccess request confirmation'
    body = new_ill_helper.make_illiad_success_message(
        shib_dct['name_first'], shib_dct['name_last'], citation_title, illiad_transaction_number, shib_dct['email'] )
    ffrom = settings_app.EMAIL_FROM
    addr = shib_dct['email']
    try:
        log.debug( 'about to send mail' )
        send_mail(
            subject, body, ffrom, [addr], fail_silently=True )
        log.debug( 'mail sent' )
    except Exception as e:
        # log.error( 'exception sending mail, ```{}```'.format(unicode(repr(e))) )
        log.exception( f'exception sending mail' )

    ## store message
    request.session['message'] = '{}\n---'.format( body )
    log.debug( 'session updated' )

    ## prep redirect
    message_redirect_url = reverse('article_request:message_url')
    log.debug( 'message_redirect_url, `%s`' % message_redirect_url )

    ## cleanup
    request.session['citation_json'] = ''

    ## build shib_logout() redirect url
    redirect_url = '{main_url}?{querystring}'.format(
        main_url=reverse('article_request:shib_logout_url'), querystring=request.META.get('QUERY_STRING', '') )
    log.debug( 'redirect_url, ```{}```'.format(redirect_url) )

    ## redirect
    return HttpResponseRedirect( redirect_url )

    ## end def illiad_handler()


def shib_logout( request ):
    """ Builds IDP shib-logout url, with target of 'article_request/message/'; redirects. """
    log_id = request.session.get( 'log_id', '' )
    log.debug( '`{id}` article_request shib_logout() starting session.items(), ```{val}```'.format(id=log_id, val=pprint.pformat(request.session.items())) )
    redirect_url = reverse( 'article_request:message_url' )
    if not ( '127.0.0.1' in request.get_host() and project_settings.DEBUG2 is True ):  # eases local development
        return_url = settings_app.SHIB_LOGOUT_URL_RETURN_ROOT
        encoded_return_url = urlquote( return_url )  # django's urlquote()
        redirect_url = '%s?return=%s' % ( settings_app.SHIB_LOGOUT_URL_ROOT, encoded_return_url )
    log.debug( '`{id}` redirect_url, ```{val}```'.format(id=log_id, val=redirect_url) )
    log.debug( '`{id}` article_request shib_logout() ending session.items(), ```{val}```'.format(id=log_id, val=pprint.pformat(request.session.items())) )
    return HttpResponseRedirect( redirect_url )


def message( request ):
    """ Handles successful confirmation messages and problem messages; clears session. """
    log_id = request.session.get( 'log_id', '' )
    log.debug( '`{id}` article_request message() beginning session.items(), ```{val}```'.format(id=log_id, val=pprint.pformat(request.session.items())) )
    context = {
        'last_path': request.session.get( 'last_path', '' ),
        'message': markdown.markdown( request.session.get('message', '') )
    }
    request.session['message'] = ''
    request.session['last_path'] = request.path
    logout( request )  # from django.contrib.auth import logout
    log.debug( '`{id}` will render message.html'.format(id=log_id) )
    log.debug( '`{id}` article_request message() ending session.items(), ```{val}```'.format(id=log_id, val=pprint.pformat(request.session.items())) )
    return render( request, 'article_request_app/message.html', context )
