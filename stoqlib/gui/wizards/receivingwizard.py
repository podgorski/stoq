# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2006-2007 Async Open Source <http://www.async.com.br>
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
## Author(s):   Evandro Vale Miquelito      <evandro@async.com.br>
##              Fabio Morbec                <fabio@async.com.br>
##              Johan Dahlin                <jdahlin@async.com.br>
##
##
""" Receiving wizard definition """

import datetime
from decimal import Decimal

from kiwi.datatypes import currency
from kiwi.ui.objectlist import Column, SearchColumn
from kiwi.ui.search import SearchSlaveDelegate, DateSearchFilter

from stoqlib.database.orm import ORMObjectQueryExecuter
from stoqlib.database.runtime import get_current_user
from stoqlib.lib.translation import stoqlib_gettext
from stoqlib.gui.base.wizards import WizardEditorStep, BaseWizard
from stoqlib.gui.base.dialogs import run_dialog
from stoqlib.gui.slaves.receivingslave import ReceivingInvoiceSlave
from stoqlib.gui.wizards.abstractwizard import SellableItemStep
from stoqlib.gui.dialogs.purchasedetails import PurchaseDetailsDialog
from stoqlib.gui.editors.receivingeditor import ReceivingItemEditor
from stoqlib.lib.validators import format_quantity, get_formatted_cost
from stoqlib.domain.purchase import PurchaseOrder, PurchaseOrderView
from stoqlib.domain.receiving import (ReceivingOrder, ReceivingOrderItem,
                                      get_receiving_items_by_purchase_order)

_ = stoqlib_gettext


# Workaround, so PurchaseSelectionStep does not complain about empty model
class _FakeReceivingOrder(object):
    pass

#
# Wizard Steps
#


class PurchaseSelectionStep(WizardEditorStep):
    gladefile = 'PurchaseSelectionStep'
    model_type = _FakeReceivingOrder

    def __init__(self, wizard, conn, model):
        self._next_step = None
        WizardEditorStep.__init__(self, conn, wizard, model)

    def _refresh_next(self, validation_value):
        has_selection = self.search.results.get_selected() is not None
        self.wizard.refresh_next(has_selection)

    def _create_search(self):
        self.search = SearchSlaveDelegate(self._get_columns())
        self.search.enable_advanced_search()
        self.attach_slave('searchbar_holder', self.search)
        self.executer = ORMObjectQueryExecuter()
        self.search.set_query_executer(self.executer)
        self.executer.set_table(PurchaseOrderView)
        self.executer.add_query_callback(self._get_extra_query)
        self._create_filters()
        self.search.results.connect('selection-changed',
                                    self._on_results__selection_changed)
        self.search.results.connect('row-activated',
                                    self._on_results__row_activated)
        self.search.focus_search_entry()

    def _create_filters(self):
        self.search.set_text_field_columns(['supplier_name'])

    def _get_extra_query(self, states):
        return PurchaseOrderView.q.status == PurchaseOrder.ORDER_CONFIRMED

    def _get_columns(self):
        return [SearchColumn('id', title=_('Number'), sorted=True,
                             data_type=str, width=80),
                SearchColumn('open_date', title=_('Date Started'),
                             data_type=datetime.date, width=100),
                SearchColumn('expected_receival_date', data_type=datetime.date,
                             title=_('Expected Receival'),  visible=False),
                SearchColumn('supplier_name', title=_('Supplier'),
                             data_type=str, searchable=True, width=130,
                             expand=True),
                SearchColumn('ordered_quantity', title=_('Qty Ordered'),
                             data_type=Decimal, width=110,
                             format_func=format_quantity),
                SearchColumn('received_quantity', title=_('Qty Received'),
                             data_type=Decimal, width=145,
                             format_func=format_quantity),
                SearchColumn('total', title=_('Order Total'),
                             data_type=currency, width=120)]

    def _update_view(self):
        has_selection = self.search.results.get_selected() is not None
        self.details_button.set_sensitive(has_selection)

    #
    # WizardStep hooks
    #

    def post_init(self):
        self._update_view()
        self.register_validate_function(self._refresh_next)
        self.force_validation()

    def next_step(self):
        selected = self.search.results.get_selected()
        purchase = selected.purchase

        # We cannot create the model in the wizard since we haven't
        # selected a PurchaseOrder yet which ReceivingOrder depends on
        # Create the order here since this is the first place where we
        # actually have a purchase selected
        if not self.wizard.model:
            self.wizard.model = self.model = ReceivingOrder(
                responsible=get_current_user(self.conn),
                supplier=None, invoice_number=None,
                branch=None, purchase=purchase,
                connection=self.conn)

        # Remove all the items added previously, used if we hit back
        # at any point in the wizard.
        if self.model.purchase != purchase:
            self.model.remove_items()
            # This forces ReceivingOrderProductStep to create a new model
            self._next_step = None

        if selected:
            self.model.purchase = purchase
            self.model.branch = purchase.branch
            self.model.supplier = purchase.supplier
            self.model.transporter = purchase.transporter
        else:
            self.model.purchase = None

        # FIXME: Improve the infrastructure to avoid this local caching of
        #        Wizard steps.
        if not self._next_step:
            # Remove all the items added previously, used if we hit back
            # at any point in the wizard.
            self._next_step = ReceivingOrderProductStep(self.wizard,
                                                        self, self.conn,
                                                        self.model)
        return self._next_step

    def has_previous_step(self):
        return False

    def setup_slaves(self):
        self._create_search()

    #
    # Kiwi callbacks
    #

