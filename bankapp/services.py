# bankapp/services.py
from .models import Account, Transaction
from django.db import transaction
from decimal import Decimal
from .models import Account, Transaction, Loan,  MobileRecharge
from django.db import transaction
from decimal import Decimal
from datetime import datetime
from .utils import send_transaction_email
from .factories import LoanFactory  # Add this import at the top


# --- STRATEGY PATTERN ---
class InterestStrategy:
    def calculate(self, balance):
        pass

class SavingsInterest(InterestStrategy):
    def calculate(self, balance):
        # Use Decimal for the rate
        return balance * Decimal('0.05') # 5% Interest for Savings

# bankapp/services.py

class CurrentInterest(InterestStrategy):
    def calculate(self, balance):
        # Always returns zero for Current Accounts to satisfy math requirements
        return Decimal('0.00')

# --- FACADE PATTERN ---
# services.py (update deposit/withdraw/transfer)

from .utils import send_transaction_email

class BankingFacade:
    
    @staticmethod
    @transaction.atomic
    def deposit(account_id, amount, description="Deposit"):
        account = Account.objects.get(id=account_id)
        account.balance += amount
        account.save()
        
        txn = Transaction.objects.create(
            account=account, 
            amount=amount, 
            description=description,
            transaction_type="Deposit"
        )

        # Send email
        send_transaction_email(txn)

        return account

    @staticmethod
    @transaction.atomic
    def withdraw(account_id, amount, description="Withdrawal"):
        account = Account.objects.get(id=account_id)
        if account.balance >= amount:
            account.balance -= amount
            account.save()
            txn = Transaction.objects.create(
                account=account, 
                amount=-amount, 
                description=description,
                transaction_type="Withdrawal"
            )
            send_transaction_email(txn)
            return True, "Success"
        return False, "Insufficient funds"

    @staticmethod
    def transfer_funds(sender_id, receiver_acc_num, amount):
        with transaction.atomic():
            try:
                sender = Account.objects.get(id=sender_id)
                receiver = Account.objects.get(account_number=receiver_acc_num)
                
                if sender.balance >= amount:
                    sender.balance -= amount
                    receiver.balance += amount
                    sender.save()
                    receiver.save()

                    txn_sender = Transaction.objects.create(
                        account=sender, amount=-amount, 
                        transaction_type='Transfer', description=f"Sent to {receiver_acc_num}"
                    )
                    txn_receiver = Transaction.objects.create(
                        account=receiver, amount=amount, 
                        transaction_type='Transfer', description=f"Received from {sender.account_number}"
                    )

                    # Send emails to both
                    send_transaction_email(txn_sender)
                    send_transaction_email(txn_receiver)

                    return True, "Transfer Successful"
                return False, "Insufficient funds"
            except Account.DoesNotExist:
                return False, "Receiver account not found"
 
            



            #============
            # bankapp/services.py
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from .models import Account, Transaction, Loan
from .services import BankingFacade  # Use your deposit/withdraw logic

# -------------------------------
# STRATEGY PATTERN: Loan Evaluation
# -------------------------------
class LoanEvaluationStrategy:
    """Abstract strategy class for evaluating loan eligibility."""
    def evaluate(self, account, requested_amount):
        """Return True if loan can be approved, False otherwise"""
        raise NotImplementedError


class BasicHistoryEvaluation(LoanEvaluationStrategy):
    """Approve based on deposits in the last 6 months."""
    def evaluate(self, account, requested_amount):
        six_months_ago = datetime.now() - timedelta(days=180)
        last_6_months = Transaction.objects.filter(
            account=account,
            timestamp__gte=six_months_ago
        )
        total_deposits = sum(t.amount for t in last_6_months if t.amount > 0)
        avg_balance = account.balance

        # Approve if deposits + current balance >= 50% of requested amount
        return (total_deposits + avg_balance) >= (requested_amount / 2)


class HighBalanceEvaluation(LoanEvaluationStrategy):
    """Approve small loans automatically if the account balance is high."""
    def evaluate(self, account, requested_amount):
        return account.balance >= 1000 and requested_amount <= 5000


from .factories import LoanFactory  # Add this import at the top

