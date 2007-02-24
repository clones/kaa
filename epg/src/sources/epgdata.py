# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_epgdata.py -  get epg data from www.epgdata.com
# -----------------------------------------------------------------------------
# $Id: 
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2006 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Tanja Kotthaus <owigera@web.de>
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
import sys
import os
import time
import glob
import logging

# kaa imports
from kaa import xml, TEMP
import kaa.notifier
import kaa.xml

from config_epgdata import config

# get logging object
log = logging.getLogger('epgdata')


######
# special functions for processing the data from epgdata.com
######


# the meaning of the tags that epgdata.com uses can be found in the qe.dtd file
# which is included in the zip archive that contains also the epg data.
PROG_MAPPING = {
    'd2':'channel_id',
    'd4':'start',
    'd5':'stop',
    'd10':'category',
    'd25':'genre',
    'd19':'title',
    'd20':'subtitle',
    'd21':'desc',
    'd32':'coutry',
    'd33':'date',
    'd34':'presenter',
    'd36':'director',
    'd37':'actor',
    'd40':'icon'
}        

# the meaning of the tags that are used in the channel*.xml files can be found
# in the header of each channe*.xml file.
CH_MAPPING = {
    'ch0':'tvchannel_name',
    'ch1':'tvchannel_short',
    'ch4':'tvchannel_id',
    'ch11':'tvchannel_dvb'
}

META_MAPPING = {
    'g0':'id',    # genre_id
    'g1':'name',  # genre
    'ca0':'id',   # category_id
    'ca2':'name'  # category
}    

def timestr2secs_utc(timestr):
    """
    Convert the timestring to UTC (=GMT) seconds.
    
    The time format in the epddata is:
    '2002-09-08 00:00:00'
    The timezone is german localtime, which is CET or CEST.
    """
    secs = time.mktime(time.strptime(timestr, '%Y-%m-%d %H:%M:%S'))
    return secs

 
        
def parse_data(info): 
    """ parse the info from the xml
    
    The current node can be either from a channel or a program.
    Subelements of the form <ch?> are for channels whereas <d?> are for programs.
    See CH_MAPPING and PROG_MAPPING for a list of subelements that are 
    processed and their meaning. 
    First all subelements of the node are read to a dictionary called attr
    and then the info in the dictionary is processed further depending on what
    kind of node we have.
    """
    
    attr= {}
    flag = None
    # child is a <data> element and its children are containing the infos
    for child in info.node.children:
        if child.name in CH_MAPPING.keys():
            # this is channel info
            flag = 'channel'
            # let's process it
            attr[CH_MAPPING[child.name]] = child.content
        
        if child.name in META_MAPPING.keys():
            # this is meta info
            flag = 'meta'
            # let's process it
            attr[META_MAPPING[child.name]] = child.content
                 
        if child.name in PROG_MAPPING.keys():
            # this is program info
            flag = 'programme'
            if child.name=='d33': # date
                date = child.content
                # try to guess the format of the date
                if len(date.split('/'))==2:
                    # if it is '1995/96', take the first year
                    date = date.split('/')[0]
                elif len(date.split('-'))==2:
                    # if it is '1999-2004', take the first year
                    date = date.split('-')[0]
                if not len(date)==4:
                    # format unknown, ignore        
                      continue
                else:     
                    fmt = '%Y'
                    attr['date'] = int(time.mktime(time.strptime(date, fmt)))
            elif child.name=='d10' or child.name=='d25': # genre and category
                content = child.content
                try:
                    content = info.meta_id_to_meta_name[content]
                except KeyError:
                    pass
                else:
                    attr[PROG_MAPPING[child.name]] = content        
            else:        
                # process all other known elements
                attr[PROG_MAPPING[child.name]] = child.content
    
    if flag =='channel':
        # create db_id
        db_id = info.epg.add_channel(tuner_id=attr['tvchannel_dvb'],
                                     name=attr['tvchannel_short'], 
                                     long_name=attr['tvchannel_name'])
        # and fill the channel_id_to_db_id dictionary
        info.channel_id_to_db_id[attr['tvchannel_id']] = db_id                            

    if flag == 'meta':
        info.meta_id_to_meta_name[attr['id']]=attr['name']

    if flag == 'programme':
        # start and stop time must be converted according to our standards
        start = timestr2secs_utc(attr.pop('start'))
        stop = timestr2secs_utc(attr.pop('stop'))
        # there of course must be a title
        title = attr.pop('title')
        # translate channel_id to db_id
        db_id = info.channel_id_to_db_id[attr.pop('channel_id')]
        # fill this program to the database
        info.epg.add_program(db_id, start, stop, title, **attr)


#####
# this functions form the interface to freevo
#####    

class UpdateInfo:
    """
    Simple class holding temporary information we need, will be filled later.
	"""
    pass


