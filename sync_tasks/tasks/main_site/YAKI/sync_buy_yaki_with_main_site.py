import time
import random
import json
import requests
from loguru import logger
from fake_useragent import UserAgent
from web3 import Web3
from eth_account import Account
from eth_utils import to_checksum_address
from sync_utils.sync_balance_native import SyncTokenBalanceChecker

class BUY_YAKI:
    def __init__(self, private_key: str, rpc: str, proxy: str = None):
        self.private_key = private_key
        self.rpc = rpc
        self.proxy_str = proxy
        self.proxies = self.build_proxies(proxy)
        self.w3 = Web3(Web3.HTTPProvider(self.rpc))
        self.address = to_checksum_address(Account.from_key(private_key=self.private_key).address)

    @staticmethod
    def build_proxies(proxy_str: str) -> dict | None:
        if proxy_str:
            if not proxy_str.startswith("http://") and not proxy_str.startswith("socks5://"):
                proxy_url = f"http://{proxy_str}"  
            else:
                proxy_url = proxy_str  
            return {"http": proxy_url, "https": proxy_url}
        return None

    @staticmethod
    def generate_random_blink_key() -> str:
        return "dk_" + ''.join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=20))

    @staticmethod
    def generate_random_value() -> float:
        return round(random.uniform(0.0001, 0.001), 6)

    @staticmethod
    def generate_random_user_agent() -> str:
        ua = UserAgent()
        return ua.random

    def sync_response_buy_yaki(self):
        random_value = self.generate_random_value()
        random_blink_key = self.generate_random_blink_key()
        random_user_agent = self.generate_random_user_agent()

        headers = {
            'accept': '*/*',
            'accept-language': 'ru,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://testnet.monad.xyz',
            'referer': 'https://testnet.monad.xyz/',
            'user-agent': random_user_agent,
            'x-blink-client-key': random_blink_key,
        }

        params = {
            'apiUrl': (
                f'https://uniswap.api.dial.to/swap/confirm?chain=monad-testnet'
                f'&inputCurrency=native&outputCurrency=0xfe140e1dCe99Be9F4F15d657CD9b7BF622270C50'
                f'&inputSymbol=MON&outputSymbol=YAKI&inputDecimals=18&outputDecimals=18&amount={random_value}'
                f'&_brf=2edc9314-361d-4dfd-a143-2fc97ee3f9e0&_bin=90f9b4e9-66e6-4fae-8f24-0ca27b280ea8'
            ),
        }

        json_data = {
            'account': self.address,
            'type': 'transaction'
        }

        try:
            response = requests.post(
                'https://api.dial.to/v1/blink',
                params=params,
                headers=headers,
                json=json_data,
                proxies=self.proxies
            )
            
            if response.status_code != 200:
                logger.error(f"❌ API Error {response.status_code}: {response.text}")
                return

            parsed = response.json()
            tx_lst = json.loads(parsed['transaction'])

            self.sign_and_send(tx_lst, random_value)

        except Exception as e:
            logger.error(f"❌ Error at response: {e}")

    def sign_and_send(self, tx_lst, amount):
        try:
            address_to = to_checksum_address(tx_lst["to"])
            value_int = int(tx_lst["value"], 16)
            gas_price_int = int(tx_lst["gasPrice"]["value"])
            nonce = self.w3.eth.get_transaction_count(self.address, 'pending')
            chain_id = self.w3.eth.chain_id

            tx_params = {
                "chainId": chain_id,
                "nonce": nonce,
                "to": address_to,
                "data": tx_lst["data"],
                "value": value_int,
                "gas": tx_lst["gas"],
                "gasPrice": gas_price_int,
            }

            signed_tx = self.w3.eth.account.sign_transaction(tx_params, self.private_key)
            txn_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = self.w3.to_hex(txn_hash)

            ins = SyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key)
            balance_yaki = ins.get_all_balances()
            balance_mon = ins.get_mon_balance()
            
            logger.success(f"🔄 Succes buy $YAKI in MAIN-SITE, {amount} MON | Wallet {self.address} |" 
                           f" Balance MON/YAKI - {balance_mon}/{balance_yaki['YAKI']} ")

        except Exception as e:
            logger.error(f"❌Error when signing the transaction: {e}| Wallet {self.address}")

