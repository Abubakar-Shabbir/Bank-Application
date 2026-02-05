from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_transaction_email(transaction):
    account = transaction.account
    user_email = account.user.email

    if not user_email:
        return False

    subject = f"Transaction Receipt - {transaction.description}"

    # HTML content
    html_content = render_to_string('transaction_email.html', {
        'transaction': transaction,
        'account': account,
    })

    # Plain text fallback
    text_content = f"""
    Transaction Receipt for {account.user.username}
    
    Account: {account.account_number} ({account.account_type})
    Transaction Type: {transaction.transaction_type}
    Description: {transaction.description}
    Amount: ${transaction.amount}
    Date: {transaction.timestamp}
    Remaining Balance: ${account.balance}
    """

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)

    return True

