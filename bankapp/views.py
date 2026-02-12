from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Account, Transaction
from .services import BankingFacade  # Import your Facade
from .services import SavingsInterest, CurrentInterest
from decimal import Decimal, InvalidOperation  # Add this import at the top
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Transaction, Account
from django.shortcuts import get_object_or_404
from decimal import Decimal, InvalidOperation
import random
from django.db import transaction
from django.contrib.auth.models import User # Ensure this is at the top
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Account, Loan
from .services import LoanFacade
from decimal import Decimal


@login_required
def transaction_receipt(request, transaction_id):
    # Ensure the transaction actually belongs to the logged-in user
    transaction = get_object_or_404(Transaction, id=transaction_id, account__user=request.user)
    return render(request, 'receipt.html', {'transaction': transaction})



@login_required
def transaction_history(request):
    try:
        account = Account.objects.get(user=request.user)
        # Fetch all transactions for this specific account
        transactions = Transaction.objects.filter(account=account).order_by('-timestamp')
        
        # Filtering logic
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            transactions = transactions.filter(timestamp__date__range=[start_date, end_date])
            
        return render(request, 'history.html', {
            'account': account, 
            'transactions': transactions
        })
    except Account.DoesNotExist:
        return redirect('signup')



from django.db import IntegrityError

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        acc_type = request.POST.get('account_type')
        cnic = request.POST.get('cnic')
        dob = request.POST.get('date_of_birth')
        age = request.POST.get('age')
        address = request.POST.get('address')
        phone = request.POST.get('phone')

        # 🔹 Check CNIC uniqueness
        if Account.objects.filter(cnic=cnic).exists():
            return render(request, 'signup.html', {'error': "CNIC already exists! You cannot create another account."})

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                acc_num = str(random.randint(10000000, 99999999))
                while Account.objects.filter(account_number=acc_num).exists():
                    acc_num = str(random.randint(10000000, 99999999))

                Account.objects.create(
                    user=user,
                    account_number=acc_num,
                    account_type=acc_type,
                    balance=Decimal('0.00'),
                    cnic=cnic,
                    date_of_birth=dob,
                    age=age,
                    address=address,
                    phone_number=phone
                )

            return redirect('login')

        except IntegrityError:
            return render(request, 'signup.html', {'error': "Username or Email already exists."})
        except Exception as e:
            return render(request, 'signup.html', {'error': f"Something went wrong: {str(e)}"})

    return render(request, 'signup.html')


@login_required
def dashboard(request):
    try:
        account = Account.objects.get(user=request.user)
        transactions = Transaction.objects.filter(account=account).order_by('-timestamp')

        # --- Monthly Balance Trend (last 6 months) ---
        from datetime import datetime, timedelta
        import json

        today = datetime.today()
        monthly_labels = []
        monthly_balance = []

        for i in range(5, -1, -1):  # last 6 months
            month = today - timedelta(days=i*30)
            label = month.strftime('%b %Y')
            monthly_labels.append(label)

            month_transactions = transactions.filter(
                timestamp__year=month.year,
                timestamp__month=month.month
            )
            month_balance = sum(t.amount for t in month_transactions) + account.balance
            monthly_balance.append(float(month_balance))

        # --- Transaction Type Summary ---
        transaction_types = ['Deposit', 'Withdrawal', 'Transfer', 'Mobile Recharge']
        type_data = []
        for t_type in transaction_types:
            if t_type == 'Deposit':
                amount = sum(t.amount for t in transactions if t.amount > 0)
            else:
                amount = sum(
                    -t.amount for t in transactions 
                    if t.transaction_type == t_type or (t_type=='Mobile Recharge' and 'Recharge' in t.description)
                )
            type_data.append(float(amount))

        context = {
            'account': account,
            'transactions': transactions,
            'monthly_labels': json.dumps(monthly_labels),
            'monthly_balance': json.dumps(monthly_balance),
            'transaction_types': json.dumps(transaction_types),
            'type_data': json.dumps(type_data),
        }

        return render(request, 'dashboard.html', context)

    except Account.DoesNotExist:
        return HttpResponse("No bank account found for this user.")

def deposit_view(request):
    account = Account.objects.get(user=request.user) # Use logged-in user
    if request.method == "POST":
        # Convert the string from the form into a Decimal, NOT a float
        amount = Decimal(request.POST.get('amount')) 
        BankingFacade.deposit(account.id, amount)
        return redirect('dashboard')
    return render(request, 'deposit.html', {'account': account})

