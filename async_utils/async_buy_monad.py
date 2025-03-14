import asyncio
import aiohttp
from web3 import AsyncWeb3
from eth_account import Account
from loguru import logger
from eth_utils import to_checksum_address

from async_utils.async_balance_native import AsyncTokenBalanceChecker

class AsyncGasZipBuyMonad:
    def __init__(self, rpc: str, private_key: str):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc))
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.from_address = to_checksum_address(self.account.address)
        self.checker = AsyncTokenBalanceChecker(rpc_url=rpc, private_key=private_key)

    async def get_eth_price(self) -> float:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'ethereum',
            'vs_currencies': 'usd'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Error at receipt ETH/USD, статус {resp.status}")
                    return 0.0
                data = await resp.json()
                return data['ethereum']['usd']

    async def calculate_eth_for_dollars(self, dollars: float) -> float:
        eth_price = await self.get_eth_price()
        return dollars / eth_price if eth_price else 0.0

    async def input_data(self, value_wei: int) -> str:
        url = f'https://backend.gas.zip/v2/quotes/42161/{value_wei}/10143'
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

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"Error at receipt quotes GasZip, status {resp.status}")
                    return ""
                data = await resp.json()
                return data.get('calldata', "")

    async def buy_monad_on_GasZip(self, dollars: float = 2):
        to_address = to_checksum_address("0x391E7C679d29bD940d63be94AD22A25d25b5A604")

        value_eth = await self.calculate_eth_for_dollars(dollars)
        value_wei = self.w3.to_wei(value_eth, 'ether')

        nonce = await self.w3.eth.get_transaction_count(self.from_address)

        input_data = await self.input_data(value_wei)

        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': value_wei,
            'gas': 47000,
            'gasPrice': self.w3.to_wei(0.01, 'gwei'),
            'data': input_data,
            'chainId': await self.w3.eth.chain_id
        }

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        try:
            tx_hash_bytes = await self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_hex = self.w3.to_hex(tx_hash_bytes)
        except Exception as e:
            logger.error(f"Error at response GasZip: {e}")
            return

        balance = await self.checker.get_mon_balance()  
        logger.success(
            f"Success buy $MON for ~${dollars} | TxHash {tx_hash_hex} | "
            f"Balance MON: {round(balance,5)} | Wallet {self.from_address}"
        )