class LoanFacade:
    
    # Predefined loan schemes
    LOAN_SCHEMES = {
        'Personal': {"max_amount": 5000, "interest_rate": 0.07, "return_days": 180},
        'Car': {"max_amount": 20000, "interest_rate": 0.08, "return_days": 365},
        'Home': {"max_amount": 100000, "interest_rate": 0.06, "return_days": 3650},  # 10 years
        'Education': {"max_amount": 15000, "interest_rate": 0.05, "return_days": 730},  # 2 years
    }
    
    @staticmethod
    @transaction.atomic
    def apply_loan(account_id, scheme_name):
        account = Account.objects.get(id=account_id)

        if scheme_name not in LoanFacade.LOAN_SCHEMES:
            raise ValueError(f"Invalid loan scheme: {scheme_name}")

        scheme = LoanFacade.LOAN_SCHEMES[scheme_name]

        # ---------- Use Factory instead of direct create ----------
        loan = LoanFactory.create_loan(account, scheme_name, scheme)
        loan.save()
        # ---------------------------------------------------------

        # --- Evaluate using existing strategies ---
        strategies = [BasicHistoryEvaluation(), HighBalanceEvaluation()]
        approved = any(s.evaluate(account, scheme["max_amount"]) for s in strategies)

        if approved:
            loan.status = 'Approved'
            loan.approved_amount = Decimal(scheme["max_amount"])
            loan.interest_rate = Decimal(scheme["interest_rate"])
            loan.balance_remaining = loan.approved_amount * (1 + loan.interest_rate)
            loan.remarks = "Approved automatically based on history and balance"
            loan.due_date = datetime.now() + timedelta(days=scheme["return_days"])

            BankingFacade.deposit(
                account_id,
                loan.approved_amount,
                description=f"{scheme_name} Loan Credit"
            )
        else:
            loan.status = 'Rejected'
            loan.approved_amount = Decimal('0.00')
            loan.interest_rate = Decimal('0.00')
            loan.balance_remaining = Decimal('0.00')
            loan.remarks = "Rejected due to insufficient history or balance"

        loan.reviewed_on = datetime.now()
        loan.save()
        return loan

    @staticmethod
    def get_pending_loans():
        """Return all pending loans for admin review (if admin implemented)."""
        return Loan.objects.filter(status='Pending').order_by('applied_on')

    @staticmethod
    def auto_repay_loans():
        """
        Check all approved loans:
        - Deduct repayment if account balance sufficient
        - If not enough, mark pending_repayment=True
        """
        loans = Loan.objects.filter(status='Approved', balance_remaining__gt=0)
        for loan in loans:
            account = loan.account
            repayment_amount = loan.balance_remaining
            if account.balance >= repayment_amount:
                # Deduct repayment
                BankingFacade.withdraw(
                    account.id,
                    repayment_amount,
                    description=f"Loan Repayment: {loan.scheme}"
                )
                loan.balance_remaining = Decimal('0.00')
                loan.status = 'Closed'
                loan.pending_repayment = False
            else:
                loan.pending_repayment = True
            loan.save()


class RechargeStrategy:
    def validate(self, account, amount):
        raise NotImplementedError


class DefaultRechargeStrategy(RechargeStrategy):
    def validate(self, account, amount):
        if amount <= 0:
            return False, "Invalid recharge amount"
        if account.balance < amount:
            return False, "Insufficient balance"
        return True, "Valid"



class RechargeFacade:

    @staticmethod
    @transaction.atomic
    def process_recharge(account_id, phone, country_code, amount):
        account = Account.objects.get(id=account_id)
        strategy = DefaultRechargeStrategy()
        is_valid, message = strategy.validate(account, amount)

        if not is_valid:
            return False, message

        account.balance -= amount
        account.save()

        txn = Transaction.objects.create(
            account=account,
            amount=-amount,
            description=f"Mobile Recharge ({country_code}) {phone}",
            transaction_type="Mobile Recharge"
        )

        # Recharge record
        MobileRecharge.objects.create(
            account=account,
            phone_number=phone,
            country_code=country_code,
            amount=amount
        )

        # Send email
        send_transaction_email(txn)

        return True, "Recharge Successful"
