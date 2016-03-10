# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime, json, logging, os, pprint, random
from article_request_app import settings_app


log = logging.getLogger('access')


class ShibChecker( object ):
    """ Contains helpers for checking Shib. """

    def grab_shib_info( self, request ):
        """ Grabs shib values from http-header or dev-settings.
            Called by LoginHelper.grab_user_info() """
        shib_dct = {}
        if 'Shibboleth-eppn' in request.META:
            shib_dct = self.grab_shib_from_meta( request )
        else:
            if request.get_host() == '127.0.0.1' and project_settings.DEBUG == True:
                shib_dct = settings_app.DEVELOPMENT_SHIB_DCT
        log.debug( 'in models.ShibChecker.grab_shib_info(); shib_dct is: %s' % pprint.pformat(shib_dct) )
        return shib_dct

    def grab_shib_from_meta( self, request ):
        """ Extracts shib values from http-header.
            Called by grab_shib_info() """
        shib_dct = {
            'brown_status': request.META.get( 'Shibboleth-brownStatus', '' ),  # eg. 'active'
            'brown_type': request.META.get( 'Shibboleth-brownType', '' ),  # eg. 'Staff'
            'department': request.META.get( 'Shibboleth-department', '' ),
            'edu_person_primary_affiliation': request.META.get( 'Shibboleth-eduPersonPrimaryAffiliation', '' ),  # eg. 'staff'
            'email': request.META.get( 'Shibboleth-mail', '' ).lower(),
            'eppn': request.META.get( 'Shibboleth-eppn', '' ),
            'id_net': request.META.get( 'Shibboleth-brownNetId', '' ),
            'id_short': request.META.get( 'Shibboleth-brownShortId', '' ),
            'member_of': request.META.get( 'Shibboleth-isMemberOf', '' ).split(';'),  # only dct element that's not a unicode string
            'name_first': request.META.get( 'Shibboleth-givenName', '' ),
            'name_last': request.META.get( 'Shibboleth-sn', '' ),
            'patron_barcode': request.META.get( 'Shibboleth-brownBarCode', '' ),
            'phone': request.META.get( 'Shibboleth-phone', '' ),  # valid?
            'title': request.META.get( 'Shibboleth-title', '' ),
            }
        return shib_dct

    # end class ShibChecker


