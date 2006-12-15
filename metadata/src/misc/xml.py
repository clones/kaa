# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xml.py - detect xml and fxd files
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
import os
import logging
import libxml2

# kaa.metadata imports
import kaa.metadata.mediainfo as core
import kaa.metadata.factory as factory

# get logging object
log = logging.getLogger('metadata')

XML_TAG_INFO = {
    'image':  'Bins Image Description',
    'freevo': 'Freevo XML Definition'
    }

class XML(core.Media):

    def __init__(self,file):
        ext = os.path.splitext(file.name)[1].lower()
        if not ext in ('.xml', '.fxd', '.html', '.htm'):
            raise core.ParseError()

        core.Media.__init__(self)

        self.mime  = 'text/xml'
        self.type  = ''
        
        if ext in ('.html', '.htm'):
            # just believe that it is a html file
            self.mime  = 'text/html'
            self.type  = 'HTML Document'
            return

        ctxt = libxml2.createFileParserCtxt(file.name)
        # Silence parse errors
        ctxt.setErrorHandler(lambda *args: None, None)
        ctxt.parseDocument()

        try:
            doc = ctxt.doc()
        except libxml2.parserError:
            raise core.ParseError()

        if not doc or not doc.children or not doc.children.name:
            raise core.ParseError()

        tag = doc.children.name
        if tag in XML_TAG_INFO:
            self.type = XML_TAG_INFO[tag]
        else:
            self.type = 'XML file'
        doc.freeDoc()


factory.register( 'text/xml', ('xml', 'fxd', 'html', 'htm'), XML )
