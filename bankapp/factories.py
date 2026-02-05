# bankapp/factories.py
from decimal import Decimal
from datetime import datetime
from .models import Loan

class LoanFactory:
    @staticmethod
    def create_loan(account, scheme_name, scheme_details):
        """
        Factory method to create a Loan object.
        """
        return Loan(
            account=account,
            scheme=scheme_name,
            principal_amount=Decimal(scheme_details["max_amount"]),
            status='Pending',
            balance_remaining=Decimal(scheme_details["max_amount"]),
            applied_on=datetime.now()
        )
