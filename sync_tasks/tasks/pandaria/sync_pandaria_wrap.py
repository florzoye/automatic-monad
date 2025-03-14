import time
from web3 import Web3
from web3.providers import HTTPProvider
import random
from sync_utils.sync_balance_native import SyncTokenBalanceChecker
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

class Pandaria:
    
    def __init__(self, rpc_url: str, private_key: str):
        self.web3 = Web3(HTTPProvider(rpc_url))
        self.private_key = private_key
        self.wallet_address = self.web3.to_checksum_address(
            self.web3.eth.account.from_key(private_key).address
        )
        self.rpc = rpc_url
        self.contract_address = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
        self.contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.contract_address),
            abi=deposit_abi
        )
        self.checker = SyncTokenBalanceChecker(private_key=self.private_key, rpc_url=self.rpc)
    
    @staticmethod
    def generate_random_value(max_value: float) -> float:
        max_value = float(max_value)  #
        limit = max_value * 0.1
        return round(random.uniform(0.0001, min(limit, max_value)), 6)


    def sync_pandaria_deposit(self,
                                 gas_limit: int = 100000,
                                   gas_price_gwei: int = 62
        ):
        try:
            token_balance = self.checker.get_mon_balance()
            amount_to_swap = self.generate_random_value(token_balance)
            value = self.web3.to_wei(amount_to_swap, "ether")
            gas_price = self.web3.to_wei(gas_price_gwei, "gwei")
            nonce = self.web3.eth.get_transaction_count(self.wallet_address, "pending")
            chain_id = self.web3.eth.chain_id

            tx = self.contract.functions.deposit().build_transaction({
                "chainId": chain_id,
                "from": self.wallet_address,
                "value": value,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "nonce": nonce
            })

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            balance = self.checker.get_mon_balance()
            all_balance = self.checker.get_all_balances()
            logger.success(f'🔄 Success Pandaria Wrap | Balance MON/WMON - {balance}/{all_balance['WMON']} | WALLET {self.wallet_address}')
        except Exception as e:
            logger.error(f'Error on Pandaria {e} | Wallet {self.wallet_address}')
