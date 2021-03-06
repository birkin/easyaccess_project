# # -*- coding: utf-8 -*-

# import logging, pprint, urllib
# from urllib.parse import parse_qs

# import bibjsontools  # requirements.txt module
# from common_classes import misc
# from findit import app_settings



# log = logging.getLogger('access')


# class IlliadUrlBuilder( object ):
#     """ Constructs url sent to illiad.
#         Called by FinditResolver() code. """

#     def __init__( self ):
#         self.validator = IlliadValidator()

#     def make_illiad_url( self, initial_querystring, enhanced_querystring, scheme, host, permalink ):
#         """ Manages steps of constructing illiad url for possible use in article-requesting.
#             Called by FinditResolver.update_session()
#             TODO: The scheme://host is no longer used, now that the illiad-api is hit; that should be phased out from the code and settings. """
#         bib_dct = bibjsontools.from_openurl( enhanced_querystring )
#         log.debug( f'bib_dct, ```{pprint.pformat(bib_dct)}```' )
#         ill_bib_dct = self.validator.add_required_kvs( bib_dct )
#         extra_dct = self.check_identifiers( ill_bib_dct )
#         extra_dct = self.check_validity( ill_bib_dct, extra_dct )
#         log.debug( f'bib_dct before enhance, ```{ill_bib_dct}```' )
#         ill_bib_dct = self.enhance_citation( ill_bib_dct, initial_querystring )
#         log.debug( f'bib_dct after enhance, ```{ill_bib_dct}```' )
#         full_permalink = '%s://%s%s' % ( scheme, host, permalink )
#         extra_dct['Notes'] = self.update_note( extra_dct.get('Notes', ''), '`shortlink: <%s>`' % full_permalink )
#         openurl = bibjsontools.to_openurl( ill_bib_dct )
#         log.debug( f'openurl from bibjsontools, ```{openurl}```' )
#         for k, v in extra_dct.items():
#             openurl += '&%s=%s' % ( urllib.parse.quote_plus(k), urllib.parse.quote_plus(v) )
#         illiad_url = app_settings.ILLIAD_URL_ROOT % openurl  # ILLIAD_URL_ROOT is like `http...OpenURL?%s
#         log.debug( 'illiad_url, ```%s```' % illiad_url )
#         return illiad_url

#     def check_identifiers( self, ill_bib_dct ):
#         """ Gets oclc or pubmed IDs.
#             Called by make_illiad_url() """
#         extra_dct = {}
#         identifiers = ill_bib_dct.get( 'identifier', [] )
#         for idt in identifiers:
#             if idt['type'] == 'pmid':
#                 extra_dct['Notes'] = '`PMID: {}`'.format( idt['id'] )
#                 # extra_dct['Notes'] = self.update_note( 'foo', 'bar' )
#             elif idt['type'] == 'oclc':
#                 extra_dct['ESPNumber'] = idt['id']
#         log.debug( f'extra_dct, ```{extra_dct}```' )
#         return extra_dct

#     def check_validity( self, ill_bib_dct, extra_dct ):
#         """ Updates notes if necessary based on IlliadValidator.add_required_kvs() work.
#             Called by make_illiad_url() """
#         if ill_bib_dct.get('_valid') is not True:
#             if extra_dct.get('Notes') is None:
#                 extra_dct['Notes'] = ''
#             # extra_dct['Notes'] += '\rNot enough data provided by original request.'
#             extra_dct['Notes'] = self.update_note( extra_dct['Notes'], '`not enough original-request data`' )
#         log.debug( f'extra_dct, ```{extra_dct}```' )
#         return extra_dct

#     def enhance_citation( self, ill_bib_dct, original_querystring ):
#         """ Enhances low-quality bib-dct data from original_querystring-data when possible.
#             Called by: make_illiad_url() """
#         original_bib_dct = ill_bib_dct.copy()
#         log.debug( f'ill_bib_dct, ```{pprint.pformat(ill_bib_dct)}```' )
#         log.debug( f'original_querystring, ```{original_querystring}```' )
#         param_dct = parse_qs( original_querystring )
#         if ill_bib_dct['type'] == 'article':
#             if 'author' not in ill_bib_dct.keys():
#                 if 'rft.creator' in param_dct.keys():
#                     auth_string = ', '.join( param_dct['rft.creator'] )
#                     ill_bib_dct['author'] = [ {'name': f'(?) {auth_string}'} ]
#             if 'title' not in ill_bib_dct.keys() or ill_bib_dct.get( 'title', '' ).lower() == 'unknown':
#                 if 'rft.source' in param_dct.keys():
#                     atitle_string = ', '.join( param_dct['rft.source'] )
#                     ill_bib_dct['title'] = f'(?) {atitle_string}'
#         misc.diff_dicts( original_bib_dct, 'original_bib_dct', ill_bib_dct, 'modified_dct' )  # just logs diffs
#         return ill_bib_dct

