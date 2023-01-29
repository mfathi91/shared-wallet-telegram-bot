import logging
import tempfile
import unittest
from json import JSONDecodeError

from app import Configuration, ConfigurationError


class TestConfiguration(unittest.TestCase):

    VALID_CFG_JSON = '{"token": "my_bot_token",' \
                     '"wallets": [{"currency": "Dollar", "symbol": "$"}, {"currency": "Toman", "symbol": "T"}],' \
                     '"users": [{"name": "Julia", "chat_id": 1234}, {"name": "Jack", "chat_id": 4321}]}'

    # --------------__init__--------------
    def test_init(self):
        # Should fail because the JSON is invalid
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write('{"token": "foo",'
                           'wallets": : "Dollar", "symbol": "$"}],'
                           '"users": [": 1234}, {"name": "Jack", "chat_id": 4321}]}')
            cfg_json.flush()
            with self.assertRaises(JSONDecodeError):
                Configuration(cfg_json.name, logging)

    def test_init2(self):
        # Should fail because no wallets is configured
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write('{"token": "foo",'
                           '"users": [{"name": "Julia", "chat_id": 1234}, {"name": "Jack", "chat_id": 4321}]}')
            cfg_json.flush()
            with self.assertRaises(KeyError):
                Configuration(cfg_json.name, logging)

    def test_init3(self):
        # Should fail because no users is configured
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write('{"token": "foo",'
                           '"wallets": [{"currency": "Dollar", "symbol": "$"}]}')
            cfg_json.flush()
            with self.assertRaises(KeyError):
                Configuration(cfg_json.name, logging)

    def test_init4(self):
        # Should fail because of similar currency names
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write('{"token": "foo",'
                           '"wallets": [{"currency": "Dollar", "symbol": "$"}, {"currency": "Dollar", "symbol": "T"}],'
                           '"users": [{"name": "Julia", "chat_id": 1234}, {"name": "Jack", "chat_id": 4321}]}')
            cfg_json.flush()
            with self.assertRaises(ConfigurationError, msg='Configuration error: the wallet must have unique currency names.'):
                Configuration(cfg_json.name, logging)

    def test_init5(self):
        # Should fail because number of configured users is not 2
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write('{"token": "foo",'
                           '"wallets": [{"currency": "Dollar", "symbol": "$"}],'
                           '"users": [{"name": "Julia", "chat_id": 1234}]}')
            cfg_json.flush()
            with self.assertRaises(ConfigurationError, msg='Configuration error: number of configured users must be 2, while it is 1'):
                Configuration(cfg_json.name, logging)

    def test_init6(self):
        # Should create the new instance successfully
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            Configuration(cfg_json.name, logging)

    # --------------get_token()--------------
    def test_get_token(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            self.assertEqual('my_bot_token', Configuration(cfg_json.name, logging).get_token())

    # --------------get_usernames()--------------
    def test_get_usernames(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            self.assertEqual(['Julia', 'Jack'], Configuration(cfg_json.name, logging).get_usernames())

    # --------------get_other_username()--------------
    def test_get_other_username(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            config = Configuration(cfg_json.name, logging)
            self.assertEqual('Julia', config.get_other_username('Jack'))
            self.assertEqual('Jack', config.get_other_username('Julia'))

    def test_get_other_username2(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            non_existing_username = 'Non_Existing_User'
            with self.assertRaises(ValueError, msg=f'Unable to find other username of: {non_existing_username}'):
                Configuration(cfg_json.name, logging).get_other_username(non_existing_username)

    # --------------get_chat_ids()--------------
    def test_get_chat_ids(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            self.assertEqual([1234, 4321], Configuration(cfg_json.name, logging).get_chat_ids())

    # --------------get_chat_id()--------------
    def test_get_chat_id(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            self.assertEqual(1234, Configuration(cfg_json.name, logging).get_chat_id('Julia'))
            self.assertEqual(4321, Configuration(cfg_json.name, logging).get_chat_id('Jack'))

    def test_get_chat_id2(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            non_existing_username = 'Non_Existing_User'
            with self.assertRaises(ValueError, msg=f'Unable to find other username of: {non_existing_username}'):
                Configuration(cfg_json.name, logging).get_chat_id(non_existing_username)

    # --------------get_other_chat_id()--------------
    def test_get_other_chat_id(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            self.assertEqual(4321, Configuration(cfg_json.name, logging).get_other_chat_id(1234))
            self.assertEqual(1234, Configuration(cfg_json.name, logging).get_other_chat_id(4321))

    def test_get_other_chat_id2(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            non_existing_chat_id = 8765
            with self.assertRaises(ValueError, msg=f'Unable to find other chat_id of: {non_existing_chat_id}'):
                Configuration(cfg_json.name, logging).get_other_chat_id(non_existing_chat_id)

    # --------------get_currencies()--------------
    def test_get_currencies(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            self.assertEqual(['Dollar', 'Toman'], Configuration(cfg_json.name, logging).get_currencies())

    # --------------get_wallet_symbol()--------------
    def test_get_wallet_symbol(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            self.assertEqual('$', Configuration(cfg_json.name, logging).get_wallet_symbol('Dollar'))
            self.assertEqual('T', Configuration(cfg_json.name, logging).get_wallet_symbol('Toman'))

    def test_get_wallet_symbol2(self):
        with tempfile.NamedTemporaryFile('w') as cfg_json:
            cfg_json.write(TestConfiguration.VALID_CFG_JSON)
            cfg_json.flush()
            non_existing_currency = 'NonExistingCurrency'
            with self.assertRaises(ValueError, msg=f'Unknown currency {non_existing_currency}'):
                Configuration(cfg_json.name, logging).get_wallet_symbol(non_existing_currency)
