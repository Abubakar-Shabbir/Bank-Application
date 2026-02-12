from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Account(models.Model):
    id = models.BigAutoField(primary_key=True)

    ACCOUNT_TYPES = [('Savings', 'Savings'), ('Current', 'Current')]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES)

    # 🔹 NEW FIELDS
    cnic = models.CharField(max_length=15, unique=True)
    date_of_birth = models.DateField()
    age = models.PositiveIntegerField()
    address = models.TextField()
    phone_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.user.username}'s {self.account_type} Account"


class Transaction(models.Model):
    TRANSACTION_TYPES = [('Deposit', 'Deposit'), ('Withdrawal', 'Withdrawal'), ('Transfer', 'Transfer')]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)

    def __str__(self):
        return f"{self.transaction_type} ${self.amount} - {self.account.user.username}"

class Loan(models.Model):
    SCHEMES = [('Personal', 'Personal'), ('Car', 'Car'), ('Education', 'Education')]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='loans')
    scheme = models.CharField(max_length=20, choices=SCHEMES)
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_remaining = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='Pending')
    applied_on = models.DateTimeField(auto_now_add=True)
    reviewed_on = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    pending_repayment = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.scheme} Loan - {self.account.user.username} - ${self.principal_amount}"

class MobileRecharge(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='mobile_recharges')
    phone_number = models.CharField(max_length=20)
    country_code = models.CharField(max_length=5)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('Success','Success'),('Failed','Failed')], default='Success')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone_number} - ${self.amount}"
