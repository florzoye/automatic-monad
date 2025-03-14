import asyncio
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
import random
from async_utils.async_balance_native import AsyncTokenBalanceChecker
from loguru import logger
import gc
import aiohttp

class Kinza:

    FUNCTION_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "spender", "type": "address"},
                {"internalType": "uint256", "name": "value", "type": "uint256"}
            ],
            "name": "approve",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

    FUNCTION_SELECTOR = "0x617ba037"
    DAK_CONTRACT_ADDRESS = "0x0F0BDEbF0F83cD1EE3974779Bcb7315f9808c714"  
    SUPPLY_ADDRESS = AsyncWeb3.to_checksum_address("0x590B03D84441c1277f32784d1fbC22Fe18b1eEe0")
    APPROVE_CONTRACT = AsyncWeb3.to_checksum_address('0x0F0BDEbF0F83cD1EE3974779Bcb7315f9808c714')

    def __init__(self,
                  rpc_url: str,
                    private_key: str,
        ):
        self.web3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.rpc = rpc_url
        self.private_key = private_key
        self.wallet_address = self.web3.to_checksum_address(
            self.web3.eth.account.from_key(private_key).address
        )
        self.contract_supply = self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.SUPPLY_ADDRESS),
           
            abi=self.FUNCTION_ABI
        )
        self.contract_approve = self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.APPROVE_CONTRACT),
            abi=self.FUNCTION_ABI
        )
        self.checker = AsyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key)
        self.value = None
        self.contract_address = self.web3.to_checksum_address("0x590B03D84441c1277f32784d1fbC22Fe18b1eEe0")

    
    async def create_supply_input_data(self) -> str:
        balance = await AsyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key).get_all_balances()
        value_eth = balance['DAK'] * 0.05
        self.value = value_eth
        value_wei = int(value_eth * (10 ** 18))  
        value_hex = hex(value_wei)[2:].rjust(64, '0')  

        contract_hex = self.DAK_CONTRACT_ADDRESS.lower()[2:].rjust(64, '0')
        sender_hex = self.wallet_address.lower()[2:].rjust(64, '0')  
        padding = "0" * 64  

        input_data = f"{self.FUNCTION_SELECTOR}{contract_hex}{value_hex}{sender_hex}{padding}"
        return input_data, value_eth


    async def infinity_approve(self,
        ):
        spender: str = '0x590B03D84441c1277f32784d1fbC22Fe18b1eEe0'
        nonce = await self.web3.eth.get_transaction_count(self.wallet_address, "pending")
        gas_price = self.web3.to_wei(62, "gwei")
        gas_limit: int = 100000
        value: int = 115792089237316195423570985008687907853269984665640564039457584007913129639935
        chain_id = await self.web3.eth.chain_id

        tx = await self.contract_approve.functions.approve(
            AsyncWeb3.to_checksum_address(spender),
            value).build_transaction({
            "chainId": chain_id,
            "from": self.wallet_address,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": nonce
        })

        signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    async def create_withdraw_input_data(self,
                                   spender: str,
                                      amount: int
        ):
        function_selector = "0x69328dec" 
        spender_address = self.web3.to_checksum_address(spender)[2:].rjust(64, '0')
        amount_hex = hex(amount)[2:].rjust(64, '0')
        owner_address = self.wallet_address[2:].rjust(64, '0')
        return function_selector + spender_address + amount_hex + owner_address
    

    async def withdraw_liquidity(self):
        try:
            withdraw_spender: str = "0x0F0BDEbF0F83cD1EE3974779Bcb7315f9808c714"
            nonce = await self.web3.eth.get_transaction_count(self.wallet_address, "pending")
            amount_withdraw = 2**256 - 1 
            gas_price = await self.web3.eth.gas_price
            chain_id = await self.web3.eth.chain_id
            input_data = await self.create_withdraw_input_data(withdraw_spender, amount_withdraw)

            tx = {
                "chainId": chain_id,
                "from": self.wallet_address,
                "to": self.contract_address,
                "data": input_data,
                "gas": 300000,
                "gasPrice": gas_price,
                "nonce": nonce
            }
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            balance_dak = await self.checker.get_all_balances()
            balance_mon = await self.checker.get_mon_balance()
            
            logger.success(f"🔄 Succes Withdraw $DAK in KINZA | Wallet {self.wallet_address} |" 
                            f" Balance MON/DAK - {balance_mon}/{balance_dak['DAK']} ")
        except Exception as e:
              logger.error(f'Error Kinza withdraw liquidity {e} | Wallet {self.wallet_address}')


    async def Kinza_supply_DAK(self):
        
        input_data = await self.create_supply_input_data()
        nonce = await self.web3.eth.get_transaction_count(self.wallet_address, "pending")
        gas_price = self.web3.to_wei(52, "gwei")
        gas_limit: int = 300000
        chain_id = await self.web3.eth.chain_id

        tx = {
            "to": AsyncWeb3.to_checksum_address(self.SUPPLY_ADDRESS),
            "value": 0,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": nonce,
            "data": input_data,
            "chainId": chain_id
        }

        signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        ins = AsyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key)
        balance_dak = await ins.get_all_balances()
        balance_mon = await ins.get_mon_balance()
        
        logger.success(f"🔄 Succes suuply {self.value} $DAK | Wallet {self.wallet_address} |" 
                        f" Balance MON/DAK - {balance_mon}/{balance_dak['DAK']} ")


