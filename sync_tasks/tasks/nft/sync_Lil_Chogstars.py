import time
from web3 import Web3
from web3.providers import HTTPProvider
from loguru import logger
from sync_utils.sync_balance_native import SyncTokenBalanceChecker


class NFTMinter:
    FUNCTION_ABI = [
        {
            "inputs": [
                {"internalType": "uint256",
                "name": "quantity",
                "type": "uint256"
                }
            ],
            "name": "mint",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function"
        }
    ]

    def __init__(self, rpc_url: str, private_key: str):
        self.web3 = Web3(HTTPProvider(rpc_url))
        self.private_key = private_key
        self.contract_address = "0xb33D7138c53e516871977094B249C8f2ab89a4F4"
        self.wallet_address = self.web3.to_checksum_address(
            self.web3.eth.account.from_key(private_key).address
        )
        self.contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.contract_address),
            abi=self.FUNCTION_ABI
        )
        self.rpc = rpc_url
        self.checker = SyncTokenBalanceChecker(rpc_url=self.rpc, private_key=self.private_key)

    def sync_mint_chogstars(self):
        try: 
            quantity: int = 1
            gas_limit: int = 200000
            gas_price_gwei: int = 62
            nonce = self.web3.eth.get_transaction_count(self.wallet_address, "pending")
            gas_price = self.web3.to_wei(gas_price_gwei, "gwei")
            chain_id = self.web3.eth.chain_id
            mint_price_eth: float = 0.0
            mint_value = self.web3.to_wei(mint_price_eth, "ether")  

            tx = self.contract.functions.mint(quantity).build_transaction({
                "chainId": chain_id,
                "from": self.wallet_address,
                "value": mint_value,  
                "gas": gas_limit,
                "gasPrice": gas_price,
                "nonce": nonce
            })

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            balance = self.checker.get_mon_balance()
            logger.success(f'Success mint LilChogstars in quantity - 1 | Balance MON - {round(balance, 5)} |  WALLET {self.wallet_address}')    
        except Exception as e:
            logger.error(f'Error in mint Lil Chogstars {e} | Wallet {self.wallet_address}')