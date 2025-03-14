import asyncio
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from async_utils.async_balance_native import AsyncTokenBalanceChecker
import random
from loguru import logger


deposit_abi = [
    {
        "inputs": [],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

class DepositContract:
    
    def __init__(self,
                  rpc_url: str,
                    private_key: str
        ):
        self.web3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.private_key = private_key
        self.wallet_address = self.web3.to_checksum_address(
            self.web3.eth.account.from_key(private_key).address
        )
        self.contract_address = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
        self.contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.contract_address),
            abi=deposit_abi
        )
    
    @staticmethod
    def generate_random_value() -> float:
        return round(random.uniform(0.0001, 0.001), 6)

    async def pandaria_wrap(self):
       try:
            gas_limit: int = 100000
            gas_price_gwei: int = 62
            value_eth = self.generate_random_value()
            value = self.web3.to_wei(value_eth, "ether")
            gas_price = self.web3.to_wei(gas_price_gwei, "gwei")
            nonce = await self.web3.eth.get_transaction_count(self.wallet_address, "pending")
            chain_id = await self.web3.eth.chain_id

            
            tx = await self.contract.functions.deposit().build_transaction({
                "chainId": chain_id,
                "from": self.wallet_address,
                "value": value,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "nonce": nonce
            })


            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)

            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logger.success(f'Success Pandaria Wrap | Wallet {self.wallet_address}')
       except Exception as e:
            logger.error(f'Error in Pandaria Wrap | Wallet {self.wallet_address} | {e}')
