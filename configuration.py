import json
from typing import List, Dict


class Configuration:

    def __init__(self, config_path: str, logger):
        with open(config_path) as f:
            data = json.load(f)
            self.token = data['token']
            self.wallets: List[Dict[str, str]] = data['wallets']
            users = data['users']
            if len(users) != 2:
                raise ValueError(f'Number of configured users must be 2, while it is {len(users)}')
            self.username1 = data['users'][0]['name']
            self.username2 = data['users'][1]['name']
            self.user_id1 = int(data['users'][0]['user_chat_id'])
            self.user_id2 = int(data['users'][1]['user_chat_id'])
            logger.info(f'Configured users: {self.username1} and {self.username2}')
            logger.info(f'Configured user IDs: {self.user_id1} and {self.user_id2}')

    def get_token(self) -> str:
        return self.token

    def get_username1(self) -> str:
        return self.username1

    def get_username2(self) -> str:
        return self.username2

    def get_user_names(self) -> List[str]:
        return [self.username1, self.username2]

    def get_user_chat_ids(self) -> List[int]:
        return [self.user_id1, self.user_id2]

    def get_currencies(self) -> List[str]:
        return [w['currency'] for w in self.wallets]

    def get_symbol(self, currency: str) -> str:
        for w in self.wallets:
            if w['currency'] == currency:
                return w['symbol']
        raise ValueError(f'Unknown currency {currency}')
