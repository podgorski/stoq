# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4
##
## Copyright (C) 2012 Async Open Source
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
## Author(s): Stoq Team <stoq-devel@async.com.br>
##

from kiwi.accessor import kgetattr
from kiwi.environ import environ

from stoqlib.database.runtime import get_default_store
from stoqlib.lib.template import render_template
from stoqlib.lib.translation import stoqlib_gettext, stoqlib_ngettext
from stoqlib.reporting.template import get_logotype_path

_ = stoqlib_gettext


class HTMLReport(object):
    template_filename = None
    title = ''
    complete_header = True

    def __init__(self, filename):
        self.filename = filename
        self.logo_path = get_logotype_path(get_default_store())

    def get_html(self):
        assert self.title
        namespace = self.get_namespace()
        # Set some defaults if the report did not provide one
        namespace.setdefault('subtitle', '')
        namespace.setdefault('notes', [])
        return render_template(self.template_filename,
                               title=self.title,
                               complete_header=self.complete_header,
                               logo_path=self.logo_path,
                               _=stoqlib_gettext,
                               **namespace)

    def save_html(self, filename):
        html = open(filename, 'w')
        html.write(self.get_html())
        html.flush()

    def save(self):
        import weasyprint
        template_dirs = environ.get_resource_paths('template')
        html = weasyprint.HTML(string=self.get_html(),
                               base_url=template_dirs[0])
        html.write_pdf(self.filename)

    #
    # Hook methods
    #

    def get_namespace(self):
        """This hook method must be implemented by children and returns
        parameters that will be passed to report template in form of a dict.
        """
        raise NotImplementedError

    def adjust_for_test(self):
        """This hook method must be implemented by children that generates
        reports with data that change with the workstation or point in time.
        This allows for the test reports to be always generated with the same
        data.
        """
        self.logo_path = 'logo.png'


class ObjectListReport(HTMLReport):
    """Creates an pdf report from an objectlist and its current state

    This report will only show the columns that are visible, in the order they
    are visible. It will also show the filters that were enabled when the report
    was generated.
    """
    #: Defines the columns that should have a summary in the last row of the
    #: report. This is a list of strings defining the attribute of the
    #: respective column. Currently, only numeric values are supported (Decimal,
    #: currenty, etc..)
    summary = []

    title = None
    subtitle_template = _("Listing {rows} of a total of {total_rows} {item}")
    main_object_name = (_("item"), _("items"))
    template_filename = "objectlist.html"
    filter_format_string = ""
    complete_header = False

    def __init__(self, filename, objectlist, data, title=None, blocked_records=0,
                 status_name=None, filter_strings=[], status=None,
                 do_footer=None):
        # TODO: do_footer
        if do_footer is not None:
            print 'do_footer', do_footer
        self.title = title or self.title
        self.blocked_records = blocked_records
        self.status_name = status_name
        self.status = status
        self.filter_strings = filter_strings
        self.data = data

        self._setup_details()

        self.columns = []
        for c in objectlist.get_columns():
            if not c.treeview_column.get_visible():
                continue
            import gtk
            if c.data_type == gtk.gdk.Pixbuf:
                continue

            self.columns.append(c)
        HTMLReport.__init__(self, filename)

    def _setup_details(self):
        """ This method build the report title based on the arguments sent
        by SearchBar to its class constructor.
        """
        rows = len(self.data)
        total_rows = rows + self.blocked_records
        item = stoqlib_ngettext(self.main_object_name[0],
                                self.main_object_name[1], total_rows)
        self.subtitle = self.subtitle_template.format(rows=rows,
                                        total_rows=total_rows, item=item)

        base_note = ""
        if self.filter_format_string and self.status_name:
            base_note += self.filter_format_string % self.status_name.lower()

        notes = []
        for filter_string in self.filter_strings:
            if base_note:
                notes.append('%s %s' % (base_note, filter_string))
            elif filter_string:
                notes.append(filter_string)
        self.notes = notes

    def get_namespace(self):
        return dict(report=self)

    def get_data(self):
        self.reset()
        for obj in self.data:
            row = []
            self.accumulate(obj)
            for c in self.columns:
                data_source = c.as_string(kgetattr(obj, c.attribute, None))
                row.append(data_source)
            yield row

    def accumulate(self, row):
        """This method is called once for each row in the report.

        Here you can create summaries (like the sum of all payments) for the
        report, that will be added in the last row of the table
        """
        for i in self.summary:
            self._summary[i] += getattr(row, i, 0) or 0

    def reset(self):
        """This is called when the iteration on all the rows starts.

        Use this to setup or reset any necesary data (like the summaries)
        """
        self._summary = {}
        for i in self.summary:
            self._summary[i] = 0

    def get_summary(self):
        """Returns a summary row for the report
        """
        if not self.summary:
            return []

        row = []
        for column in self.columns:
            value = self._summary.get(column.attribute, '')
            if value:
                value = column.as_string(value)
            row.append(value)
        return row
