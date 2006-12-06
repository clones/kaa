# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_zap2it.py - Zap2It source for the epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2006 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Jason Tackaberry <tack@sault.org>
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
from StringIO import StringIO

import libxml2

# kaa imports
import kaa
from kaa.strutils import str_to_unicode
from kaa.config import Var, Group

# get logging object
log = logging.getLogger('epg')

ZAP2IT_HOST = "datadirect.webservices.zap2it.com:80"
ZAP2IT_URI = "/tvlistings/xtvdService"

# Source configuration
config = \
       Group(name='zap2it', desc='''
       Zap2it settings

       Add more doc here please!
       ''',
             desc_type='group',
             schema = [

    Var(name='activate',
        default=False,
        desc='Use Zap2it service to populate database.'
       ),

    Var(name='username',
        default='',
        desc='Zap2it username.'
       ),

    Var(name='password',
        default='',
        desc='Zap2it password.'
       ),
    ])

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
        log.info('Connecting to zap2it server')

    conn.request("POST", uri, None, headers)
    conn.send(soap_request)
    response = conn.getresponse()
    if response.status == 401 and auth:
        # Failed authentication.
        log.error('zap2it authentication failed; bad username or password?')
        return

    if not auth and response.getheader("www-authenticate"):
        header = response.getheader("www-authenticate")
        auth  = get_auth_digest_response_header(username, passwd, uri, header)
        return request(username, passwd, host, uri, start, stop, auth)

    log.info('Connected in %.02f seconds; downloading guide update.' % (time.time() - t0))

    t0 = time.time()
    fname = '/tmp/zap2it.xml.gz'
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


def iternode(node):
    child = node.children
    while child:
        yield child
        child = child.get_next()


def parse_station(node, info):
    id = node.prop("id")
    d = {}
    for child in iternode(node):
        if child.name == "callSign":
            d["station"] = str_to_unicode(child.content)
        elif child.name == "name":
            d["name"] = str_to_unicode(child.content)
    info.stations_by_id[id] = d


def parse_map(node, info):
    id = node.prop("station")
    if id not in info.stations_by_id:
        # Shouldn't happen.
        return

    channel = int(node.prop("channel"))
    db_id = info.epg.add_channel(tuner_id=channel,
                                 name=info.stations_by_id[id]["station"],
                                 long_name=info.stations_by_id[id]["name"])
    info.stations_by_id[id]["db_id"] = db_id



def parse_schedule(node, info):
    program_id = node.prop("program")
    if program_id not in info.schedules_by_id:
        return
    d = info.schedules_by_id[program_id]
    d["station_id"] = node.prop("station")
    t = time.strptime(node.prop("time")[:-1], "%Y-%m-%dT%H:%M:%S")
    d["start"] = int(calendar.timegm(t))
    duration = node.prop("duration")

    # Assumes duration is in the form PT00H00M
    duration_secs = (int(duration[2:4])*60 + int(duration[5:7]))*60
    d["stop"] = d["start"] + duration_secs
    d["rating"] = str_to_unicode(node.prop("tvRating"))

    info.epg.add_program(info.stations_by_id[d["station_id"]]["db_id"], d["start"],
                         d["stop"], d.get("title"), desc=d.get("desc"))


def parse_program(node, info):
    program_id = node.prop("id")
    d = {}
    for child in iternode(node):
        if child.name == "title":
            d["title"] = str_to_unicode(child.content)
        elif child.name == "description":
            d["desc"] = str_to_unicode(child.content)

    info.schedules_by_id[program_id] = d


def find_roots(node, roots = {}):
    for child in iternode(node):
        if child.name == "stations":
            roots["stations"] = child
        elif child.name == "lineup":
            roots["lineup"] = child
        elif child.name == "schedules":
            roots["schedules"] = child
        elif child.name == "programs":
            roots["programs"] = child
        elif child.name == "productionCrew":
            roots["crew"] = child
        elif child.children:
            find_roots(child, roots)
        if len(roots) == 5:
            return

class UpdateInfo:
    pass

def _update_parse_xml_thread(epg, username, passwd, start, stop):
    filename = request(username, passwd, ZAP2IT_HOST, ZAP2IT_URI, start, stop)
    if not filename:
        return
    doc = libxml2.parseFile(filename)

    stations_by_id = {}
    roots = {}

    find_roots(doc, roots)
    nprograms = 0
    for child in iternode(roots["schedules"]):
        if child.name == "schedule":
            nprograms += 1

    info = UpdateInfo()
    info.doc = doc
    info.roots = [roots["stations"], roots["lineup"], roots["programs"], roots["schedules"]]
    info.node_names = ["station", "map", "program", "schedule"]
    info.node = None
    info.total = nprograms
    info.schedules_by_id = {}
    info.stations_by_id = stations_by_id
    info.epg = epg
    info.progress_step = info.total / 100
    info.t0 = time.time()

    timer = kaa.notifier.Timer(_update_process_step, info)
    timer.start(0)


def _update_process_step(info):
    t0=time.time()
    if not info.node and info.roots:
        info.node = info.roots.pop(0).children
        info.cur_node_name = info.node_names.pop(0)

    while info.node:
        if info.node.name == info.cur_node_name:
            globals()["parse_%s" % info.cur_node_name](info.node, info)

        info.node = info.node.get_next()
        if time.time() - t0 > 0.1:
            break

    if not info.node and not info.roots:
        os.unlink(info.doc.name)
        info.doc.freeDoc()
        info.epg.guide_changed()
        log.info('Processed %d programs in %.02f seconds' % (info.epg._num_programs, time.time() - info.t0))
        return False

    return True


def update(epg, start = None, stop = None):
    if not start:
        # If start isn't specified, choose current time (rounded down to the
        # nearest hour).
        start = int(time.time()) / 3600 * 3600
    if not stop:
        # If stop isn't specified, use 24 hours after start.
        stop = start + (24 * 60 * 60)

    thread = kaa.notifier.Thread(_update_parse_xml_thread, epg,
                                 str(config.username), str(config.password),
                                 start, stop)
    thread.start()
    return True
