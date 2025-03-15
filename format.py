def format_amount(value):
    if value.is_integer():
        return f"{int(value)}"  # Return as integer if whole number
    else:
        return f"{value:.1f}"  # Return with one decimal place
