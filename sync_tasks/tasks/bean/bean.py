from web3 import Web3
import time
from eth_account import Account
import random
from sync_utils.sync_balance_native import SyncTokenBalanceChecker
from loguru import logger
from decimal import Decimal

class BeanExchange:

    UNISWAP_ROUTER_ADDRESS = Web3.to_checksum_address("0xCa810D095e90Daae6e867c19DF6D9A8C56db2c89")  # Адрес UniswapV2Router
    WMON_ADDRESS = Web3.to_checksum_address("0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701")  # Адрес WMON
    BEAN_ADDRESS = Web3.to_checksum_address("0x268E4E24E0051EC27b3D27A95977E71cE6875a05")  # Адрес BEAN
    SWAP_SELECTOR = "0x7ff36ab5"  
    APPROVE_SELECTOR = "0x095ea7b3" 
    UNLIMITED_APPROVE_AMOUNT = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    DELEGATE_SELECTOR = "0xf305d719"
    bean_to_mon_rate = Decimal("0.083488") 

    def __init__(self,
                  rpc_url: str,
                    private_key: str
        ):
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.rpc = rpc_url
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.wallet_address = self.account.address
        self.contract = self.web3.eth.contract(address=self.UNISWAP_ROUTER_ADDRESS, abi=[])
        self.checker = SyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key)
        self.deadline = int(time.time()) + 600

    
    def generate_value(self) -> float:
        return round(Decimal(self.checker.get_mon_balance()) * Decimal(0.05), 5)


    def swap_mon_to_bean(self):
        try:
            deadline_seconds: int = 300
            amount = self.generate_value()
            amount_in_wei = Web3.to_wei(amount, 'ether')  
            min_amount_out_wei = int(amount_in_wei * 0.99) 
            deadline = int(time.time()) + deadline_seconds  
            path = [self.WMON_ADDRESS, self.BEAN_ADDRESS]  

            input_data = (
                self.SWAP_SELECTOR + 
                hex(min_amount_out_wei)[2:].rjust(64, '0') +  
                hex(128)[2:].rjust(64, '0') +  
                self.wallet_address[2:].rjust(64, '0') +  
                hex(deadline)[2:].rjust(64, '0') +  
                hex(len(path))[2:].rjust(64, '0') +  
                ''.join([token[2:].rjust(64, '0') for token in path])
            )

            tx = {
                "from": self.wallet_address,
                "to": self.UNISWAP_ROUTER_ADDRESS,
                "value": amount_in_wei,
                "gasPrice": self.web3.eth.gas_price,
                "nonce": self.web3.eth.get_transaction_count(self.wallet_address),
                "data": input_data
            }

            try:
                estimated_gas = self.web3.eth.estimate_gas(tx)
                gas_limit = int(estimated_gas * 1.2)  
            except Exception as e:
                gas_limit = 300000  

            tx["gas"] = gas_limit

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

            balance_chog = self.checker.get_all_balances()
            balance_mon = self.checker.get_mon_balance()
        
            logger.success(f"🔄 Succes swap $BEAN, {amount} MON | Wallet {self.wallet_address} |" 
                            f" Balance MON/BEAN - {round(balance_mon, 5)}/{round(balance_chog['BEAN'], 5)} ")
        except Exception as e:
              logger.error(f'Error in swap $MON to $BEAN {e} | Wallet {self.wallet_address}')

    def approve_bean(self):
        try:
            input_data = (
                self.APPROVE_SELECTOR +
                self.UNISWAP_ROUTER_ADDRESS[2:].rjust(64, '0') +  
                self.UNLIMITED_APPROVE_AMOUNT  
            )

            tx = {
                "from": self.wallet_address,
                "to": self.BEAN_ADDRESS,
                "gasPrice": self.web3.eth.gas_price,
                "nonce": self.web3.eth.get_transaction_count(self.wallet_address),
                "data": input_data
            }

            try:
                estimated_gas = self.web3.eth.estimate_gas(tx)
                gas_limit = int(estimated_gas * 1.2)  
            except Exception as e:
                gas_limit = 100000 

            tx["gas"] = gas_limit
        
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        except Exception as e:
              logger.error(f'Error in approve Bean {e} | Wallet {self.wallet_address}')

    def bean_add_liquidity(self):
        try:
            balances = self.checker.get_all_balances()
            eth_balance = Web3.from_wei(self.web3.eth.get_balance(self.wallet_address), 'ether')

            if "BEAN" not in balances or balances["BEAN"] == 0:
                raise ValueError(f"❌ Error: in wallet not BEAN! | Wallet {self.wallet_address}")

            if eth_balance < Decimal("0.01"):
                raise ValueError(f"❌ Error: in wallet not MON! | Wallet {self.wallet_address}")

            self.amount_token = Decimal(balances["BEAN"]) * Decimal("0.9")
            self.amount_token_wei = Web3.to_wei(self.amount_token, 'ether')

            self.amount_eth = self.amount_token * self.bean_to_mon_rate
            self.amount_eth_wei = Web3.to_wei(self.amount_eth, 'ether')

            self.min_token = Web3.to_wei(self.amount_token * Decimal(random.uniform(0.9, 0.98)), 'ether')
            self.min_eth = Web3.to_wei(self.amount_eth * Decimal(random.uniform(0.9, 0.98)), 'ether')

            input_data = (
                self.DELEGATE_SELECTOR +
                self.BEAN_ADDRESS[2:].rjust(64, '0') +
                hex(self.amount_token_wei)[2:].rjust(64, '0') +
                hex(self.min_token)[2:].rjust(64, '0') +
                hex(self.min_eth)[2:].rjust(64, '0') +
                self.wallet_address[2:].rjust(64, '0') +
                hex(self.deadline)[2:].rjust(64, '0')
            )

            tx = {
                "from": self.wallet_address,
                "to": self.UNISWAP_ROUTER_ADDRESS,
                "value": self.amount_eth_wei,
                "gasPrice": self.web3.eth.gas_price,
                "nonce": self.web3.eth.get_transaction_count(self.wallet_address),
                "data": input_data,
            }

            try:
                estimated_gas = self.web3.eth.estimate_gas(tx)
                gas_limit = int(estimated_gas * 1.2)  
            except Exception as e:
                gas_limit = 300000 

            tx["gas"] = gas_limit

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

            logger.success(f"🔄 Balance BEAN/MON: {round(balances['BEAN'], 5)}/{round(eth_balance, 5)} | Used BEAN/MON: {round(self.amount_token, 6)}/{round(self.amount_eth, 6)} | Wallet {self.wallet_address} ")
        except Exception as e:
              logger.error(f'Error Bean add liquidity {e} | Wallet {self.wallet_address}')


