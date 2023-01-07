def prettify_balance(amount: str, wallet: str, creditor: str = None) -> str:
    result = f'{amount}'
    if creditor:
        result += f'\n{creditor} ⬆️'
    return result

