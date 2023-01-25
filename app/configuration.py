import json
from typing import List, Dict


class Configuration:

    def __init__(self, config_path: str, logger):
        with open(config_path) as f:
            data = json.load(f)
            self.token = data['token']

            # Initialize wallets
            self._wallets: List[Dict[str, str]] = data['wallets']
            currencies = [w['currency'] for w in self._wallets]
            if len(set(currencies)) < len(currencies):
                raise ValueError('Configuration error: the wallet must have unique currency names.')

            # Validate and initialize users
            self._users = data['users']
            if len(self._users) != 2:
                raise ValueError(f'Configuration error: number of configured users must be 2, while it is {len(self._users)}')
            self._user1 = data['users'][0]
            self._user2 = data['users'][1]
            if 'name' not in self._user1 or 'name' not in self._user2:
                raise ValueError(f'Configuration error: "name" not defined in at least one user.')
            if 'chat_id' not in self._user1 or 'chat_id' not in self._user2:
                raise ValueError(f'Configuration error: "chat_id" not defined in at least one user.')
            if self._user1['name'] == self._user2['name']:
                raise ValueError(f'Configuration error: usernames cannot be the same.')

            logger.info(f'Configured users: {self._user1["name"]} and {self._user2["name"]}')
            logger.info(f'Configured user IDs: {self._user2["chat_id"]} and {self._user2["chat_id"]}')

    def get_token(self) -> str:
        return self.token

    def get_usernames(self) -> List[str]:
        return [self._user1['name'], self._user2['name']]

    def get_other_username(self, username: str) -> str:
        if username == self._user1['name']:
            return self._user2['name']
        elif username == self._user2['name']:
            return self._user1['name']
        else:
            assert False, f'Unable to find other username of: {username}'

    def get_chat_ids(self) -> List[int]:
        return [int(self._user1['chat_id']), int(self._user2['chat_id'])]

    def get_chat_id(self, username) -> int:
        if username == self._user1['name']:
            return int(self._user1['chat_id'])
        elif username == self._user2['name']:
            return int(self._user2['chat_id'])
        else:
            assert False, f'Unable to find other username of: {username}'

    def get_other_chat_id(self, chat_id: int) -> str:
        if chat_id == int(self._user1['chat_id']):
            return self._user2['chat_id']
        elif chat_id == int(self._user2['chat_id']):
            return self._user1['chat_id']
        else:
            assert False, f'Unable to find other chat_id of: {chat_id}'

    def get_currencies(self) -> List[str]:
        return [w['currency'] for w in self._wallets]

    def get_symbol(self, currency: str) -> str:
        for w in self._wallets:
            if w['currency'] == currency:
                return w['symbol']
        raise ValueError(f'Unknown currency {currency}')
