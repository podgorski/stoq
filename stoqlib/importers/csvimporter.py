# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2007 Async Open Source
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU Lesser General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##
## Author(s):       Johan Dahlin                <jdahlin@async.com.br>
##
##

import csv

from kiwi.python import namedAny

from stoqlib.database.runtime import new_transaction

class CSVDataLine:
    pass

class CSVImporter(object):
    """
    @cvar fields: field names, a list of strings
    @cvar optional_fields: optional field names, a list of strings
    """
    fields = []
    optional_fields = []

    # Available importers, the value is relative to stoqlib.importers
    _available_importers = {
        'client': 'clientimporter.ClientImporter',
        'employee': 'employeeimporter.EmployeeImporter',
        'product': 'productimporter.ProductImporter',
        'service': 'serviceimporter.ServiceImporter',
        }

    #
    # Public API
    #

    def feed_file(self, filename):
        """
        Feeds csv data from filename to the importer
        @param filename: filename
        """
        self.feed(open(filename), filename)

    def feed(self, iterable, filename='<stdin>'):
        """
        Feeds csv data from an iterable
        @param iterable: an iterable
        @param filename: optinal filename
        """
        field_names = self.fields + self.optional_fields

        trans = new_transaction()
        lineno = 1
        for item in csv.reader(iterable):
            if not item or item[0].startswith('%'):
                lineno += 1
                continue
            if len(item) < len(self.fields):
                raise ValueError(
                    "line %d in file %s has %d fields, but we need at "
                    "least %d fields to be able to process it, fields=%s" % (
                    lineno, filename, len(item), len(self.fields)))
            if len(item) > len(field_names):
                raise ValueError(
                    "line %d in file %s has %d fields, but we can at most "
                    "handle %d fields" % (
                    lineno, filename, len(item), len(field_names), list(item)))

            data = CSVDataLine()
            fields = []
            for i, field in enumerate(item):
                setattr(data, field_names[i], field)
                fields.append(field_names[i])

            self.process_one(data, fields, trans)

            lineno += 1
        trans.commit()

    #
    # Classmethods
    #

    @classmethod
    def get_by_type(cls, importer_type):
        """
        Gets an importers class, instantiates it returns it
        @param importer_type: an importer
        @type importer_type: string
        @returns: an importer instance
        @type: L{CSVImporter} subclass
        """
        if not importer_type in cls._available_importers:
            raise ValueError("Invalid importer %s, must be one of %s" % (
                importer_type, ', '.join(sorted(cls._available_importers))))
        name = cls._available_importers[importer_type]
        importer_cls = namedAny('stoqlib.importers.%s' % (name,))
        return importer_cls()

    #
    # Override this in a subclass
    #

    def process_one(self, data, fields, trans):
        """
        Processes one line in a csv file, you can access the columns
        using attributes on the data object.
        @param data: object with data attributes
        @param fields: a list of fields set in data
        @param trans: a database transaction
        """
        raise NotImplementedError
