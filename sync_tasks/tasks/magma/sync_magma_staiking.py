import time
import random
from web3 import Web3
from sync_utils.sync_balance_native import SyncTokenBalanceChecker
from loguru import logger
from decimal import Decimal

class MAGMA:

    def __init__(self,
                  rpc_url: str,
                    private_key: str,
                      token_decimals: int = 18
        ):
        self.rpc_url = rpc_url
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.private_key = private_key
        self.wallet_address = self.web3.to_checksum_address(
            self.web3.eth.account.from_key(private_key).address
        )
        self.contract_address = self.web3.to_checksum_address("0x2c9C959516e9AAEdB2C748224a41249202ca8BE7")
        self.stake_function_selector = "0xd5575982"
        self.unstake_function_selector = "0x6fed1ea7"
        self.token_decimals = token_decimals
        self.balance_checker = SyncTokenBalanceChecker(self.rpc_url, self.private_key)

    def generate_value(self) -> float:
        return round(Decimal(self.balance_checker.get_mon_balance()) * Decimal(0.05), 5)

    def sync_magma_stake_mon(self):
        try:
            value_eth = self.generate_value()
            value = self.web3.to_wei(value_eth, "ether")
            gas_price_gwei = 62
            gas_price = self.web3.to_wei(gas_price_gwei, "gwei")
            nonce = self.web3.eth.get_transaction_count(self.wallet_address, "pending")
            chain_id = self.web3.eth.chain_id

            tx = {
                "chainId": chain_id,
                "nonce": nonce,
                "to": self.contract_address,
                "value": value,
                "gasPrice": gas_price,
                "data": self.stake_function_selector,
            }

            try:
                estimated_gas = self.web3.eth.estimate_gas(tx)
                gas_limit = int(estimated_gas * 1.2)  
            except Exception as e:
                gas_limit = 200000  

            tx["gas"] = gas_limit

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            balance_gMON = self.balance_checker.get_all_balances()
            balance_mon = self.balance_checker.get_mon_balance()
            
            logger.success(f"🔄 Succes MAGMA stake MON, amount: {round(value_eth, 6)} | Wallet {self.wallet_address} |" 
                        f" Balance MON/gMON - {balance_mon}/{balance_gMON['gMON']} ")
        except Exception as e:
              logger.error(f'Error MAGMA stake $MON {e} | Wallet {self.wallet_address}')

    
    def create_unstake_input_data(self, amount_tokens: float) -> str:
        amount_min_units = int(amount_tokens * (10 ** self.token_decimals))
        hex_amount = hex(amount_min_units)[2:].rjust(64, '0')
        return f"{self.unstake_function_selector}{hex_amount}"

    def sync_magma_unstake_gmon(self):
        try:
            gmon_address = "0xaEef2f6B429Cb59C9B2D7bB2141ADa993E8571c3"  
            balance = self.balance_checker.get_token_balance(gmon_address) * 0.95

            if balance == 0:
                print("⚠️ Balance gMON = 0 ")
                return None

            input_data = self.create_unstake_input_data(balance)
            nonce = self.web3.eth.get_transaction_count(self.wallet_address, "pending")
            gas_price_gwei = 50
            gas_limit = 200000

            tx = {
                "to": self.contract_address,
                "value": 0,
                "gas": gas_limit,
                "gasPrice": self.web3.to_wei(gas_price_gwei, "gwei"),
                "nonce": nonce,
                "data": input_data,
                "chainId": self.web3.eth.chain_id
            }

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            balance_gMON = self.balance_checker.get_all_balances()
            balance_mon = self.balance_checker.get_mon_balance()
            
            logger.success(f"🔄 Succes MAGMA unstake MON, amount: {balance} | Wallet {self.wallet_address} |" 
                        f" Balance MON/gMON - {balance_mon}/{balance_gMON['gMON']} ")
        except Exception as e:
              logger.error(f'Error MAGMA unstake $MON {e} | Wallet {self.wallet_address}')


