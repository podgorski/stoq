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
##  Author(s):  Evandro Vale Miquelito      <evandro@async.com.br>
##              Fabio Morbec                <fabio@async.com.br>
##              Johan Dahlin                <jdahlin@async.com.br>
##
""" Receiving management """

import datetime
from decimal import Decimal

from kiwi.argcheck import argcheck
from kiwi.datatypes import currency
from sqlobject import ForeignKey, IntCol, DateTimeCol, UnicodeCol

from stoqlib.database.columns import PriceCol, DecimalCol
from stoqlib.domain.base import Domain
from stoqlib.domain.interfaces import IStorable, IPaymentGroup
from stoqlib.domain.purchase import PurchaseOrder
from stoqlib.lib.defaults import quantize
from stoqlib.lib.parameters import sysparam
from stoqlib.lib.translation import stoqlib_gettext

_ = stoqlib_gettext


class ReceivingOrderItem(Domain):
    """This class stores information of the purchased items.

    B{Importante attributes}
        - I{quantity}: the total quantity received for a certain
          product
        - I{cost}: the cost for each product received
    """
    quantity = DecimalCol()
    cost = PriceCol()
    purchase_item = ForeignKey('PurchaseItem')
    sellable = ForeignKey('ASellable')
    receiving_order = ForeignKey('ReceivingOrder')

    #
    # Accessors
    #

    def get_remaining_quantity(self):
        """Get the remaining quantity from the purchase order this item
        is included in.
        @returns: the remaining quantity
        """
        return self.purchase_item.get_pending_quantity()

    def get_price(self):
        """Get the price of this item. It's used by the SellableItemEditor.
        @returns: the price
        """
        return self.sellable.cost

    def get_total(self):
        return currency(self.quantity * self.get_price())

    def get_quantity_unit_string(self):
        unit = self.sellable.unit
        return "%s %s" % (self.quantity,
                          unit and unit.description or u"")

    def get_unit_description(self):
        unit = self.sellable.unit
        return "%s" % (unit and unit.description or "")


