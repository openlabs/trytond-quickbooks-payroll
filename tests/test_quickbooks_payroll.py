# -*- coding: utf-8 -*-
"""
    tests/test_quickbooks_payroll.py

    :copyright: (C) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import csv
import tempfile


class TestQuickBooksPayroll:

    def test_views(self, install_module):
        "Test all tryton views"

        from trytond.tests.test_tryton import test_view
        test_view('quickbooks_payroll')

    def test_depends(self, install_module):
        "Test missing depends on fields"

        from trytond.tests.test_tryton import test_depends
        test_depends()

    def test_import_payroll_item(self, test_dataset, transaction):
        "Test import payroll item wizard"
        Date = self.POOL.get('ir.date')
        Account = self.POOL.get('account.account')
        Move = self.POOL.get('account.move')
        Employee = self.POOL.get('company.employee')
        QuickBooksPayroll = self.POOL.get('quickbooks.payroll_account')
        ImportPayrollItem = self.POOL.get(
            'quickbooks.wizard_import_payroll_item', type='wizard'
        )

        # Map quickbooks payroll item to tryton
        main_expense, = Account.search([('name', '=', 'Main Expense')])
        main_expense.party_required = True
        main_expense.save()

        main_tax, = Account.search([('name', '=', 'Main Tax')])
        main_tax.party_required = True
        main_tax.save()

        main_cash, = Account.search([('name', '=', 'Main Cash')])

        QuickBooksPayroll.create([{
            'account': main_expense.id,
            'payroll_item': 'Salary Expense',
        }, {
            'account': main_tax.id,
            'payroll_item': 'Federal Income Taxes Payable',
        }, {
            'account': main_tax.id,
            'payroll_item': 'State Income Taxes Payable',
        }, {
            'account': main_tax.id,
            'payroll_item': 'FICA Taxes Payable',
        }])

        # Map employee to quickbooks source name
        employee, = Employee.search([])
        employee.quickbooks_source_name = 'Pandey, Prakash'
        employee.save()

        credit_account, = Account.search([], limit=1)

        import_payroll_item = ImportPayrollItem(
            ImportPayrollItem.create()[0]
        )

        import_payroll_item.start.credit_account = main_cash

        with tempfile.NamedTemporaryFile(delete=False) as csv_file:
            csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
            csv_writer.writerow([
                'Date', 'Num', 'Type', 'Source Name', 'Payroll Item',
                'Wage Base', 'Amount',
            ])
            csv_writer.writerow([
                Date.today(), '309333', 'Cash', "Pandey, Prakash",
                'Salary Expense', '', '-100000',
            ])
            csv_writer.writerow([
                '', '', '', "Pandey, Prakash", 'Federal Income Taxes Payable',
                '', 15000,

            ])
            csv_writer.writerow([
                '', '', '', "Pandey, Prakash", 'State Income Taxes Payable',
                '', 5000,

            ])
            csv_writer.writerow([
                '', '', '', "Pandey, Prakash", 'FICA Taxes Payable', '', 7650,
            ])
            csv_writer.writerow([
                '', '', '', '', '', '', 72350
            ])
            csv_file.flush()

        import_payroll_item.start.csv_file = \
            buffer(open(csv_file.name).read())

        _, res = import_payroll_item.do_import_(action=None)

        move, = Move.search([])

        assert move.id in res['res_id']
        assert len(move.lines) == 5

        Move.post([move])
