# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2006 Async Open Source <http://www.async.com.br>
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
## Author(s):   Johan Dahlin  <jdahlin@async.com.br>
##

import datetime

from stoqlib.database.runtime import get_current_station
from stoqlib.domain.interfaces import (IBranch, ICompany, IEmployee,
                                       IIndividual, ISupplier,
                                       ISellable, IStorable, ISalesPerson,
                                       IClient, IUser)
from stoqlib.lib.parameters import sysparam

def create_person(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('Person')

def create_branch(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('IBranch')

def create_supplier(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('ISupplier')

def create_employee(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('IEmployee')

def create_salesperson(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('ISalesPerson')

def create_client(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('IClient')

def create_individual(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('IIndividual')

def create_user(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('IUser')

def create_storable(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('ProductAdaptToStorable')

def create_product(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('Product')

def create_sellable(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('ProductAdaptToSellable')

def create_sale(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('Sale')

def create_city_location(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('CityLocation')

def create_parameter_data(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('ParameterData')

def create_service_sellable_item(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('ServiceSellableItem')

def create_device_settings(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('DeviceSettings')

def create_company(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('ICompany')

def create_till(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('Till')

def create_user_profile(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('UserProfile')

def get_station(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('BranchStation')

def get_location(trans):
    ex = ExampleCreator(trans)
    return ex.create_by_type('CityLocation')



class ExampleCreator(object):
    def __init__(self, trans):
        self.trans = trans

    def create_by_type(self, model_type):
        known_types = {
            'ASellable': self.create_sellable,
            'BranchStation': self.get_station,
            'CityLocation': self.get_location,
            'IClient': self.create_client,
            'IBranch': self.create_branch,
            'IEmployee': self.create_employee,
            'IIndividual': self.create_individual,
            'ISupplier': self.create_supplier,
            'IUser': self.create_user,
            'ParameterData': self.create_parameter_data,
            'Person': self.create_person,
            'PersonAdaptToBranch': self.create_branch,
            'PersonAdaptToCompany': self.create_company,
            'PersonAdaptToClient': self.create_client,
            'PersonAdaptToUser': self.create_user,
            'Product': self.create_product,
            'ProductAdaptToSellable' : self.create_sellable,
            'Sale': self.create_sale,
            'ServiceSellableItem': self.create_service_sellable_item,
            'Till': self.create_till,
            'UserProfile': self.create_user_profile,
            }
        if isinstance(model_type, basestring):
            model_name = model_type
        else:
            model_name = model_type.__name__
        if model_name in known_types:
            return known_types[model_name]()

    def create_person(self):
        from stoqlib.domain.person import Person
        return Person(name='John', connection=self.trans)

    def create_branch(self):
        from stoqlib.domain.person import Person
        person = Person(name='Dummy', connection=self.trans)
        person.addFacet(ICompany, fancy_name='Dummy shop',
                        connection=self.trans)
        return person.addFacet(IBranch, connection=self.trans)

    def create_supplier(self):
        from stoqlib.domain.person import Person
        person = Person(name='Supplier', connection=self.trans)
        person.addFacet(ICompany, fancy_name='Company Name',
                        connection=self.trans)
        return person.addFacet(ISupplier, connection=self.trans)


    def create_employee(self):
        from stoqlib.domain.person import Person, EmployeeRole
        person = Person(name='SalesPerson', connection=self.trans)
        person.addFacet(IIndividual, connection=self.trans)
        role = EmployeeRole(name='Role', connection=self.trans)
        return person.addFacet(IEmployee, role=role, connection=self.trans)

    def create_salesperson(self):
        employee = self.create_employee()
        return employee.person.addFacet(ISalesPerson, connection=self.trans)

    def create_client(self):
        from stoqlib.domain.person import Person
        person = Person(name='Client', connection=self.trans)
        person.addFacet(IIndividual, connection=self.trans)
        return person.addFacet(IClient, connection=self.trans)

    def create_individual(self):
        from stoqlib.domain.person import Person
        person = Person(name='individual', connection=self.trans)
        return person.addFacet(IIndividual, connection=self.trans)

    def create_user(self):
        individual = self.create_individual()
        profile = self.create_user_profile()
        return individual.person.addFacet(IUser, username='username',
                                          password='password',
                                          profile=profile,
                                          connection=self.trans)

    def create_storable(self):
        from stoqlib.domain.product import Product
        product = Product(connection=self.trans)
        return product.addFacet(IStorable, connection=self.trans)

    def create_product(self):
        from stoqlib.domain.product import ProductSupplierInfo
        sellable = self.create_sellable()
        product = sellable.get_adapted()
        product.addFacet(IStorable, connection=self.trans)
        ProductSupplierInfo(connection=self.trans,
                            supplier=self.create_supplier(),
                            product=product, is_main_supplier=True)
        return product

    def create_sellable(self):
        from stoqlib.domain.product import Product
        from stoqlib.domain.sellable import BaseSellableInfo
        product = Product(connection=self.trans)
        sellable_info = BaseSellableInfo(connection=self.trans,
                                         description="Description",
                                         price=10)
        return product.addFacet(ISellable,
                                base_sellable_info=sellable_info,
                                connection=self.trans)
    def create_sale(self):
        from stoqlib.domain.sale import Sale
        from stoqlib.domain.till import Till
        till = Till.get_current(self.trans)
        salesperson = self.create_salesperson()
        return Sale(till=till,
                    coupon_id=0,
                    open_date=datetime.datetime.now(),
                    salesperson=salesperson,
                    cfop=sysparam(self.trans).DEFAULT_SALES_CFOP,
                    connection=self.trans)

    def create_city_location(self):
        from stoqlib.domain.address import CityLocation
        return CityLocation(country='Groenlandia',
                            city='Acapulco',
                            state='Wisconsin',
                            connection=self.trans)

    def create_parameter_data(self):
        from stoqlib.domain.parameter import ParameterData
        return ParameterData.select(connection=self.trans)[0]

    def create_service_sellable_item(self):
        from stoqlib.domain.service import ServiceSellableItem
        sale = self.create_sale()
        sellable = self.create_sellable()
        return ServiceSellableItem(
            sellable=sellable,
            quantity=1, price=10,
            sale=sale, connection=self.trans)

    def create_device_settings(self):
        from stoqlib.lib.drivers import get_fiscal_printer_settings_by_station

        station = get_current_station(self.trans)
        return get_fiscal_printer_settings_by_station(self.trans, station)

    def create_company(self):
        from stoqlib.domain.person import Person
        person = Person(name='Dummy', connection=self.trans)
        return person.addFacet(ICompany, fancy_name='Dummy shop',
                               connection=self.trans)

    def create_till(self):
        from stoqlib.domain.till import Till
        station = get_current_station(self.trans)
        return Till(connection=self.trans, station=station)

    def create_user_profile(self):
        from stoqlib.domain.profile import UserProfile
        return UserProfile(connection=self.trans, name='assistant')

    def get_station(self):
        return get_current_station(self.trans)

    def get_location(self):
        from stoqlib.domain.address import CityLocation
        return CityLocation.get_default(self.trans)