class ReceivingOrder(Domain):
    """Receiving order definition."""

    (STATUS_PENDING,
     STATUS_CLOSED) = range(2)

    status = IntCol(default=STATUS_PENDING)
    receival_date = DateTimeCol(default=datetime.datetime.now)
    confirm_date = DateTimeCol(default=None)
    notes = UnicodeCol(default='')
    freight_total = PriceCol(default=0)
    surcharge_value = PriceCol(default=0)
    discount_value = PriceCol(default=0)

    # This is Brazil-specific information
    icms_total = PriceCol(default=0)
    ipi_total = PriceCol(default=0)
    invoice_number = IntCol()
    invoice_total = PriceCol(default=None)
    cfop = ForeignKey("CfopData")

    responsible = ForeignKey('PersonAdaptToUser')
    supplier = ForeignKey('PersonAdaptToSupplier')
    branch = ForeignKey('PersonAdaptToBranch')
    purchase = ForeignKey('PurchaseOrder')
    transporter = ForeignKey('PersonAdaptToTransporter', default=None)

    def _create(self, id, **kw):
        # ReceiveOrder objects must be set as valid explicitly
        kw['_is_valid_model'] = False
        conn = self.get_connection()
        if not 'cfop' in kw:
            kw['cfop'] = sysparam(conn).DEFAULT_RECEIVING_CFOP
        Domain._create(self, id, **kw)

    def confirm(self):
        conn = self.get_connection()
        # Stock management
        for item in self.get_items():
            # FIXME: Don't use sellable.get_adapted() here
            storable = IStorable(item.sellable.get_adapted(), None)
            if item.quantity > item.get_remaining_quantity():
                raise ValueError(
                    "Quantity received (%d) is greater than "
                    "quantity ordered (%d)" % (
                        item.quantity,
                        item.get_remaining_quantity()))
            if storable is not None:
                storable.increase_stock(item.quantity, self.branch)
            self.purchase.increase_quantity_received(item.sellable,
                                                     item.quantity)

        group = IPaymentGroup(self.purchase)
        group.create_icmsipi_book_entry(self.cfop, self.invoice_number,
                                        self.icms_total, self.ipi_total)

        if self.purchase.can_close():
            self.purchase.close()

    def get_items(self):
        conn = self.get_connection()
        return ReceivingOrderItem.selectBy(receiving_order=self,
                                           connection=conn)

    def remove_items(self):
        for item in self.get_items():
            item.receiving_order = None


    #
    # Properties
    #

    @property
    def receiving_number(self):
        return self.id


    #
    # Accessors
    #


    def get_transporter_name(self):
        if not self.transporter:
            return u""
        return self.transporter.get_description()

    def get_receiving_number_str(self):
        return u"%04d" % self.id

    def get_branch_name(self):
        return self.branch.get_description()

    def get_supplier_name(self):
        if not self.supplier:
            return u""
        return self.supplier.get_description()

    def get_responsible_name(self):
        return self.responsible.get_description()

    def get_products_total(self):
        total = sum([item.get_total() for item in self.get_items()],
                     currency(0))
        return currency(total)

    def get_order_number(self):
        return self.purchase.get_order_number_str()

    def get_receival_date_str(self):
        return self.receival_date.strftime("%x")

    def get_total(self):
        """
        Fetch the total, including discount and surcharge for both the
        purchase order and the receiving order.
        """

        total = self.invoice_total or 0
        if self.discount_value:
            total -= self.discount_value
        if self.surcharge_value:
            total += self.surcharge_value

        if self.purchase.discount_value:
            total -= self.purchase.discount_value
        if self.purchase.surcharge_value:
            total += self.purchase.surcharge_value
        return currency(total)


    #
    # General methods
    #

    def reset_discount_and_surcharge(self):
        self.discount_value = self.surcharge_value = currency(0)

    def _get_percentage_value(self, percentage):
        if not percentage:
            return currency(0)
        subtotal = self.get_products_total()
        percentage = Decimal(percentage)
        return subtotal * (percentage / 100)

    def _set_discount_by_percentage(self, value):
        """Sets a discount by percentage.
        Note that percentage must be added as an absolute value not as a
        factor like 1.05 = 5 % of surcharge
        The correct form is 'percentage = 3' for a discount of 3 %
        """
        self.discount_value = self._get_percentage_value(value)

    def _get_discount_by_percentage(self):
        discount_value = self.discount_value
        if not discount_value:
            return currency(0)
        subtotal = self.get_products_total()
        assert subtotal > 0, ('the subtotal should not be zero '
                              'at this point')
        total = subtotal - discount_value
        percentage = (1 - total / subtotal) * 100
        return quantize(percentage)

    discount_percentage = property(_get_discount_by_percentage,
                                   _set_discount_by_percentage)

    def _set_surcharge_by_percentage(self, value):
        """Sets a surcharge by percentage.
        Note that surcharge must be added as an absolute value not as a
        factor like 0.97 = 3 % of discount.
        The correct form is 'percentage = 3' for a surcharge of 3 %
        """
        self.surcharge_value = self._get_percentage_value(value)

    def _get_surcharge_by_percentage(self):
        surcharge_value = self.surcharge_value
        if not surcharge_value:
            return currency(0)
        subtotal = self.get_products_total()
        assert subtotal > 0, ('the subtotal should not be zero '
                              'at this point')
        total = subtotal + surcharge_value
        percentage = ((total / subtotal) - 1) * 100
        return quantize(percentage)

    surcharge_percentage = property(_get_surcharge_by_percentage,
                                 _set_surcharge_by_percentage)


@argcheck(PurchaseOrder, ReceivingOrder)
def get_receiving_items_by_purchase_order(purchase_order, receiving_order):
    """Returns a list of receiving items based on a list of purchase items
    that weren't received yet.

    @param purchase_order: a PurchaseOrder instance that holds one or more
                           purchase items
    @param receiving_order: a ReceivingOrder instance tied with the
                            receiving_items that will be created
    """
    conn = purchase_order.get_connection()
    return [ReceivingOrderItem(connection=conn,
                               quantity=item.get_pending_quantity(),
                               cost=item.cost,
                               sellable=item.sellable,
                               purchase_item=item,
                               receiving_order=receiving_order)
            for item in purchase_order.get_pending_items()]
