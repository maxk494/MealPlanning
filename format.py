from decimal import Decimal

def format_amount(amount):
    if isinstance(amount, (int, float)):
        if amount % 1 == 0:  # Check if it's a whole number
            return str(int(amount))
        return f"{amount:.1f}"  # Return with one decimal place
    elif isinstance(amount, Decimal):
        if amount == amount.to_integral_value():
            return str(int(amount))
        return str(amount)
    return str(amount)