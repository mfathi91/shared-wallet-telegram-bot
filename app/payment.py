import json
from typing import NamedTuple


class Payment(NamedTuple):
    payer: str
    amount: str
    wallet: str
    wallet_symbol: str
    note: str

    def format(self) -> str:
        return f'Payer: {self.payer}\n' \
               f'Amount: {self.amount} {self.wallet_symbol}\n' \
               f'Wallet: {self.wallet}\n' \
               f'Note: {self.note}\n'

    def jsonify(self):
        return json.dumps({'payer': self.payer, 'wallet': self.wallet, 'amount': self.amount, 'note': self.note})

    def __repr__(self):
        return f'Payment ({self.payer!r}, {self.amount!r}, {self.wallet!r}, {self.wallet_symbol!r}, {self.note!r})'


class PersistedPayment(Payment):
    date: str

    def format(self) -> str:
        return f'{self.format()}Date: {self.date}\n'
