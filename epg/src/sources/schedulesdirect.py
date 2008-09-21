# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_schedulesdirect.py - Schedules Direct source for the epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2007 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# Maintainer: Jason Tackaberry <tack@urandom.ca>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

# python imports
import os
import md5
import time
import httplib
import gzip
import calendar
import logging
import xml.sax
import urlparse

# kaa imports
import kaa
from config import config

# get logging object
log = logging.getLogger('epg.schedulesdirect')

def H(m):
    return md5.md5(m).hexdigest()

soap_download_request = \
'''<?xml version="1.0" encoding="utf-8"?>
<SOAP-ENV:Envelope
     xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/">
<SOAP-ENV:Body>
  <tms:download xmlns:tms="urn:TMSWebServices">
    <startTime xsi:type="tms:dateTime">%s</startTime>
    <endTime xsi:type="tms:dateTime">%s</endTime>
  </tms:download>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>'''

def get_auth_digest_response_header(username, passwd, uri, auth):
    auth = auth[auth.find("Digest") + len("Digest "):].strip()
    vals = [ x.split("=", 1) for x in auth.split(", ") ]
    vals = [ (k.strip(), v.strip().replace('"', '')) for k, v in vals ]
    params = dict(vals)

    if None in [ params.get(x) for x in ("nonce", "qop", "realm") ]:
        return None

    nc = "00000001"
    cnonce = md5.md5("%s:%s:%s:%s" % (nc, params["nonce"], time.ctime(),
                                      open("/dev/urandom").read(8))).hexdigest()

    A1 = "%s:%s:%s" % (username, params["realm"], passwd)
    A2 = "%s:%s" % ("POST", uri)
    response = "%s:%s:%s:%s:%s:%s" % (H(A1), params["nonce"], nc, cnonce,
                                      params["qop"], H(A2))

    response = md5.md5(response).hexdigest()

    hdr = ('Digest username="%s", realm="%s", qop="%s", algorithm="MD5", ' +
          'uri="%s", nonce="%s", nc="%s", cnonce="%s", response="%s"') % \
          (username, params["realm"], params["qop"], uri, params["nonce"],
           nc, cnonce, response)
    if "opaque" in params:
        hdr += ', opaque="%s"' % params["opaque"]
    return hdr



def request(username, passwd, host, uri, start, stop, auth = None):
    t0 = time.time()
    if ':' not in host:
        # Append default port of 80
        host = host + ':80'
    conn = httplib.HTTPConnection(host)
    start_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start))
    stop_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop))
    soap_request = soap_download_request % (start_str, stop_str)

    headers = {
        "Accept-Encoding": "gzip",
        "Host": host,
        "User-Agent": "kaa.epg/0.0.1",
        "Content-Length": "%d" % len(soap_request),
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:TMSWebServices:xtvdWebService#download"
    }
    if auth:
        headers["Authorization"] = auth
    else:
        log.info('Connecting to schedulesdirect server')

    conn.request("POST", uri, None, headers)
    conn.send(soap_request)
    response = conn.getresponse()
    if response.status == 401 and auth:
        # Failed authentication.
        log.error('schedulesdirect authentication failed; bad username or password?')
        return

    if not auth and response.getheader("www-authenticate"):
        header = response.getheader("www-authenticate")
        auth  = get_auth_digest_response_header(username, passwd, uri, header)
        return request(username, passwd, host, uri, start, stop, auth)

    log.info('Connected in %.02f seconds; downloading guide update.' % (time.time() - t0))

    t0 = time.time()
    # FIXME: check response header to see if data is compressed.
    fname = '/tmp/schedulesdirect.xml.gz'
    dfile = open(fname, 'w+')
    # Read data in 50KB chunks.
    while True:
        data = response.read(50*1024)
        if not data:
            break
        dfile.write(data)
    dfile.close()

    conn.close()
    log.info('Downloaded %dKB in %.02f seconds.' % \
             (os.path.getsize(fname) / 1024.0, time.time() - t0))
    return fname