#     def on_searchbar_activate(self, slave, objs):
#         """Use this callback with SearchBar search-activate signal"""
#         self.results.add_list(objs, clear=True)
#         has_selection = self.results.get_selected() is not None
#         self.wizard.refresh_next(has_selection)

    def _on_results__selection_changed(self, results, purchase_order_view):
        self.force_validation()
        self._update_view()

    def _on_results__row_activated(self, results, purchase_order_view):
        run_dialog(PurchaseDetailsDialog, self, self.conn,
                   model=purchase_order_view.purchase)

    def on_details_button__clicked(self, *args):
        selected = self.search.results.get_selected()
        if not selected:
            raise ValueError('You should have one order selected '
                             'at this point, got nothing')
        run_dialog(PurchaseDetailsDialog, self, self.conn,
                   model=selected.purchase)


class ReceivingOrderProductStep(SellableItemStep):
    model_type = ReceivingOrder
    item_table = ReceivingOrderItem
    summary_label_text = "<b>%s</b>" % _('Total Received:')

    def _validate(self, value):
        has_receivings = self.model.get_total() > 0
        self.wizard.refresh_next(has_receivings)
        return has_receivings

    #
    # SellableItemStep overrides
    #

    def setup_sellable_entry(self):
        # We do not use the sellable entry in this step, so no action needs to
        # be performed here.
        pass

    #
    # WizardStep hooks
    #

    def post_init(self):
        # Hide the search bar, since it does not make sense to add new
        # items to a receivable order.
        self.item_hbox.hide()
        self.slave.hide_add_button()
        self.slave.hide_del_button()
        self.slave.set_editor(ReceivingItemEditor)
        self._refresh_next()
        self.register_validate_function(self._validate)

    def next_step(self):
        # Remove the items that will not be received now.
        for item in self.model.get_items():
            if item.quantity == 0:
                ReceivingOrderItem.delete(item.id, connection=self.conn)

        return ReceivingInvoiceStep(self.conn, self.wizard, self.model, self)

    def get_columns(self):
        return [
            Column('sellable.description', title=_('Description'),
                   data_type=str, expand=True, searchable=True),
            Column('remaining_quantity', title=_('Quantity'), data_type=int,
                   width=90, format_func=format_quantity, expand=True),
            Column('quantity', title=_('Quantity to receive'), data_type=int,
                   width=110, format_func=format_quantity),
            Column('sellable.unit_description', title=_('Unit'), data_type=str,
                   width=50),
            Column('cost', title=_('Cost'), data_type=currency,
                   format_func=get_formatted_cost, width=90),
            Column('total', title=_('Total'), data_type=currency, width=100)
            ]


    def get_order_item(self, sellable, cost, quantity):
        # Never called in this wizard.
        return

    def get_saved_items(self):
        if not self.model.purchase:
            return []
        return get_receiving_items_by_purchase_order(self.model.purchase,
                                                     self.model)


class ReceivingInvoiceStep(WizardEditorStep):
    gladefile = 'HolderTemplate'
    model_type = ReceivingOrder

    #
    # WizardStep hooks
    #

    def has_next_step(self):
        return False

    def post_init(self):
        self.invoice_slave = ReceivingInvoiceSlave(self.conn, self.model)
        self.attach_slave("place_holder", self.invoice_slave)
        self.register_validate_function(self.wizard.refresh_next)
        self.force_validation()


#
# Main wizard
#

class ReceivingOrderWizard(BaseWizard):
    title = _("Receiving Order")
    size = (750, 350)

    def __init__(self, conn):
        self.model = None
        first_step = PurchaseSelectionStep(self, conn,
                                           _FakeReceivingOrder())
        BaseWizard.__init__(self, conn, first_step, self.model)
        self.next_button.set_sensitive(False)

    #
    # WizardStep hooks
    #

    def finish(self):
        assert self.model
        assert self.model.branch

        if not self.model.get_valid():
            self.model.set_valid()
        self.retval = self.model
        self.model.confirm()
        self.close()
