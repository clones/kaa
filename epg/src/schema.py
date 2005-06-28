# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# schema.py - database schema
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-epg - Python EPG module
# Copyright (C) 2002-2005 Dirk Meyer, Rob Shortt, et al.
#
# First Edition: Rob Shortt <rob@tvcentric.com>
# Maintainer:    Rob Shortt <rob@tvcentric.com>
#
# Please see the file doc/AUTHORS for a complete list of authors.
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

__all__ = [ 'schema', 'update' ]

# the complete schema
schema = '''

create table versioning (
    thing text primary key,
    version text
);
insert into versioning (thing, version) values ("sql", "0.1.1");

create table channels (
    id unicode primary key,
    display_name unicode not null,
    access_id unicode not null
);

create table channel_types (
    id integer primary key,
    name text not null
);
insert into channel_types (id, name) values (0, "undefined");
insert into channel_types (id, name) values (1, "tv");
insert into channel_types (id, name) values (2, "camera");
insert into channel_types (id, name) values (3, "radio");

create table programs (
    id integer primary key,
    channel_id unicode(16) not null,
    start int not null,
    stop int not null,
    title unicode(256) not null,
    episode unicode(256),
    subtitle unicode(256),
    description unicode(4096),
    rating int,
    original_airdate int
);

create index pc on programs (channel_id);
create unique index pc_start on programs (channel_id, start);
create unique index pc_start_stop on programs (channel_id, start, stop);
create index p_start_stop on programs (start, stop);
create index p_start on programs (start);
create index p_stop on programs (stop);
create index p_title on programs (title);

create table categories (
    id integer primary key,
    name unicode not null
);
insert into categories (id, name) values (0, "undefined");
insert into categories (id, name) values (1, "series");
insert into categories (id, name) values (2, "news");
insert into categories (id, name) values (3, "movie");
insert into categories (id, name) values (4, "special");
insert into categories (id, name) values (5, "audio");
insert into categories (id, name) values (6, "feed");
insert into categories (id, name) values (7, "drama");

create table program_category (
    program_id integer not null,
    category_id integer not null
);

create table advisories (
    id integer primary key,
    name unicode not null
);
insert into advisories (id, name) values (0, "undefined");

create table program_advisory (
    program_id integer not null,
    advisory_id integer not null
);

create table ratings (
    id integer primary key,
    name unicode not null
);
insert into ratings (id, name) values (0, "undefined");
insert into ratings (id, name) values (1, "NR");
insert into ratings (id, name) values (2, "G");
insert into ratings (id, name) values (3, "PG");
insert into ratings (id, name) values (4, "PG-13");
insert into ratings (id, name) values (5, "PG-14");
insert into ratings (id, name) values (6, "A");
insert into ratings (id, name) values (7, "R");
insert into ratings (id, name) values (8, "X");

create table record_programs (
    program_id integer primary key
);

create table recorded_programs (
    program_id integer primary key
);
'''

# internal update list between versions
update = {
    '0.1.1': '''
    drop table admin;
    create table versioning (thing text primary key, version text);
    insert into versioning (thing, version) values ("sql", "0.1.1");
    create index p_title on programs (title);
    '''
    }
