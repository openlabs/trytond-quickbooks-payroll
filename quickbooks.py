# -*- coding: utf-8 -*-
"""
    Quickbooks

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import csv
import tempfile
from decimal import Decimal
from dateutil import parser

from trytond.pool import Pool
from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, Button, StateAction, StateView

__all__ = ['PayrollAccount']


class PayrollAccount(ModelSQL, ModelView):
    'Payroll Account'
    __name__ = 'quickbooks.payroll_account'
    _rec_name = 'payroll_item'

    account = fields.Property(
        fields.Many2One('account.account', 'Account', required=True)
    )
    payroll_item = fields.Char('Payroll Item')

    @classmethod
    def __setup__(cls):
        super(PayrollAccount, cls).__setup__()
        cls._error_messages.update({
            'party_required': 'Party must be required on account'
        })
        cls._sql_constraints = [(
            'payroll_item_uniq',
            'UNIQUE(payroll_item)',
            'Payroll Item must be unique per project'
        )]

    @classmethod
    def validate(cls, payroll_accounts):
        super(PayrollAccount, cls).validate(payroll_accounts)
        for account in payroll_accounts:
            account.check_account()

    def check_account(self):
        if not self.account.party_required:
            self.raise_user_error("party_required")


class ImportPayrollItemStart(ModelView):
    "Import Payroll Item Start View"
    __name__ = 'quickbooks.wizard_import_payroll_item.start'

    message = fields.Text("Message", readonly=True)
    credit_account = fields.Many2One(
        "account.account", "Credit Account", required=True,
        domain=[('kind', '!=', 'view')],
    )
    csv_file = fields.Binary("CSV File", required=True)


class ImportPayrollItem(Wizard):
    """
    Import payroll items from a csv file
    """
    __name__ = 'quickbooks.wizard_import_payroll_item'

    start = StateView(
        'quickbooks.wizard_import_payroll_item.start',
        'quickbooks_payroll.import_payroll_item_start',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Import', 'import_', 'tryton-ok', default=True),
        ]
    )

    import_ = StateAction('account.act_move_form')

    def get_quickbook_payroll_account(self, payroll_item):
        "Return account mapped to quickbook payroll item"
        QuickBooksPayroll = Pool().get('quickbooks.payroll_account')

        try:
            quickbooks_payroll, = QuickBooksPayroll.search([
                ('payroll_item', '=', payroll_item),
            ])
        except ValueError:
            self.raise_user_error(
                "Payroll item '%s' is not mapped to any account" % (
                    payroll_item,
                )
            )
        return quickbooks_payroll.account

    def get_quickbook_source_name(self, source_name):
        "Return party mapped to quickbook source name"
        Employee = Pool().get('company.employee')
        Party = Pool().get('party.party')
        try:
            employee, = Employee.search([
                ('quickbooks_source_name', '=', source_name)
            ])
            party = employee.party
        except ValueError:
            try:
                party, = Party.search([('name', '=', source_name)])
            except ValueError:
                self.raise_user_error(
                    "Source name '%s' not found" % (source_name, )
                )
        return party

    def do_import_(self, action):
        """Create account move from csv file.
        """
        Move = Pool().get('account.move')
        MoveLine = Pool().get('account.move.line')
        Journal = Pool().get('account.journal')

        csv_file = tempfile.NamedTemporaryFile(delete=False)
        csv_file.write(self.start.csv_file)
        csv_file.close()

        csv_reader = csv.DictReader(open(csv_file.name))

        # First row contains move number etc.
        first_row = csv_reader.next()

        try:
            journal, = Journal.search([('name', '=', first_row['Type'])])
        except ValueError:
            self.raise_user_error("Type '%s; not found" % (first_row['Type'], ))

        debit = credit = Decimal('0')
        if Decimal(first_row['Amount']) > 0:
            credit = Decimal(first_row['Amount'])
        else:
            debit = abs(Decimal(first_row['Amount']))

        move = Move(
            number=first_row['Num'],
            date=parser.parse(first_row['Date']).date(),
            journal=journal,
            lines=[
                MoveLine(
                    account=self.get_quickbook_payroll_account(
                        first_row['Payroll Item']
                    ),
                    debit=debit,
                    credit=credit,
                    party=self.get_quickbook_source_name(
                        first_row['Source Name']
                    )
                )
            ]
        )

        for row in csv_reader:
            debit = credit = Decimal('0')
            if Decimal(row['Amount']) > 0:
                credit = Decimal(row['Amount'])
            else:
                debit = abs(Decimal(row['Amount']))

            if row['Source Name']:
                move.lines.append(MoveLine(
                    account=self.get_quickbook_payroll_account(
                        row['Payroll Item']
                    ),
                    debit=debit,
                    credit=credit,
                    party=self.get_quickbook_source_name(
                        row['Source Name']
                    )
                ))
            else:
                # This is an effective balance line.
                move.lines.append(MoveLine(
                    account=self.start.credit_account,
                    debit=debit,
                    credit=credit,
                ))

        move.save()

        return action, {'res_id': [move.id]}
