# -*- coding: utf-8 -*-
"""
    tests/conftest.py

    :copyright: (C) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import os
import time
import datetime
from dateutil.relativedelta import relativedelta

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--db", action="store", default="sqlite",
        help="Run on database: sqlite or postgres"
    )


@pytest.fixture(scope='session')
def install_module(request):
    """Install tryton module in specified database.
    """
    if request.config.getoption("--db") == 'sqlite':
        os.environ['TRYTOND_DATABASE_URI'] = "sqlite://"
        os.environ['DB_NAME'] = ':memory:'

    elif request.config.getoption("--db") == 'postgres':
        os.environ['TRYTOND_DATABASE_URI'] = "postgresql://"
        os.environ['DB_NAME'] = 'test_' + str(int(time.time()))

    from trytond.tests import test_tryton
    test_tryton.install_module('quickbooks_payroll')


@pytest.yield_fixture()
def transaction(request):
    """Yields transaction with installed module.
    """
    from trytond.transaction import Transaction
    from trytond.tests.test_tryton import USER, CONTEXT, DB_NAME, POOL

    # Inject helper functions in instance on which test function was collected.
    request.instance.POOL = POOL
    request.instance.USER = USER
    request.instance.CONTEXT = CONTEXT
    request.instance.DB_NAME = DB_NAME

    with Transaction().start(DB_NAME, USER, context=CONTEXT) as transaction:
        yield transaction

        transaction.cursor.rollback()


@pytest.fixture(scope='session')
def test_dataset(request):
    """Create minimal data needed for testing
    """
    from trytond.transaction import Transaction
    from trytond.tests.test_tryton import USER, CONTEXT, DB_NAME, POOL

    Party = POOL.get('party.party')
    Company = POOL.get('company.company')
    Employee = POOL.get('company.employee')
    Currency = POOL.get('currency.currency')
    User = POOL.get('res.user')
    FiscalYear = POOL.get('account.fiscalyear')
    Sequence = POOL.get('ir.sequence')
    AccountTemplate = POOL.get('account.account.template')
    Account = POOL.get('account.account')
    account_create_chart = POOL.get('account.create_chart', type="wizard")

    with Transaction().start(DB_NAME, USER, context=CONTEXT) as transaction:
        # Create company, employee and set it user's current company
        usd, = Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])
        company_party, = Party.create([{
            'name': 'Openlabs Technologies and Consulting (P) LTD.',
        }])
        employee_party, = Party.create([{
            'name': 'Prakash Pandey',
        }])
        company, = Company.create([{
            'party': company_party.id,
            'currency': usd.id,
        }])
        employee, = Employee.create([{
            'party': employee_party.id,
            'company': company.id,
        }])
        User.write(
            [User(USER)], {
                'main_company': company.id,
                'company': company.id,
            }
        )
        CONTEXT.update(User.get_preferences(context_only=True))

        # Create fiscal year
        date = datetime.date.today()

        fiscal_year, = FiscalYear.create([{
            'name': '%s' % date.year,
            'start_date': date + relativedelta(month=1, day=1),
            'end_date': date + relativedelta(month=12, day=31),
            'company': company.id,
            'post_move_sequence': Sequence.create([{
                'name': '%s' % date.year,
                'code': 'account.move',
                'company': company.id,
            }])[0],
        }])
        FiscalYear.create_period([fiscal_year])

        # Create minimal chart of account
        account_template, = AccountTemplate.search(
            [('parent', '=', None)]
        )

        session_id, _, _ = account_create_chart.create()
        create_chart = account_create_chart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()

        receivable, = Account.search([
            ('kind', '=', 'receivable'),
            ('company', '=', company.id),
        ])
        payable, = Account.search([
            ('kind', '=', 'payable'),
            ('company', '=', company.id),
        ])
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()

        transaction.cursor.commit()
