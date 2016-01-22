# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import pprint
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured

from shibboleth.app_settings import SHIB_ATTRIBUTE_MAP, LOGOUT_SESSION_KEY


#logging
import logging
from django.conf import settings
from django.utils.log import dictConfig
dictConfig(settings.LOGGING)
alog = logging.getLogger('access')


class ShibbolethRemoteUserMiddleware(RemoteUserMiddleware):
    """
    Authentication Middleware for use with Shibboleth.  Uses the recommended pattern
    for remote authentication from: http://code.djangoproject.com/svn/django/tags/releases/1.3/django/contrib/auth/middleware.py
    """
    def process_request(self, request):
        alog.debug( 'starting shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request()' )
        alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); request.META, `%s`' % pprint.pformat(request.META) )

        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The Django remote user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class.")

        ## is this needed? ##
        # #To support logout.  If this variable is True, do not
        # #authenticate user and return now.
        # if request.session.get(LOGOUT_SESSION_KEY) == True:
        #     alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); LOGOUT_SESSION_KEY found' )
        #     return
        # else:
        #     alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); LOGOUT_SESSION_KEY not found' )
        #     #Delete the shib reauth session key if present.
        #     request.session.pop(LOGOUT_SESSION_KEY, None)

        #Locate the remote user header.
        try:
            # alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); request.META, `%s`' % pprint.pformat(request.META) )
            username = request.META[self.header]
            alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); username found, `%s`' % username )
        except KeyError:
            alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); no REMOTE_USER found' )
            # If specified header doesn't exist then return (leaving
            # request.user set to AnonymousUser by the
            # AuthenticationMiddleware).
            if settings.SHIB_MOCK_HEADERS is True and '/login/' in request.META['REQUEST_URI']:
                username = settings.SHIB_MOCK_MAP['Shibboleth-eppn']
                pass
            else:
                alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); returning because no remote user was found' )
                return

        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.
        alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); request.user.is_authenticated(), `%s`' % request.user.is_authenticated() )
        if request.user.is_authenticated():
            if request.user.username == self.clean_username(username, request):
                return


        # # Make sure we have all required Shiboleth elements before proceeding.
        # shib_meta, error = self.parse_attributes(request)
        # # Add parsed attributes to the session.
        # request.session['shib'] = shib_meta
        # if error:
        #     raise ShibbolethValidationError("All required Shibboleth elements"
        #                                     " not found.  %s" % shib_meta)

        ## Make sure we have all required Shiboleth elements before proceeding.
        if settings.SHIB_MOCK_HEADERS is True and '/login/' in request.META['REQUEST_URI']:
            alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); populating shib_meta from SHIB_MOCK_MAP' )
            ( shib_meta, error ) = ( settings.SHIB_MOCK_MAP, False )
        else:
            alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); populating shib_meta from apache header' )
            shib_meta, error = self.parse_attributes(request)
        # Add parsed attributes to the session.
        request.session['shib'] = shib_meta
        alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); request.session["shib"] set' )
        if error:
            raise ShibbolethValidationError("All required Shibboleth elements"
                                            " not found.  %s" % shib_meta)


        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); about to authenticate' )
        user = auth.authenticate(remote_user=username, shib_meta=shib_meta)
        alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); authentication just occurred' )
        if user:
            alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.process_request(); auth produced valid user' )
            # User is valid.  Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            auth.login(request, user)
            user.set_unusable_password()
            user.save()
            # call make profile.
            self.make_profile(user, shib_meta)
            #setup session.
            self.setup_session(request)

        return

    def make_profile(self, user, shib_meta):
        """
        This is here as a stub to allow subclassing of ShibbolethRemoteUserMiddleware
        to include a make_profile method that will create a Django user profile
        from the Shib provided attributes.  By default it does nothing.
        """
        return

    def setup_session(self, request):
        """
        If you want to add custom code to setup user sessions, you
        can extend this.
        """
        return

    def parse_attributes(self, request):
        """
        Parse the incoming Shibboleth attributes.
        From: https://github.com/russell/django-shibboleth/blob/master/django_shibboleth/utils.py
        Pull the mapped attributes from the apache headers.
        """
        alog.debug( 'starting shibboleth.middleware.ShibbolethRemoteUserMiddleware.parse_attributes()' )
        shib_attrs = {}
        error = False
        meta = request.META
        for header, attr in SHIB_ATTRIBUTE_MAP.items():
            required, name = attr
            value = meta.get(header, None)
            shib_attrs[name] = value
            if not value or value == '':
                if required:
                    error = True
                    # if settings.SHIB_MOCK_HEADERS is False:
                    #     error = True
        alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.parse_attributes(); shib_attrs, `%s`' % shib_attrs )
        alog.debug( 'in shibboleth.middleware.ShibbolethRemoteUserMiddleware.parse_attributes(); error, `%s`' % error )
        return shib_attrs, error

class ShibbolethValidationError(Exception):
    pass
