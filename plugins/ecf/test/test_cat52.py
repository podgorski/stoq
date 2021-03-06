# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2007-2008 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
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

import datetime
from decimal import Decimal
import os

from kiwi.component import get_utility

from stoqlib.domain.devices import FiscalDayHistory, FiscalDayTax
from stoqlib.domain.test.domaintest import DomainTest
from stoqlib.lib.diffutils import diff_files
from stoqlib.lib.interfaces import IAppInfo
from stoqlib.lib.unittestutils import get_tests_datadir

from ecf.cat52 import CATFile
from ecf.catgenerator import async
from ecf.ecfdomain import ECFPrinter, FiscalSaleHistory


def compare_files(sfile, basename):
    expected = basename + '-expected.txt'
    output = basename + '-output.txt'

    sfile.write(output)
    expected = get_tests_datadir('plugins', expected)
    diff = diff_files(expected, output)
    os.unlink(output)
    return diff


class Cat52Test(DomainTest):
    def test_complete(self):
        station = self.create_station()
        today = datetime.date(2007, 1, 1)
        reduction_date = datetime.datetime(2007, 1, 1, 23, 59)
        day = FiscalDayHistory(store=self.store,
                               emission_date=today,
                               station=station,
                               serial=u'serial',
                               serial_id=1,
                               coupon_start=1,
                               coupon_end=23,
                               crz=18,
                               cro=25,
                               period_total=Decimal("456.00"),
                               total=Decimal("123141.00"),
                               reduction_date=reduction_date)
        for code, value, type in [(u'2500', Decimal("123.00"), u'ICMS'),
                                  (u'F', Decimal("789.00"), u'ICMS')]:
            FiscalDayTax(fiscal_day_history=day, code=code,
                         value=value, type=type,
                         store=self.store)

        printer = ECFPrinter(
            store=self.store,
            model=u'FS345',
            brand=u'daruma',
            device_name=u'test',
            device_serial=u'serial',
            baudrate=9600,
            station=station,
            user_number=1,
            register_date=today,
            register_cro=1,
        )

        f = CATFile(printer)
        f.software_version = '6.6.6'  # kiko sends <3

        appinfo = get_utility(IAppInfo)
        f.add_software_house(async, appinfo.get('name'),
                             appinfo.get('version'))
        # Cant call add_ecf_identification, since it depends on a
        # conected printer
        # f.add_ecf_identification()

        for item in self.store.find(FiscalDayHistory):
            f.add_z_reduction(item)
            for i, tax in enumerate(item.taxes):
                f.add_z_reduction_details(item, tax, i + 1)

        sale = self.create_sale()
        sale.client = self.create_client()
        sale.confirm_date = today
        sellable = self.add_product(sale, price=100)
        sellable.code = u'09999'

        self.add_payments(sale)
        history = FiscalSaleHistory(store=self.store,
                                    sale=sale)

        f.add_fiscal_coupon(sale, sale.client, history)
        for i, item in enumerate(sale.get_items()):
            f.add_fiscal_coupon_details(sale, sale.client, history,
                                        item, 800, i + 1)

        for payment in sale.payments:
            f.add_payment_method(sale, history, payment)

        diff = compare_files(f, 'cat52')
        self.failIf(diff, '%s\n%s' % ("Files differ, output:", diff))
