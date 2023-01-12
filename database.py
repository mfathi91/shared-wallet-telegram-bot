import os
import sqlite3
from typing import Tuple, List
from datetime import datetime

from configuration import Configuration
from sqlite3 import Connection


class Database:

    def __init__(self, configuration: Configuration, database_path: str):
        self.configuration = configuration
        self.database_path = database_path
        self.initialize()

    def initialize(self):
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            try:
                result = cursor.execute('SELECT name FROM sqlite_master')
                if not result.fetchone():
                    # Create and initialize users table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS "users" (
                            "id"   INTEGER,
                            "name" TEXT NOT NULL,
                            PRIMARY KEY("id")
                        );
                    """)
                    for name in self.configuration.get_usernames():
                        cursor.execute(f'INSERT INTO users (name) VALUES ("{name}")')

                    # Create and initialize wallets table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS "wallets" (
                            "id"   INTEGER,
                            "wallet" TEXT NOT NULL,
                            PRIMARY KEY("id")
                        );
                    """)
                    for wallet in self.configuration.get_currencies():
                        cursor.execute(f'INSERT INTO wallets (wallet) VALUES ("{wallet}")')

                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS "payments" (
                            "id"        INTEGER,
                            "payer_id"  INTEGER,
                            "amount"    INTEGER NOT NULL,
                            "wallet_id" INTEGER,
                            "note"      TEXT NOT NULL,
                            "dt"        TEXT NOT NULL,
                            PRIMARY KEY("id"),
                            FOREIGN KEY("payer_id") REFERENCES users("id"),
                            FOREIGN KEY("wallet_id") REFERENCES wallets("id")
                        );
                    """)

                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS "balances" (
                            "id"        INTEGER,
                            "user_id"   INTEGER,
                            "balance"   INTEGER,
                            "wallet_id" INTEGER,
                            PRIMARY KEY("id"),
                            FOREIGN KEY("user_id") REFERENCES users("id"),
                            FOREIGN KEY("wallet_id") REFERENCES wallet("id")
                        );
                    """)

                    connection.commit()
            except Exception:
                os.remove(self.database_path)
                raise RuntimeError('Unable to create the database')
            finally:
                cursor.close()

    @staticmethod
    def __get_user_id(connection: Connection, username: str) -> int:
        cursor = connection.cursor()
        row = cursor.execute('SELECT id FROM users WHERE name = :un', {'un': username}).fetchone()
        if row:
            return row[0]
        else:
            raise ValueError(f'No user with username of "{username}" found')

    @staticmethod
    def __add_payment(connection: Connection, username: str, amount: float, wallet: str, note: str):
        cursor = connection.cursor()
        try:
            cursor.execute('INSERT INTO payments (payer_id, amount, wallet_id, note, dt) VALUES ( '
                           '(SELECT id FROM users WHERE name = :username),'
                           ':amount,'
                           '(SELECT id FROM wallets WHERE wallet = :wallet),'
                           ':note, '
                           ':dt)',
                           {'username': username, 'amount': amount, 'wallet': wallet, 'note': note, 'dt': datetime.now()})
        finally:
            cursor.close()

    @staticmethod
    def __increase_user_balance(connection: Connection, payer: str, amount: float, wallet: str):
        cursor = connection.cursor()
        try:
            # Get the user ID of the given username
            row = cursor.execute('SELECT id FROM users WHERE name = :un', {'un': payer}).fetchone()
            if not row:
                raise ValueError(f'No user with username of "{payer}" found')
            payer_user_id = row[0]

            # Get the existing balance for the wallet
            row = cursor.execute('SELECT balance, users.id AS user_id FROM balances '
                                 'JOIN users ON balances.user_id = users.id '
                                 'JOIN wallets ON balances.wallet_id = wallets.id '
                                 'WHERE wallets.wallet = :wallet', {'wallet': wallet}).fetchone()
            old_balance = row[0] if row else 0
            old_user_id = row[1] if row else payer_user_id

            # Compute new_user_id and new_balance
            if payer_user_id == old_user_id:
                new_user_id = old_user_id
                new_balance = old_balance + amount
            else:
                new_balance = old_balance - amount
                if new_balance < 0:
                    new_user_id = payer_user_id
                    new_balance = -new_balance
                else:
                    new_user_id = old_user_id

            # Persist in the database
            if row:
                cursor.execute('UPDATE balances SET user_id = :new_uid, balance = :new_bal '
                               'WHERE user_id = :old_uid AND wallet_id = (SELECT id FROM wallets WHERE wallet = :wallet)',
                               {'new_uid': new_user_id, 'new_bal': new_balance, 'old_uid': old_user_id,'wallet': wallet})
            else:
                cursor.execute('INSERT INTO balances (user_id, balance, wallet_id) VALUES ('
                               ':new_uid, '
                               ':new_bal, '
                               '(SELECT id FROM wallets WHERE wallet = :wallet))',
                               {'new_uid': new_user_id, 'new_bal': new_balance, 'wallet': wallet})
        finally:
            cursor.close()

    def write_transaction(self, username: str, amount: float, wallet: str, note: str):
        with sqlite3.connect(self.database_path) as connection:
            try:
                self.__add_payment(connection, username, amount, wallet, note)
                self.__increase_user_balance(connection, username, amount, wallet)
            except Exception:
                connection.rollback()
                raise RuntimeError(f'Unable to write the transaction to the database -> user: {username}, amount: {amount}, wallet: {wallet}, note: {note}')

    def get_balance(self, wallet: str) -> Tuple[str, str]:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            try:
                res = cursor.execute('SELECT users.name AS username, balance FROM balances '
                                     'JOIN users ON balances.user_id = users.id '
                                     'WHERE wallet_id = (SELECT id FROM wallets WHERE wallet = :wallet)', {'wallet': wallet}).fetchone()
                if res:
                    return str(round(res[1], 2)), res[0]
            finally:
                cursor.close()

    def get_payments(self, wallet: str = None) -> List[Tuple]:
        payments = []
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            try:

                if wallet:
                    rows = cursor.execute('SELECT users.name, amount, wallets.wallet, note, dt FROM payments '
                                          'JOIN users ON payments.payer_id = users.id '
                                          'JOIN wallets ON payments.wallet_id = wallets.id '
                                          'WHERE wallets.wallet = :wallet', {'wallet': wallet}).fetchall()
                else:
                    rows = cursor.execute('SELECT users.name, amount, wallets.wallet, note, dt FROM payments '
                                          'JOIN users ON payments.payer_id = users.id '
                                          'JOIN wallets ON payments.wallet_id = wallets.id').fetchall()
                if rows:
                    for row in rows:
                        payments.append((row[0], row[1], row[2], row[3], row[4]))
            finally:
                cursor.close()
        return payments
