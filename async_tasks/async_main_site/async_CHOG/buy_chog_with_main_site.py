import asyncio
import random
import json
import aiohttp
from loguru import logger
from fake_useragent import UserAgent
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from eth_account import Account
from eth_utils import to_checksum_address
from async_utils.async_balance_native import AsyncTokenBalanceChecker


class BUY_CHOG:
    def __init__(self,
                  private_key: str,
                    rpc: str,
                      proxy: str 
        ):
        self.private_key = private_key
        self.rpc = rpc
        self.proxy_str = proxy
        self.proxies = self.build_proxies(proxy)
        self.w3 = AsyncWeb3(AsyncHTTPProvider(self.rpc))
        self.address = to_checksum_address(Account.from_key(private_key=self.private_key).address)
        self.proxy_disabled = False



    @staticmethod
    def build_proxies(proxy_str: str) -> str | None:
        if proxy_str:
            if not proxy_str.startswith("http://") and not proxy_str.startswith("socks5://"):
                proxy_url = f"http://{proxy_str}"  
            else:
                proxy_url = proxy_str  
            return proxy_url
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


    async def response_buy_chog(self):
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
                f'https://uniswap.api.dial.to/swap/confirm?chain=monad-testnet&inputCurrency=native&outputCurrency=0xE0590015A873bF326bd645c3E1266d4db41C4E6B&inputSymbol=MON&outputSymbol=CHOG&inputDecimals=18&outputDecimals=18&amount={random_value}&_brf=0b32a5e3-0887-4295-a6e4-d799ea0e1d3a&_bin=ea413435-33cb-419f-a492-682929431f0e',
            ),
        }

        json_data = {
            'account': self.address,
            'type': 'transaction'
        }

        try:
            async with aiohttp.ClientSession() as session:
                    proxy = None if self.proxy_disabled else self.proxies
                    async with session.post('https://api.dial.to/v1/blink', params=params, headers=headers, json=json_data, proxy=proxy) as response:
                        if response.status == 200:
                            await asyncio.sleep(random.randint(5, 15))
                            parsed = await response.json()
                            tx_lst = json.loads(parsed['transaction'])
                            await self.sign_and_send(tx_lst, random_value)
                            await session.connector.close()
                            return
                        else:
                            logger.error(f"❌ API Error {response.status}: {await response.text()}")
                            return

        except Exception as e:
            logger.error(f"❌ Error in response: {e}")

    async def sign_and_send(self, tx_lst, amount):
        max_attempts = 3  
        for attempt in range(1, max_attempts + 1):
            try:
                address_to = to_checksum_address(tx_lst["to"])
                value_int = int(tx_lst["value"], 16)
                gas_price_int = int(tx_lst["gasPrice"]["value"])
                nonce = await self.w3.eth.get_transaction_count(self.address, 'pending')
                chain_id = await self.w3.eth.chain_id

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
                txn_hash = await self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                tx_hash = self.w3.to_hex(txn_hash)
                
                ins = AsyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key)
                balance_chog = await ins.get_all_balances()
                balance_mon = await ins.get_mon_balance()

                if balance_mon > 0:
                    logger.success(f"🔄 Success buy $CHOG, {amount} MON | Wallet {self.address} |"
                                   f" Balance MON/CHOG - {balance_mon}/{balance_chog['CHOG']} ")
                    return tx_hash

            except Exception as e:
                logger.error(f"❌ Error when send transaction: {e}")
                break  

        logger.error(f"🚨 The transaction could not be completed | Wallet {self.address} ")
    
    