@kaa.notifier.execute_in_thread('epg')
def _parse_xml(epg):
    """
    Thread to parse the xml file. It will also call the grabber if needed.
    """
        
    # create a tempdir as working area
    tempdir = os.path.join(TEMP, 'epgdata')
    if not os.path.isdir(tempdir):
        os.mkdir(tempdir)
    # and clear it if needed
    for i in glob.glob(os.path.join(tempdir,'*')):       
       os.remove(i) 
        
    # temp file
    tmpfile = os.path.join(tempdir,'temp.zip')
    # logfile
    logfile = os.path.join(TEMP,'epgdata.log')
    
    # empty list for the xml docs
    docs = []
    # count of the nodes that have to be parsed
    nodes = 0
       
    
    # create download adresse for meta data
    addresse = 'http://www.epgdata.com/index.php'
    addresse+= '?action=sendInclude&iLang=de&iOEM=xml&iCountry=de'
    addresse+= '&pin=%s' % config.pin
    addresse+= '&dataType=xml'    

    
    # remove old file if needed
    try:
        os.remove(tmpfile)
    except OSError:
         pass 
    # download the meta data file     
    log.info ('Downloading meta data')
    exit = os.system('wget -N -O %s "%s" >>%s 2>>%s' 
                    %(tmpfile, addresse, logfile, logfile))
    if not os.path.exists(tmpfile) or exit:
        log.error('Cannot get file from epgdata.com, see %s' %logfile)
        return
    # and unzip the zip file    
    log.info('Unzipping data for meta data')
    exit = os.system('unzip -uo -d %s %s >>%s 2>>%s' 
                    %(tempdir, tmpfile, logfile, logfile))
    if exit:
        log.error('Cannot unzip the downloaded file, see %s' %logfile)
        return
    
    # list of channel info xml files    
    chfiles = glob.glob(os.path.join(tempdir,'channel*.xml'))   
    if len(chfiles)==0:
        log.error('no channel xml files for parsing')
        return              
   
    # parse this files    
    for xmlfile in chfiles:
        try:
            doc = kaa.xml.Document(xmlfile, 'channel')
        except:
            log.warning('error while parsing %s' %xmlfile)
            continue
        docs.append(doc) 
        nodes = nodes + len(doc.children)      
            
    
    #parse the meta files
    try:
        # the genre file
        xmlfile = os.path.join(tempdir, 'genre.xml')
        doc = kaa.xml.Document(xmlfile, 'genre')
    except:
        log.warning('error while parsing %s' %xmlfile)
    else:
        # add the files to the list
        docs.append(doc)  
        nodes = nodes + len(doc.children) 
    try:
        # the category file
        xmlfile = os.path.join(tempdir, 'category.xml')
        doc = kaa.xml.Document(xmlfile, 'category')
    except:
        log.warning('error while parsing %s' %xmlfile)
    else:
        # add the files to the list
        docs.append(doc) 
        nodes = nodes + len(doc.children)    
    
               
    # create download adresse for programm files  
    addresse = 'http://www.epgdata.com/index.php'
    addresse+= '?action=sendPackage&iLang=de&iOEM=xml&iCountry=de'
    addresse+= '&pin=%s' % config.pin
    addresse+= '&dayOffset=%s&dataType=xml' 
       
    # get the file for each day 
    for i in range(0, int(config.days)):
            # remove old file if needed
            try:
                os.remove(tmpfile)
            except OSError:
                pass    
            # download the zip file    
            log.info('Getting data for day %s' %(i+1))
            exit = os.system('wget -N -O %s "%s" >>%s 2>>%s' 
                            %(tmpfile, addresse %i, logfile, logfile))
            if not os.path.exists(tmpfile) or exit:
                log.error('Cannot get file from epgdata.com, see %s' %logfile)
                return
            # and unzip the zip file    
            log.info('Unzipping data for day %s' %(i+1))
            exit = os.system('unzip -uo -d %s %s >>%s 2>>%s' 
                            %(tempdir, tmpfile, logfile, logfile))
            if exit:
                log.error('Cannot unzip the downloaded file, see %s' %logfile)
                return
    
  
    # list of program xml files that must be parsed   
    progfiles = glob.glob(os.path.join(tempdir,'*de_q[a-z].xml'))  
    if len(progfiles)==0:
        log.warning('no progam xml files for parsing')
    
    # parse the progam xml files    
    for xmlfile in progfiles:
        try:
            doc = kaa.xml.Document(xmlfile, 'pack')
        except:
            log.warning('error while parsing %s' %xmlfile)
            continue
        # add the files to the list    
        docs.append(doc)  
        nodes = nodes + len(doc.children)  
          
    log.info('There are %s files to parse with in total %s nodes' 
             %(len(docs), nodes))
    
    
    # put the informations in the UpdateInfo object.
    info = UpdateInfo()
    info.epg = epg
    info.pin = config.pin
    info.channel_id_to_db_id = {}
    info.meta_id_to_meta_name = {}
    info.docs =docs
    info.doc = info.docs.pop(0)
    info.node = info.doc.first
    info.total = nodes
    info.progress_step = info.total / 100
           
    return info


@kaa.notifier.yield_execution()
def update(epg):
    """
    Interface to source_epgdata.
    """
    if not config.pin:
        log.error('PIN for epgdata.com is missing in tvserver.conf')
        yield False

    # _parse_xml is forced to be executed in a thread. This means that
    # it always returns an InProgress object that needs to be yielded.
    # When yield returns we need to call the InProgress object to get
    # the result. If the result is None, the thread run into an error.
    info = _parse_xml(epg)
    yield info
    info = info()
    if not info:
        yield False

    t0 = time.time()
    while info.node or len(info.docs) > 0:
        while info.node:
            if info.node.name == "data":
                #  parse!
                parse_data(info)
            info.node = info.node.get_next()
            if time.time() - t0 > 0.1:
                # time to return to the main loop
                yield kaa.notifier.YieldContinue
                t0 = time.time()
        if len(info.docs) > 0:
            # take the next one
            info.doc = info.docs.pop(0)
            # and start with its first node
            info.node = info.doc.first
    epg.guide_changed()
    yield True
