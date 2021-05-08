#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2006 Søren Roug, European Environment Agency
# Copyright (C) 2021 Kazuo Moriwaka
#
# This is free software.  You may redistribute it under the terms
# of the Apache license and the GNU General Public License Version
# 2 or at your option any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
import zipfile
from xml.sax import make_parser,handler
from xml.sax.xmlreader import InputSource
import xml.sax.saxutils
import sys
from odf.namespaces import TEXTNS, TABLENS, DRAWNS, PRESENTATIONNS
from io import BytesIO, StringIO

PAGE_HEADER = '<!-- page {page} start -->'
PAGE_FOOTER = '<!-- page {page} end -->'

def getxmlpart(odffile, xmlfile):
    """ Get the content out of the ODF file"""
    z = zipfile.ZipFile(odffile)
    content = z.read(xmlfile)
    z.close()
    return content

#
# Extract notes part from content.xml
#

class ODFSlideHandler(handler.ContentHandler):
    """ Extract notes from content.xml of an ODF file """
    def __init__(self, eater):
        self.r = eater
        self.data = []
        self.pagenum = 0
        self.in_notes = False

    def characters(self, data):
        self.data.append(data)

    def startElementNS(self, tag, qname, attrs):
        if tag == (DRAWNS, 'page'):
            self.pagenum = self.pagenum + 1
            self.r.append(PAGE_HEADER.format(page = self.pagenum)) 
        if tag == (DRAWNS, 'frame'):
            if (PRESENTATIONNS, 'class') in attrs and attrs[(PRESENTATIONNS, 'class')] in ('notes'):
                self.in_notes = True
                self.data = []

    def endElementNS(self, tag, qname):
        if tag == (TEXTNS, 'p') and self.in_notes:
            str = ''.join(self.data) + '\n'
            self.data = []
            if len(str) > 0:
                self.r.append(str)
        if tag == (DRAWNS, 'frame') and self.in_notes:
            self.in_notes = False
        if tag == (DRAWNS, 'page'):
            self.r.append(PAGE_FOOTER.format(page = self.pagenum)) 
            self.in_notes = False # just for broken content.xml

def odfnotes(odffile):
    mimetype = getxmlpart(odffile,'mimetype')
    content = getxmlpart(odffile,'content.xml')
    lines = []
    parser = make_parser()
    parser.setFeature(handler.feature_namespaces, 1)
    
    if mimetype.decode('utf8') in ('application/vnd.oasis.opendocument.presentation',
                    'application/vnd.oasis.opendocument.presentation-template'):
        parser.setContentHandler(ODFSlideHandler(lines))
    else:
        print("Unsupported fileformat")
        sys.exit(2)
    parser.setErrorHandler(handler.ErrorHandler())

    inpsrc = InputSource()
    inpsrc.setByteStream(StringIO(content.decode('utf8')))
    parser.parse(inpsrc)
    return lines


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='extract notes text from ODP file')
    parser.add_argument(metavar='input.odp',
                        dest='inputfile', help='input ODP file')
    parser.add_argument('--ssml', action='store_true',
                        help='insert SSML header/footer for slide2mp4')

    args = parser.parse_args()

    if args.ssml:
        PAGE_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n<speak version="1.1"> '
        PAGE_FOOTER = '</speak>'

    with open(args.inputfile, 'rb') as f:
        for line in odfnotes(BytesIO(f.read())):
            print(line)
