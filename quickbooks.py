# -*- coding: utf-8 -*-
"""
    Quickbooks

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import ModelSQL, ModelView, fields

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