class Handler(xml.sax.handler.ContentHandler):
    def __init__(self, epg):
        xml.sax.handler.ContentHandler.__init__(self)
        self._epg = epg
        self._obj_type = None
        self._stations_by_id = {}
        self._schedule_by_program = {}
        self._handle_elements_list = []
        self._node_name = []
        self._program_info = {}

    def handle_elements(self, *args):
        self._handle_elements_list = args

    def startElement(self, name, attrs):
        self._node_name.append(name)
        if self._obj_type or (self._handle_elements_list and name not in self._handle_elements_list):
            return

        if name == 'schedule' and not self._obj_type:
            # Schedule elements map programs to times, but they are defined
            # before programs in the xml, so we have to keep this map in
            # memory.
            try:
                program = attrs.getValue('program')
                station = attrs.getValue('station')
                pgtime = attrs.getValue('time')
                duration = attrs.getValue('duration')
                if 'tvRating' in attrs.getNames():
                    rating = attrs.getValue('tvRating')
                else:
                    rating = None

            except KeyError, e:
                log.warning('Malformed schedule element; no %s attribute.' % e)

            if station not in self._stations_by_id:
                log.warning('Schedule defined for unknown station %s' % station)
                return
            
            t = time.strptime(pgtime[:-1], '%Y-%m-%dT%H:%M:%S')
            start = int(calendar.timegm(t))
            # Assumes duration is in the form PT00H00M
            duration_secs = (int(duration[2:4])*60 + int(duration[5:7]))*60
            stop = start + duration_secs

            if program not in self._schedule_by_program:
                self._schedule_by_program[program] = []
            self._schedule_by_program[program].append({
                'station': self._stations_by_id[station],
                'time': pgtime,
                'duration': duration_secs,
                'start': start,
                'stop': stop,
                'rating': rating
            })

        elif name == 'program':
            try:
                self._obj = { 'id': attrs.getValue('id') }
                self._obj_type = name
            except KeyError, e:
                log.warning('Malformed program element; no %s attribute.' % e)

        elif name == 'programGenre':
            try:
                self._obj = { 
                    'program': attrs.getValue('program'),
                    'genres': {},
                }
                self._obj_type = name
            except KeyError, e:
                log.warning('Malformed programGenre element; no %s attribute.' % e)
            
        elif name == 'station':
            try:
                self._obj = { 'id': attrs.getValue('id') }
                self._obj_type = name
            except KeyError, e:
                log.warning('Malformed station element; no %s attribute.' % e)

        elif name == 'map':
            try:
                station = attrs.getValue('station')
                channel = int(attrs.getValue('channel'))
            except KeyError, e:
                return log.warning('Malformed map element; no %s attribute.' % e)
            except ValueError:
                return log.warning('Malformed map element; channel is not an integer.')

            if station not in self._stations_by_id:
                # Maps may references stations that haven't been defined; I
                # believe we can safely ignore these.
                return

            db_id = self._epg.add_channel(tuner_id = channel,
                                         name = self._stations_by_id[station]['callSign'],
                                         long_name = self._stations_by_id[station]['name']).wait()
            self._stations_by_id[station]['db_id'] = db_id
            

    def characters(self, content):
        if self._obj_type == 'program':
            if self._node_name[-1] in ('title', 'subtitle', 'description', 'year', 'originalAirDate', 'year',
                                       'syndicatedEpisodeNumber', 'mpaaRating', 'starRating'):
                self._obj[self._node_name[-1]] = self._obj.get(self._node_name[-1], '') + content

        elif self._obj_type == 'station':
            if self._node_name[-1] in ('callSign', 'name'):
                self._obj[self._node_name[-1]] = self._obj.get(self._node_name[-1], '') + content

        elif self._obj_type == 'programGenre':
            if self._node_name[-1] == 'class':
                self._obj['_class'] = content
            elif self._node_name[-1] == 'relevance':
                self._obj['_relevance'] = content


    def endElement(self, name):
        self._node_name.pop()
        if self._handle_elements_list and name not in self._handle_elements_list:
            return
        if name == 'station':
            self._obj_type = None
            self._stations_by_id[self._obj['id']] = self._obj
        elif name == 'program':
            self._obj_type = None
            program = self._obj
            if program['id'] not in self._schedule_by_program:
                # program defined for which there is no schedule.
                return

            if 'year' in program:
                if program['year'].isdigit():
                    program['year'] = int(program['year'])
                else:
                    # Malformed.
                    del program['year']
            if 'originalAirDate' in program:
                date = time.strptime(program['originalAirDate'], '%Y-%m-%d')
                program['date'] = int(calendar.timegm(date))
            if 'syndicatedEpisodeNumber' in program:
                program['episode'] = program['syndicatedEpisodeNumber']
            if 'mpaaRating' in program:
                program['rating'] = program['mpaaRating']
            if 'starRating' in program:
                score = program['starRating']
                program['score'] = score.count('*') + score.count('+') * 0.5
            if program['id'] in self._program_info:
                program['genres'] = self._program_info[program['id']].get('genres')

            for schedule in self._schedule_by_program[program['id']]:
                channel_db_id = schedule['station']['db_id']
                # Prefer the TV rating over the mpaa rating.
                rating = schedule.get('rating') or program.get('rating')
                self._epg.add_program(channel_db_id, schedule['start'], schedule['stop'],
                                      program.get('title'), desc = program.get('description'),
                                      date = program.get('date'), episode = program.get('episode'),
                                      genres = program.get('genres'), score = program.get('score'),
                                      subtitle = program.get('subtitle'), year = program.get('year'),
                                      rating = rating)

        elif name == 'genre':
            self._obj['genres'][self._obj['_class']] = self._obj['_relevance']

        elif name == 'programGenre':
            self._obj_type = None
            pid = self._obj['program']
            if pid not in self._program_info:
                self._program_info[pid] = {}
            genres = self._obj['genres']
            self._program_info[pid]['genres'] = sorted(genres.keys(), key=lambda x: genres[x])


@kaa.threaded('epg')
def update(epg, start = None, stop = None):
    from gzip import GzipFile

    if not start:
        # If start isn't specified, choose current time (rounded down to the
        # nearest hour).
        start = int(time.time()) / 3600 * 3600
    if not stop:
        # If stop isn't specified, use config default.
        stop = start + (24 * 60 * 60 * config.days)

    urlparts = urlparse.urlparse(config.schedulesdirect.url)
    filename = request(str(config.schedulesdirect.username), str(config.schedulesdirect.password), urlparts[1], urlparts[2], start, stop)
    #filename = '/tmp/schedulesdirect.xml.gz'
    if not filename:
        return

    parser = xml.sax.make_parser()
    handler = Handler(epg)
    parser.setContentHandler(handler)

    # Pass 1: map genres to program ids
    handler.handle_elements('programGenre', 'genre')
    parser.parse(GzipFile(filename))

    # Pass 2: Parse everything else.
    handler.handle_elements('schedule', 'program', 'station', 'map')
    parser.parse(GzipFile(filename))

    os.unlink(filename)
    return True
