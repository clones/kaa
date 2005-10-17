import libxml2, sys, time, os, calendar
import kaa.notifier

def timestr2secs_utc(timestr):
    """
    Convert a timestring to UTC (=GMT) seconds.

    The format is either one of these two:
    '20020702100000 CDT'
    '200209080000 +0100'
    """
    # This is either something like 'EDT', or '+1'
    try:
        tval, tz = timestr.split()
    except ValueError:
        tval = timestr
        tz   = str(-time.timezone/3600)

    if tz == 'CET':
        tz='+1'

    # Is it the '+1' format?
    if tz[0] == '+' or tz[0] == '-':
        tmTuple = ( int(tval[0:4]), int(tval[4:6]), int(tval[6:8]),
                    int(tval[8:10]), int(tval[10:12]), 0, -1, -1, -1 )
        secs = calendar.timegm( tmTuple )

        adj_neg = int(tz) >= 0
        try:
            min = int(tz[3:5])
        except ValueError:
            # sometimes the mins are missing :-(
            min = 0
        adj_secs = int(tz[1:3])*3600+ min*60

        if adj_neg:
            secs -= adj_secs
        else:
            secs += adj_secs
    else:
        # No, use the regular conversion

        ## WARNING! BUG HERE!
        # The line below is incorrect; the strptime.strptime function doesn't
        # handle time zones. There is no obvious function that does. Therefore
        # this bug is left in for someone else to solve.

        try:
            secs = time.mktime(strptime.strptime(timestr, xmltv.date_format))
        except ValueError:
            timestr = timestr.replace('EST', '')
            secs = time.mktime(strptime.strptime(timestr, xmltv.date_format))
    return secs



def parse_channel(info):
    channel_id = info.node.prop("id").decode("utf-8")
    channel = station = name = None

    child = info.node.children
    while child:
        # This logic expects that the first display-name that appears
        # after an all-numeric and an all-alpha display-name is going
        # to be the descriptive station name.  XXX: check if this holds
        # for all xmltv source.
        if child.name == "display-name":
            if not channel and child.content.isdigit():
                channel = int(child.content)
            elif not station and child.content.isalpha():
                station = child.content.decode("utf-8")
            elif channel and station and not name:
                name = child.content.decode("utf-8")
        child = child.get_next()

    id = info.epg._add_channel_to_db(channel_id, channel, station, name)
    info.channel_id_to_db_id[channel_id] = [id, None]


def parse_programme(info):
    channel_id = info.node.prop("channel").decode("utf-8")
    if channel_id not in info.channel_id_to_db_id:
        log.warning("Program exists for unknown channel '%s'" % channel_id)
        return

    title = date = desc = None

    child = info.node.children
    while child:
        if child.name == "title":
            title = child.content.decode("utf-8")
        elif child.name == "desc":
            desc = child.content.decode("utf-8")
        elif child.name == "date":
            fmt = "%Y%m%d"
            if len(child.content) == 4:
                fmt = "%Y"
            date = time.mktime(time.strptime(child.content, fmt))
        child = child.get_next()

    if not title:
        return

    start = timestr2secs_utc(info.node.prop("start"))
    channel_db_id, last_prog = info.channel_id_to_db_id[channel_id]
    if last_prog:
        # There is a previous program for this channel with no stop time,
        # so set last program stop time to this program start time.
        last_start, last_title, last_desc = last_prog
        info.epg._add_program_to_db(channel_db_id, last_start, start, last_title, last_desc)

    if not info.node.prop("stop"):
        info.channel_id_to_db_id[channel_id][1] = (start, title, desc)
    else:
        stop = timestr2secs_utc(info.node.prop("stop"))
        info.epg._add_program_to_db(channel_db_id, start, stop, title, desc)
 

class UpdateInfo:
    pass

def _update_parse_xml_thread(epg, xmltv_file):
    doc = libxml2.parseFile(xmltv_file)
    channel_id_to_db_id = {}
    nprograms = 0
    child = doc.children.get_next().children
    while child:
        if child.name == "programme":
            nprograms += 1
        child = child.get_next()

    info = UpdateInfo()
    info.doc = doc
    info.node = doc.children.get_next().children
    info.channel_id_to_db_id = channel_id_to_db_id
    info.total = nprograms
    info.cur = 0
    info.epg = epg
    info.progress_step = info.total / 100

    timer = kaa.notifier.Timer(_update_process_step, info)
    timer.set_prevent_recursion()
    timer.start(0)
    

def _update_process_step(info):
    t0 = time.time()
    while info.node:
        if info.node.name == "channel":
            parse_channel(info)
        elif info.node.name == "programme":
            parse_programme(info)
            info.cur +=1
            if info.cur % info.progress_step == 0:
                info.epg.signals["update_progress"].emit(info.cur, info.total)

        info.node = info.node.get_next()
        if time.time() - t0 > 0.1:
            break

    if not info.node:
        info.epg.signals["update_progress"].emit(info.cur, info.total)
        info.doc.freeDoc()
        return False

    return True
    

def update(epg, xmltv_file):
    thread = kaa.notifier.Thread(_update_parse_xml_thread, epg, xmltv_file)
    thread.start()
