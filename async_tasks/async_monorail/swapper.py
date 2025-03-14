import asyncio
import random
import json
import aiohttp
from loguru import logger
from fake_useragent import UserAgent
from web3 import AsyncWeb3
from eth_account import Account
from eth_utils import to_checksum_address

from async_utils.async_balance_native import AsyncTokenBalanceChecker




class MONORAIL:
    def __init__(self, private_key: str, rpc: str, proxy: str | None):
        self.private_key = private_key
        self.rpc = rpc
        self.proxy_str = proxy  
        
        self.proxy_url = self._build_proxy_url(self.proxy_str)
        
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(self.rpc))
        self.address = to_checksum_address(Account.from_key(private_key=self.private_key).address)
        self.value_to_approve = None
        self.balance_checker = AsyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key)

    @staticmethod
    def _build_proxy_url(proxy_str: str) -> str | None:
        if not proxy_str:
            return None
        
        if not (proxy_str.startswith("http://") or proxy_str.startswith("socks5://")):
            proxy_str = f"http://{proxy_str}"
        return proxy_str

    @staticmethod
    async def test_proxy(proxy_url: str):
        if not proxy_url:
            return
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://httpbin.org/ip", proxy=proxy_url, timeout=10) as resp:
                    text = await resp.text()
        except Exception as e:
            logger.error(f"Proxy is not valid: {e}")

    @staticmethod
    def generate_random_value(max_value: float) -> float:
        limit = max_value * 0.1
        return round(random.uniform(0.0001, min(limit, max_value)), 6)

    async def approve_token(self, amount_to_approve: float, token_address: str):
        try:
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
            nonce = await self.w3.eth.get_transaction_count(self.address, 'pending')
            gas_price = max(await self.w3.eth.gas_price, self.w3.to_wei(50, 'gwei'))

            transaction = await contract.functions.approve(
                spender_address, self.value_to_approve
            ).build_transaction({
                "chainId": await self.w3.eth.chain_id,
                "gasPrice": gas_price,
                "nonce": nonce,
                "gas": 80000,
                "value": 0,
            })

            signed_tx = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            txn_hash = await self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = self.w3.to_hex(txn_hash)

        except Exception as e:
            logger.error(f"❌ Error at approve: {e}")

    async def response(self, from_token: str, user_agent: str, amount_to_swap, to_token: str) -> dict | None:

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

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    'https://testnet-pathfinder-v2.monorail.xyz/v1/quote',
                    params=params,
                    headers=headers,
                    proxy=self.proxy_url, 
                    timeout=15
                ) as resp:

                    if resp.status != 200:
                        text = await resp.text()
                        return None  

                    result = await resp.json()
                    return result
                
            except Exception as e:
                logger.error(f"Error in response: {e}")

        return None

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

    async def monorail_swap(self):

        ua = UserAgent()
        user_agent = ua.random

        if self.proxy_url:
            await self.test_proxy(self.proxy_url)

        from_token_name, from_token_address = self.choice_token()
        to_token_name, to_token_address = self.choice_token()

        while to_token_name == from_token_name:
            to_token_name, to_token_address = self.choice_token()

        token_balance = await self.balance_checker.get_token_balance(from_token_address)
        amount_to_swap = self.generate_random_value(token_balance)
        mon_balance = await self.balance_checker.get_mon_balance()

        if token_balance <= 0.05 or mon_balance <= 0.05:
            logger.error(f"❌ There is not enough balance ${from_token_name} or $MON to swap. "
                         f"token_balance: {token_balance}, mon_balance: {mon_balance}")
            return

    
        await self.approve_token(amount_to_swap, from_token_address)

        resp_json = await self.response(
            from_token=from_token_address,
            user_agent=user_agent,
            amount_to_swap=amount_to_swap,
            to_token=to_token_address
        )

        if not resp_json:
            logger.error("❌ API is nothing (None). Stop swap.")
            return

        transaction_info = resp_json.get('transaction')

        try:
            address_to = to_checksum_address('0xC995498c22a012353FAE7eCC701810D673E25794')
            value_int = int(transaction_info["value"], 16)
            gas_price = max(await self.w3.eth.gas_price, self.w3.to_wei(50, 'gwei'))

            tx_params = {
                "chainId": await self.w3.eth.chain_id,
                "nonce": await self.w3.eth.get_transaction_count(self.address, 'latest'),
                "to": address_to,
                "data": transaction_info["data"],
                "value": value_int,
                "gasPrice": gas_price,
                "gas": 400000
            }

            signed_tx = self.w3.eth.account.sign_transaction(tx_params, self.private_key)
            txn_hash = await self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = self.w3.to_hex(txn_hash)

            balance = await self.balance_checker.get_all_balances()

            logger.success(
                f"🔄 Success swap {from_token_name} → {to_token_name} "
                f"({amount_to_swap} {from_token_name}), tx={tx_hash} | Wallet {self.address}\n"
                f"Balance {to_token_name}/{from_token_name} "
                f"- {round(balance[to_token_name], 5)}/{round(balance[from_token_name], 5)}"
            )

        except Exception as e:
            logger.error(f"Error swap Monorail: {e} | Wallet {self.address}")