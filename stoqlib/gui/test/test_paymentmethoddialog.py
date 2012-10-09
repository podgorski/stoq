# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2012 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##

import mock

from stoqlib.database.runtime import StoqlibTransaction
from stoqlib.gui.dialogs.paymentmethod import PaymentMethodsDialog
from stoqlib.gui.editors.paymentmethodeditor import MoneyPaymentMethodEditor
from stoqlib.gui.uitestutils import GUITest


class TestPaymentMethodsDialog(GUITest):
    def test_show(self):
        dialog = PaymentMethodsDialog(self.trans)
        self.check_dialog(dialog, 'payment-methods-dialog-show')

    @mock.patch('stoqlib.gui.dialogs.paymentmethod.run_dialog')
    def test_edit_button(self, run_dialog):
        payment_method = self.get_payment_method('money')

        dialog = PaymentMethodsDialog(self.trans)
        dialog.klist.select(payment_method)
        self.click(dialog._toolbar_slave.edit_button)

        run_dialog.assert_called_once()

        args, kwargs = run_dialog.call_args
        editor, payment_dialog, trans, method = args

        self.assertEquals(editor, MoneyPaymentMethodEditor)
        self.assertEquals(payment_dialog, dialog)
        self.assertTrue(isinstance(trans, StoqlibTransaction))
        # comparing both objects does not work because they are in different
        # transactions
        self.assertEquals(method.id, payment_method.id)