def withdraw_view(request):
    account = Account.objects.get(user=request.user)
    message = ""
    if request.method == "POST":
        # Convert here as well
        amount = Decimal(request.POST.get('amount')) 
        success, result = BankingFacade.withdraw(account.id, amount)
        if success:
            return redirect('dashboard')
        message = result
    return render(request, 'withdraw.html', {'account': account, 'message': message})



# bankapp/views.py
@login_required
def transfer_view(request):
    # FIX: Get the account belonging ONLY to the logged-in user
    sender_account = Account.objects.get(user=request.user)
    message = ""

    if request.method == "POST":
        receiver_num = request.POST.get('receiver_account')
        
        # Ensure we use Decimal for precision as discussed before
        try:
            amount = Decimal(request.POST.get('amount'))
            
            # Call the Facade with the specific ID of the logged-in sender
            success, message = BankingFacade.transfer_funds(sender_account.id, receiver_num, amount)
            
            if success:
                return redirect('dashboard')
        except (InvalidOperation, ValueError):
            message = "Invalid amount entered."

    return render(request, 'transfer.html', {'account': sender_account, 'message': message})

# bankapp/views.py additions

from django.contrib import messages

@login_required
def apply_interest(request):
    account = Account.objects.get(user=request.user)
    
    if account.account_type == 'Savings':
        strategy = SavingsInterest()
        interest_amount = strategy.calculate(account.balance)
        
        if interest_amount > 0:
            BankingFacade.deposit(account.id, interest_amount, description="Monthly Interest Credit (5%)")
            messages.success(request, f"Interest of ${interest_amount} applied!")
    else:
        # This handles your specific requirement for Current Accounts
        messages.info(request, "Not applicable for current account")

    return redirect('dashboard')

@login_required
def profile_view(request):
    account = Account.objects.get(user=request.user)
    return render(request, 'profile.html', {'account': account})

@login_required
def print_statement(request):
    account = Account.objects.get(user=request.user)
    transactions = Transaction.objects.filter(account=account).order_by('-timestamp')
    
    # Optional: Keep the same date filtering logic from the history view
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        transactions = transactions.filter(timestamp__date__range=[start_date, end_date])
        
    return render(request, 'print_statement.html', {
        'account': account, 
        'transactions': transactions
    })

from decimal import Decimal
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Account, Loan
from .services import LoanFacade

from django.utils.safestring import mark_safe
import json

@login_required
def apply_loan_view(request):
    account = Account.objects.get(user=request.user)
    message = ""
    loan = None

    # Loan schemes with markup and return period
    loan_schemes = [
        {"name": "Personal", "max_amount": 5000, "interest_rate": 0.07, "return_days": 180},
        {"name": "Car", "max_amount": 20000, "interest_rate": 0.08, "return_days": 365},
        {"name": "Home", "max_amount": 100000, "interest_rate": 0.06, "return_days": 3650},
        {"name": "Education", "max_amount": 15000, "interest_rate": 0.05, "return_days": 730},
    ]

    # Convert to JSON string safely for template
    loan_schemes_json = mark_safe(json.dumps(loan_schemes))

    if request.method == "POST":
        scheme_name = request.POST.get("scheme")
        scheme_obj = next((s for s in loan_schemes if s["name"] == scheme_name), None)
        if scheme_obj:
            amount = scheme_obj["max_amount"]
            loan = LoanFacade.apply_loan(account.id, scheme_name)
            message = f"Loan '{scheme_name}' request for ${amount} submitted! Status: {loan.status}."
        else:
            message = "Invalid loan scheme selected."

    return render(request, "apply_loan.html", {
        "account": account,
        "message": message,
        "loan": loan,
        "loan_schemes": loan_schemes,
        "loan_schemes_json": loan_schemes_json,  # Pass JSON-safe version
    })


@login_required
def my_loans_view(request):
    account = Account.objects.get(user=request.user)
    loans = Loan.objects.filter(account=account).order_by('-applied_on')
    return render(request, 'my_loans.html', {
        'loans': loans,
        'account': account
    })



# bankapp/views.py

from .services import RechargeFacade
from django.contrib import messages

@login_required
def mobile_recharge_view(request):
    account = Account.objects.get(user=request.user)

    if request.method == "POST":
        phone = request.POST.get("phone")
        country_code = request.POST.get("country_code")
        amount = Decimal(request.POST.get("amount"))

        success, msg = RechargeFacade.process_recharge(
            account.id,
            phone,
            country_code,
            amount
        )

        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)

        return redirect("mobile_recharge")

    return render(request, "mobile_recharge.html", {
        "account": account
    })





