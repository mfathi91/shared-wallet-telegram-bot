import json
from typing import List, Dict


class Configuration:

    def __init__(self, config_path: str, logger):
        with open(config_path) as f:
            data = json.load(f)
            self.token = data['token']

            # Initialize wallets
            self.wallets: List[Dict[str, str]] = data['wallets']
            currencies = [w['currency'] for w in self.wallets]
            if len(set(currencies)) < len(currencies):
                raise ValueError('Configuration error: the wallet must have unique currency names.')

            # Initialize users
            self.users = data['users']
            if len(self.users) != 2:
                raise ValueError(f'Configuration error: umber of configured users must be 2, while it is {len(self.users)}')
            self.username1 = data['users'][0]['name']
            self.username2 = data['users'][1]['name']
            if self.username1 == self.username2:
                raise ValueError(f'Configuration error: usernames cannot be the same.')
            self.chat_id1 = int(data['users'][0]['chat_id'])
            self.chat_id2 = int(data['users'][1]['chat_id'])

            logger.info(f'Configured users: {self.username1} and {self.username2}')
            logger.info(f'Configured user IDs: {self.chat_id1} and {self.chat_id2}')

    def get_token(self) -> str:
        return self.token

    def get_username1(self) -> str:
        return self.username1

    def get_username2(self) -> str:
        return self.username2

    def get_usernames(self) -> List[str]:
        return [self.username1, self.username2]

    def get_chat_ids(self) -> List[int]:
        return [self.chat_id1, self.chat_id2]

    def get_chat_id(self, username) -> int:
        for user in self.users:
            if user['name'] == username:
                return user['chat_id']
        raise ValueError(f'Unable to find chat ID of user {username}')

    def get_currencies(self) -> List[str]:
        return [w['currency'] for w in self.wallets]

    def get_symbol(self, currency: str) -> str:
        for w in self.wallets:
            if w['currency'] == currency:
                return w['symbol']
        raise ValueError(f'Unknown currency {currency}')
