import string
import os
import time
import cPickle
from pysqlite2 import dbapi2 as sqlite

CREATE_SCHEMA = """
    CREATE TABLE meta (
        attr        TEXT UNIQUE, 
        value       TEXT
    );
    INSERT INTO meta VALUES('filecount', 0);
    INSERT INTO meta VALUES('version', 0.1);

    CREATE TABLE types (
        id              INTEGER PRIMARY KEY AUTOINCREMENT, 
        name            TEXT UNIQUE,
        attrs_pickle    BLOB
    );

    CREATE TABLE words (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        word            TEXT,
        count           INTEGER
    );
    CREATE UNIQUE INDEX words_idx on WORDS (word) ON CONFLICT REPLACE;

    CREATE TABLE words_map (
        rank            INTEGER,
        word_id         INTEGER,
        file_type       INTEGER,
        file_id         INTEGER,
        frequency       FLOAT
    );
    CREATE INDEX words_map_idx ON words_map (word_id, rank, file_type);
"""


ATTR_SIMPLE       = 0x00
ATTR_SEARCHABLE   = 0x01      # Is a SQL column, not a pickled field
ATTR_INDEXED      = 0x02      # Will have an SQL index
ATTR_KEYWORDS     = 0x04      # Also indexed for keyword queries


class Database:
    def __init__(self, dbfile = None):
        if not dbfile:
            dbfile = "kaavfs.sqlite"

        self._object_types = {}
        self._dbfile = dbfile
        self._open_db()

    def __del__(self):
        self._db.commit()

    def _open_db(self):
        self._db = sqlite.connect(self._dbfile)
        self._cursor = self._db.cursor()
        self._cursor.execute("PRAGMA synchronous=OFF")
        self._cursor.execute("PRAGMA count_changes=OFF")
        self._cursor.execute("PRAGMA cache_size=50000")

        if not self.check_table_exists("meta"):
            self._db.close()
            self._create_db()

        self._load_object_types()

    def _db_query(self, statement, args = ()):
        self._cursor.execute(statement, args)
        rows = self._cursor.fetchall()
        return rows

    def _db_query_row(self, statement, args = ()):
        rows = self._db_query(statement, args)
        if len(rows) == 0:
            return None
        return rows[0]

    def check_table_exists(self, table):
        res = self._db_query_row("SELECT name FROM sqlite_master where " \
                         "name=? and type='table'", (table,))
        return res != None


    def _create_db(self):
        try:
            os.unlink(self._dbfile)
        except:
            pass
        f = os.popen("sqlite3 %s" % self._dbfile, "w")
        f.write(CREATE_SCHEMA)
        f.close()
        self._open_db()

        self.register_object_type_attrs("dir")


    def register_object_type_attrs(self, type_name, attr_list = ()):
        if type_name in self._object_types:
            # This type already exists.  Compare given attributes with
            # existing attributes for this type.
            cur_type_id, cur_type_attrs = self._object_types[type_name]
            new_attrs = {}
            db_needs_update = False
            for name, type, flags in attr_list:
                if name not in cur_type_attrs:
                    new_attrs[name] = type, flags
                    if flags:
                        # New attribute isn't simple, needs to alter table.
                        db_needs_update = True

            if len(new_attrs) == 0:
                # All these attributes are already registered; nothing to do.
                return

            if not db_needs_update:
                # Only simple (i.e. pickled only) attributes are added, so we
                # don't need to alter the table, just update the types table.
                cur_type_attrs.update(new_attrs)
                self._db_query("UPDATE types SET attrs_pickle=? WHERE id=?",
                           (buffer(cPickle.dumps(cur_type_attrs, 2)), cur_type_id))
                return

            # Update the attr list to merge both existing and new attributes.
            # We need to update the database now.
            attr_list = []
            for name, (type, flags) in cur_type_attrs.items() + new_attrs.items():
                attr_list.append((name, type, flags))

        else:
            new_attrs = {}
            # Merge standard attributes with user attributes for this type.
            attr_list = (
                ("id", int, ATTR_SEARCHABLE),
                ("name", str, ATTR_KEYWORDS),
                ("parent_id", int, ATTR_SEARCHABLE),
                ("parent_type", int, ATTR_SEARCHABLE),
                ("size", int, ATTR_SIMPLE),
                ("mtime", int, ATTR_SEARCHABLE),
                ("pickle", buffer, ATTR_SEARCHABLE),
            ) + tuple(attr_list)

        table_name = "objects_%s" % type_name

        create_stmt = "CREATE TABLE %s_tmp ("% table_name

        # Iterate through type attributes and append to SQL create statement.
        attrs = {}
        for name, type, flags in attr_list:
            # If flags is non-zero it means this attribute needs to be a
            # column in the table, not a pickled value.
            if flags:
                sql_types = {str: "TEXT", int: "INTEGER", float: "FLOAT", 
                             buffer: "BLOB", unicode: "TEXT"}
                assert(type in sql_types)
                create_stmt += "%s %s" % (name, sql_types[type])
                if name == "id":
                    # Special case, these are auto-incrementing primary keys
                    create_stmt += " PRIMARY KEY AUTOINCREMENT"
                create_stmt += ","

            attrs[name] = (type, flags)

        create_stmt = create_stmt[:-1] + ")"
        self._db_query(create_stmt)

        # Add this type to the types table, including the attributes
        # dictionary.
        self._db_query("INSERT OR REPLACE INTO types VALUES(NULL, ?, ?)", 
                       (type_name, buffer(cPickle.dumps(attrs, 2))))

        if new_attrs:
            # Migrate rows from old table to new one.
            columns = filter(lambda x: cur_type_attrs[x][1], cur_type_attrs.keys())
            columns = string.join(columns, ",")
            self._db_query("INSERT INTO %s_tmp (%s) SELECT %s FROM %s" % \
                           (table_name, columns, columns, table_name))

            # Delete old table.
            self._db_query("DROP TABLE %s" % table_name)

        # Rename temporary table.
        self._db_query("ALTER TABLE %s_tmp RENAME TO %s" % \
                       (table_name, table_name))


        # Create index for locating object by full path (i.e. parent + name)
        self._db_query("CREATE UNIQUE INDEX %s_parent_name_idx on %s "\
                       "(parent_id, parent_type, name)" % \
                       (table_name, table_name))
        # Create index for locating all objects under a given parent.
        self._db_query("CREATE INDEX %s_parent_idx on %s (parent_id, "\
                       "parent_type)" % (table_name, table_name))

        # If any of these attributes need to be indexed, create the index
        # for that column.  TODO: need to support indexes on multiple
        # columns.
        for name, type, flags in attr_list:
            if flags & ATTR_INDEXED:
                self._db_query("CREATE INDEX %s_%s_idx ON %s (%s)" % \
                               (table_name, name, table_name, name))

        self._load_object_types()


    def _load_object_types(self):
        for id, name, attrs in self._db_query("SELECT * from types"):
            self._object_types[name] = id, cPickle.loads(str(attrs))
    

    def _make_query_from_attrs(self, query_type, attrs, type_name):
        type_attrs = self._object_types[type_name][1]

        columns = []
        values = []
        placeholders = []

        for key in attrs.keys():
            if attrs[key] == None:
                del attrs[key]
        attrs_copy = attrs.copy()
        for name, (type, flags) in type_attrs.items():
            if flags != ATTR_SIMPLE:
                columns.append(name)
                placeholders.append("?")
                if name in attrs:
                    values.append(attrs[name])
                    del attrs_copy[name]
                else:
                    values.append(None)

        if len(attrs_copy) > 0:
            values[columns.index("pickle")] = buffer(cPickle.dumps(attrs_copy, 2))
        else:
            values[columns.index("pickle")] = None

        table_name = "objects_" + type_name

        if query_type == "add":
            columns = string.join(columns, ",")
            placeholders = string.join(placeholders, ",")
            q = "INSERT INTO %s (%s) VALUES(%s)" % (table_name, columns, placeholders)
        else:
            q = "UPDATE %s SET " % table_name
            for col, ph in zip(columns, placeholders):
                q += "%s=%s," % (col, ph)
            # Trim off last comma
            q = q[:-1]
            q += " WHERE id=?"
            values.append(attrs["id"])

        # TODO: keyword indexing for ATTR_KEYWORDS attributes.

        return q, values
    

    def add_object(self, (object_type, object_name), parent = None, **attrs):
        """
        Adds an object to the database.   When adding, an object is identified
        by a (type, name) tuple.  Parent is a (type, id) tuple which refers to
        the object's parent.  In both cases, "type" is a type name as 
        given to register_object_type_attrs().  attrs kwargs will vary based on
        object type.  ATTR_SIMPLE attributes which a None are not added.
        """
        if parent:
            attrs["parent_type"] = self._object_types[parent[0]][0]
            attrs["parent_id"] = parent[1]
        attrs["name"] = object_name
        query, values = self._make_query_from_attrs("add", attrs, object_type)
        self._db_query(query, values)
        attrs["id"] = self._cursor.lastrowid
        # add lastrowid
        return attrs


    def update_object(self, (object_type, object_id), parent = None, **attrs):
        """
        Update an object in the database.  For updating, object is identified
        by a (type, id) tuple.  Parent is a (type, id) tuple which refers to
        the object's parent.  If specified, the object is reparented,
        otherwise the parent remains the same as when it was added with
        add_object().  attrs kwargs will vary based on object type.  If a
        ATTR_SIMPLE attribute is set to None, it will be removed from the
        pickled dictionary.
        """
        row = self._db_query_row("SELECT pickle FROM objects_%s WHERE id=?" % object_type,
                                 (object_id,))
        assert(row)
        if row[0]:
            row_attrs = cPickle.loads(str(row[0]))
            row_attrs.update(attrs)
            attrs = row_attrs
        if parent:
            attrs["parent_type"] = self._object_types[parent[0]][0]
            attrs["parent_id"] = parent[1]
        attrs["id"] = object_id
        query, values = self._make_query_from_attrs("update", attrs, object_type)
        self._db_query(query, values)


    def query(self, **attrs):
        """
        Query the database for objects matching all of the given attributes
        (specified in kwargs).  "parent" is a special kwarg which is a
        (type, id) tuple referring to the object's parent.  "object" is 
        another special kwarg which is a (type, id) tuple referring to a
        specific object.  "type" can refer to a object type name, and if
        specified, only objects of that type will be queried.
        """
        if "type" in attrs:
            type_list = [(attrs["type"], self._object_types[attrs["type"]])]
            del attrs["type"]
        else:
            type_list = self._object_types.items()

        if "parent" in attrs:
            parent_type, parent_id = attrs["parent"]
            attrs["parent_type"] = self._object_types[parent_type][0]
            attrs["parent_id"] = parent_id
            del attrs["parent"]

        results = []
        for type_name, (type_id, type_attrs) in type_list:
            # List of attribute dicts for this type.
            columns = filter(lambda x: type_attrs[x][1], type_attrs.keys())

            # Construct a query based on the supplied attributes for this
            # object type.  If any of the attribute names aren't valid for
            # this type, then we don't bother matching, since this an AND
            # query and there aren't be any matches.
            q = "SELECT %s FROM objects_%s WHERE " % \
                (string.join(columns, ","), type_name)
            query_values = []
            for attr, value in attrs.items():
                q += "%s=? AND " % attr
                query_values.append(value)

            # Trim off last AND
            q = q[:-4]
            rows = self._db_query(q, query_values)
            #results.append((columns_dict, type_name, row))
            #results.extend(rows)
            results.append((columns, type_name, rows))

        return results

    def query_normalized(self, **attrs):
        """
        Performs a query as in query() and returns normalized results.
        """
        return self.normalize_query_results(self.query(**attrs))

    def normalize_query_results(self, results):
        """
        Takes a results list as returned from query() and converts to a list
        of dicts.  Each result dict is given a "type" entry which corresponds 
        to the type name of that object.
        """
        new_results = []
        for columns, type_name, rows in results:
            for row in rows:
                result = dict(zip(columns, row))
                result["type"] = type_name
                if result["pickle"]:
                    pickle = cPickle.loads(str(result["pickle"]))
                    del result["pickle"]
                    result.update(pickle)
                new_results.append(result)
        return new_results


    def list_query_results_names(self, results):
        """
        Do a quick-and-dirty list of filenames given a query results list,
        sorted by filename.
        """
        # XXX: should be part of VFS, not database.
        files = []
        for columns, type_name, rows in results:
            filecol = columns.index("name")
            for row in rows:
                files.append(row[filecol])
        files.sort()
        return files

