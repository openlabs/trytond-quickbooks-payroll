# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from quickbooks import PayrollAccount


def register():
    Pool.register(
        PayrollAccount,
        module='quickbooks_payroll', type_='model'
    )