#     def update_note( self, initial_note, additional_note ):
#         """ Updates notes with correct spacing & punctuation.
#             Called by check_identifiers(), check_validity(), make_illiad_url() """
#         log.debug( 'starting update_note' )
#         note = initial_note
#         if note is None:
#             note = additional_note
#         elif len( note.strip() ) == 0:
#             note = additional_note
#         else:
#             note += '; {}'.format( additional_note )
#         log.debug( 'note now, ```{}```'.format(note) )
#         return note

#     # end class IlliadUrlBuilder


# class IlliadValidator( object ):
#     """ Adds required keys and values for illiad.
#         Called by IlliadHelper.make_illiad_url() """

#     # def add_required_kvs( self, bib_dct ):
#     #     """ Adds required keys and values for illiad.
#     #         Called by IlliadHelper.make_illiad_url() """
#     #     original_bib_dct = bib_dct.copy()
#     #     valid_check = True
#     #     if bib_dct['type'] == 'article':
#     #         ( bib_dct, valid_check ) = self._handle_article( bib_dct, valid_check )
#     #     elif bib_dct['type'] == 'book':
#     #         ( bib_dct, valid_check ) = self._handle_book( bib_dct, valid_check )
#     #     elif (bib_dct['type'] == 'bookitem') or (bib_dct['type'] == 'inbook'):  # TL: These should all be inbooks but checking for now.
#     #         ( bib_dct, valid_check ) = self._handle_bookish( bib_dct, valid_check )
#     #     bib_dct['_valid'] = valid_check
#     #     # log.debug( f'modifed_bib_dct, ```{pprint.pformat(bib_dct)}```' )
#     #     misc.diff_dicts( original_bib_dct, 'original_bib_dct', bib_dct, 'modified_dct' )  # just logs diffs
#     #     return bib_dct

#     def add_required_kvs( self, bib_dct ):
#         """ Adds required keys and values for illiad.
#             Called by IlliadHelper.make_illiad_url() """
#         original_bib_dct = bib_dct.copy()
#         valid_check = True
#         if bib_dct['type'] == 'article':
#             ( bib_dct, valid_check ) = self._handle_article( bib_dct, valid_check )
#         elif bib_dct['type'] == 'book':
#             ( bib_dct, valid_check ) = self._examine_book( bib_dct, valid_check )
#         elif (bib_dct['type'] == 'bookitem') or (bib_dct['type'] == 'inbook'):  # TL: These should all be inbooks but checking for now.
#             ( bib_dct, valid_check ) = self._handle_bookish( bib_dct, valid_check )
#         bib_dct['_valid'] = valid_check
#         misc.diff_dicts( original_bib_dct, 'original_bib_dct', bib_dct, 'modified_dct' )  # just logs diffs
#         return bib_dct

#     def _handle_article( self, bib_dct, valid_check ):
#         """ Updates bib_dct with article values.
#             Called by add_required_kvs() """
#         if bib_dct.get('journal') is None:
#             bib_dct['journal'] = {'name': 'Not provided'}; valid_check = False
#         if bib_dct.get('year') is None:
#             bib_dct['year'] = '?'; valid_check = False
#         if bib_dct.get('title') is None:
#             bib_dct['title'] = 'Title not specified'; valid_check = False
#         if bib_dct.get('pages') is None:
#             bib_dct['pages'] = '? - ?'; valid_check = False
#         return ( bib_dct, valid_check )

#     def _examine_book( self, bib_dct, valid_check ):
#         """ Updates bib_dct genre if necessary.
#             Called by add_required_kvs() """
#         log.debug( 'here' )
#         handle_book_flag = True
#         if bib_dct.get( 'identifier', None ):
#             for element_dct in bib_dct['identifier']:
#                 if 'type' in element_dct.keys():
#                     if element_dct['type'] == 'pmid':
#                         bib_dct['type'] = 'article'
#                         handle_book_flag = False
#                         ( bib_dct, valid_check ) = self._handle_article( bib_dct, valid_check )
#         if handle_book_flag is True:
#             ( bib_dct, valid_check ) = self._handle_book( bib_dct, valid_check )
#         return ( bib_dct, valid_check )

#     def _handle_book( self, bib_dct, valid_check ):
#         """ Updates bib_dct with book values.
#             Called by add_required_kvs() """
#         if bib_dct.get('title') is None:
#             bib_dct['title'] = 'Not available'
#             valid_check = False
#         return ( bib_dct, valid_check )

#     def _handle_bookish( self, bib_dct, valid_check ):
#         """ Updates bib_dct with bookitem or inbook values.
#             Called by add_required_kvs() """
#         if bib_dct.get('title') is None:
#             bib_dct['title'] = 'Title not specified'; valid_check = False
#         if bib_dct.get('journal') is None:
#             bib_dct['journal'] = {'name': 'Source not provided'}; valid_check = False
#         pages = bib_dct.get('pages')
#         if (pages == []) or (pages is None):
#             bib_dct['pages'] = '? - ?'; valid_check = False
#         return ( bib_dct, valid_check )

#     # end class IlliadValidator
