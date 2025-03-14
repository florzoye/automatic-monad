import asyncio
import random
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from async_utils.async_balance_native import AsyncTokenBalanceChecker
from loguru import logger

class MAGMA:

    def __init__(self,
                  rpc_url: str,
                    private_key: str,
                      token_decimals: int = 18
        ):
        self.rpc_url = rpc_url
        self.web3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.private_key = private_key
        self.wallet_address = self.web3.to_checksum_address(
            self.web3.eth.account.from_key(private_key).address
        )
        self.contract_address = self.web3.to_checksum_address("0x2c9C959516e9AAEdB2C748224a41249202ca8BE7")
        self.stake_function_selector = "0xd5575982"
        self.unstake_function_selector = "0x6fed1ea7"
        self.token_decimals = token_decimals

        self.balance_checker = AsyncTokenBalanceChecker(self.rpc_url, self.private_key)


    async def magma_stake_mon(self):
        value_eth = round(random.uniform(0.001, 0.005), 4)  

        value = self.web3.to_wei(value_eth, "ether")
        gas_limit = 200000
        gas_price_gwei: int = 62
        gas_price = self.web3.to_wei(gas_price_gwei, "gwei")
        nonce = await self.web3.eth.get_transaction_count(self.wallet_address, "pending")
        chain_id = await self.web3.eth.chain_id

        tx = {
            "chainId": chain_id,
            "nonce": nonce,
            "to": self.contract_address,
            "value": value,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "data": self.stake_function_selector,
        }

        signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        ins = AsyncTokenBalanceChecker(rpc_url=self.rpc_url, private_key=self.private_key)
        balance_gMON = await ins.get_all_balances()
        balance_mon = await ins.get_mon_balance()
        
        logger.success(f" Wallet {self.wallet_address} |" 
                       f" Balance MON/gMON - {balance_mon}/{balance_gMON['gMON']} ")
    
    


    def create_unstake_input_data(self, 
                                  amount_tokens: float) -> str:
        amount_min_units = int(amount_tokens * (10 ** self.token_decimals))
        hex_amount = hex(amount_min_units)[2:].rjust(64, '0')
        return f"{self.unstake_function_selector}{hex_amount}"


    async def magma_unstake_gmon(self):
        gmon_address = "0xaEef2f6B429Cb59C9B2D7bB2141ADa993E8571c3"  
        balance = await self.balance_checker.get_token_balance(gmon_address) * 0.95

        if balance == 0:
            print("⚠️ Balance gMON = 0 ")
            return None

        input_data = self.create_unstake_input_data(balance)
        nonce = await self.web3.eth.get_transaction_count(self.wallet_address, "pending")
        gas_price_gwei: int = 50
        gas_limit: int = 200000

        tx = {
            "to": self.contract_address,
            "value": 0,
            "gas": gas_limit,
            "gasPrice": self.web3.to_wei(gas_price_gwei, "gwei"),
            "nonce": nonce,
            "data": input_data,
            "chainId": await self.web3.eth.chain_id
        }

        signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        ins = AsyncTokenBalanceChecker(rpc_url=self.rpc_url, private_key=self.private_key)
        balance_gMON = await ins.get_all_balances()
        balance_mon = await ins.get_mon_balance()
        
        logger.success(f" Wallet {self.wallet_address} |" 
                       f" Balance MON/gMON - {balance_mon}/{balance_gMON['gMON']} ")
    

