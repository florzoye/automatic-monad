from web3 import Web3
from eth_account import Account
import requests
from loguru import logger
from sync_utils.sync_balance_native import SyncTokenBalanceChecker


class GasZipBuyMonad:
    def __init__(self, rpc, private_key):
        self.web3 = Web3(Web3.HTTPProvider(rpc))
        if not self.web3.is_connected():
            raise Exception("Не удалось подключиться к Ethereum ноде")
        self.private_key = private_key
        self.rpc = rpc
        self.account = Account.from_key(private_key)
        self.from_address = self.account.address
        self.checker = SyncTokenBalanceChecker(self.rpc, self.private_key)

    def get_eth_price(self):
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'ethereum',
            'vs_currencies': 'usd'
        }
        response = requests.get(url, params=params)
        data = response.json()
        return data['ethereum']['usd']

    def calculate_eth_for_dollars(self, dollars):
        eth_price = self.get_eth_price()
        return dollars / eth_price
    
    def input_data(self, value):

        headers = {
            'accept': '*/*',
            'accept-language': 'ru,en;q=0.9',
            'origin': 'https://www.gas.zip',
            'priority': 'u=1, i',
            'referer': 'https://www.gas.zip/',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "YaBrowser";v="25.2", "Yowser";v="2.5"',
        }

        params = {
            'from': self.from_address,
            'to': self.from_address,
        }

        response = requests.get(f'https://backend.gas.zip/v2/quotes/42161/{value}/10143', params=params, headers=headers)
        return response.json()

    def buy_monad_on_GasZip(self):
        to_address = "0x391E7C679d29bD940d63be94AD22A25d25b5A604"
        value_eth = self.calculate_eth_for_dollars(2)
        value_wei = self.web3.to_wei(value_eth, 'ether')
        nonce = self.web3.eth.get_transaction_count(self.from_address)
        i = self.input_data(value_wei)
        input_data = i['calldata']
        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': value_wei,
            'gas': 46896,
            'gasPrice': self.web3.to_wei(0.01, 'gwei'),
            'data': input_data,
            'chainId': self.web3.eth.chain_id
        }

        signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        balance = self.checker.get_mon_balance()
        logger.success(f'Success buy $MON | Balance {round(balance, 5)} | Wallet {self.from_address}')


