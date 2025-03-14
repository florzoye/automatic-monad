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

class MONORAIL:
    def __init__(self, private_key: str, rpc: str, proxy: str = None):
        self.private_key = private_key
        self.rpc = rpc
        self.proxy_str = proxy
        self.proxies = self.build_proxies(proxy)
        self.w3 = Web3(Web3.HTTPProvider(self.rpc))
        self.address = to_checksum_address(Account.from_key(private_key=self.private_key).address)
        self.value_to_approve = None
        self.balance_checker = SyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key)
        self.chog_address = "0xE0590015A873bF326bd645c3E1266d4db41C4E6B"

    @staticmethod
    def generate_random_value(max_value: float) -> float:
        limit = max_value * 0.1
        return round(random.uniform(0.0001, min(limit, max_value)), 6)
    
    @staticmethod
    def build_proxies(proxy_str: str) -> dict | None:
        if proxy_str:
            if not proxy_str.startswith("http://") and not proxy_str.startswith("socks5://"):
                proxy_url = f"http://{proxy_str}" 
            else:
                proxy_url = proxy_str  
            return {"http": proxy_url, "https": proxy_url}
        return None

    def approve_token(self,
                       amount_to_approve: float,
                       token_address: str
        ):
        self.value_to_approve = self.w3.to_wei(amount_to_approve, 'ether')
        contract_address = to_checksum_address(token_address)
        spender_address = to_checksum_address("0xc995498c22a012353fae7ecc701810d673e25794")

        abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]

        contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(self.address, 'pending')
        gas_price = max(self.w3.eth.gas_price, self.w3.to_wei(50, 'gwei'))

        transaction = contract.functions.approve(
            spender_address, self.value_to_approve
        ).build_transaction({
            "chainId": self.w3.eth.chain_id,
            "gasPrice": gas_price,
            "nonce": nonce,
            "gas": 80000,
            "value": 0,
        })

        try:
            signed_tx = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            txn_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = self.w3.to_hex(txn_hash)
        except Exception as e:
            logger.error(f"❌ Error at approve: {e}")


    def response(self,
                  from_token: str,
                     user_agent: str,
                        amount_to_swap,
                        to_token: str
        ):

        headers = {
            'accept': '*/*',
            'accept-language': 'ru,en;q=0.9',
            'origin': 'https://testnet-preview.monorail.xyz',
            'priority': 'u=1, i',
            'referer': 'https://testnet-preview.monorail.xyz/',
            'user-agent': user_agent,
        }

        params = {
            'amount': str(amount_to_swap),
            'from': from_token,
            'to': to_token,
            'slippage': '100',
            'deadline': '60',
            'source': 'fe2',
            'sender': self.address,
        }

        try:
            response = requests.get(
                'https://testnet-pathfinder-v2.monorail.xyz/v1/quote',
                params=params,
                headers=headers,
                proxies=self.proxies
            )
            
            return response.json()
        
        except Exception as e:
            logger.error(f"Error at respponse on buy {e}")


    @staticmethod
    def choice_token():
        tokens = {
            "CHOG": "0xE0590015A873bF326bd645c3E1266d4db41C4E6B",
            "YAKI": "0xfe140e1dCe99Be9F4F15d657CD9b7BF622270C50",
            "DAK":  "0x0F0BDEbF0F83cD1EE3974779Bcb7315f9808c714",
            "WMON": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",
        }

        name = random.choice(list(tokens.keys()))
        return name, tokens[name]


    def monorail_swap(self):

        ua = UserAgent()
        user_agent = ua.random

        from_token_name, from_token_address = self.choice_token()

        while True:
            to_token_name, to_token_address = self.choice_token()
            if to_token_name != from_token_name:
                break

        token_balance = self.balance_checker.get_token_balance(from_token_address)
        amount_to_swap = self.generate_random_value(token_balance)

        if token_balance <= 0.05 or self.balance_checker.get_mon_balance() <= 0.05:
            logger.error(f"❌ Not enough balance ${from_token_name} or $MON for swap")
            return

        self.approve_token(amount_to_swap, from_token_address)
        
        resp_json = self.response(
            from_token=from_token_address,
                user_agent=user_agent,
                    amount_to_swap=amount_to_swap,
                        to_token=to_token_address
        )
        transaction = resp_json['transaction']
        
        try:
            address_to = to_checksum_address('0xC995498c22a012353FAE7eCC701810D673E25794')
            value_int = int(transaction["value"], 16)
            gas_price = max(self.w3.eth.gas_price, self.w3.to_wei(50, 'gwei'))

            tx_params = {
                "chainId": self.w3.eth.chain_id,
                "nonce": self.w3.eth.get_transaction_count(self.address, 'latest'),
                "to": address_to,
                "data": transaction["data"],
                "value": value_int,
                "gasPrice": gas_price,
            }

            try:
                estimated_gas = self.w3.eth.estimate_gas(tx_params)
                gas_limit = int(estimated_gas * 1.2)  
            except Exception as e:
                gas_limit = 400000 

            tx_params["gas"] = gas_limit
            signed_tx = self.w3.eth.account.sign_transaction(tx_params, self.private_key)
            txn_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = self.w3.to_hex(txn_hash)

            balance = self.balance_checker.get_all_balances()
            mon_balance = self.balance_checker.get_mon_balance()

            logger.success(f"🔄 Success swap ${from_token_name} → ${to_token_name} in amount {amount_to_swap} {from_token_name} | Wallet {self.address} | "
                            f"Balance {to_token_name}/{from_token_name} - {round(balance[f"{to_token_name}"], 5)}/{round(balance[f"{from_token_name}"],5)}")
        except Exception as e:
            logger.error(f'Error Monorail swap {e} | Wallet {self.address}')

