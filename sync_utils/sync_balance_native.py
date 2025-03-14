import sys
import os
from web3 import Web3
from web3.providers import HTTPProvider

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

class SyncTokenBalanceChecker:

    def __init__(self, rpc_url: str, private_key: str):
        self.w3 = Web3(HTTPProvider(rpc_url))
        self.private_key = private_key
        self.wallet_address = Web3.to_checksum_address(
            self.w3.eth.account.from_key(private_key).address
        )

        self.tokens = {
            "CHOG": "0xE0590015A873bF326bd645c3E1266d4db41C4E6B",
            "YAKI": "0xfe140e1dCe99Be9F4F15d657CD9b7BF622270C50",
            "DAK": "0x0F0BDEbF0F83cD1EE3974779Bcb7315f9808c714",
            "WMON": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",
            "ETH": "0x836047a99e11F376522B447bffb6e3495Dd0637c",
            "gMON": "0xaEef2f6B429Cb59C9B2D7bB2141ADa993E8571c3",
            "BEAN": "0x268E4E24E0051EC27b3D27A95977E71cE6875a05"
        }

        self.erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function",
            },
        ]

    def get_token_balance(self, token_address: str) -> float:
        token_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=self.erc20_abi,
        )

        balance = token_contract.functions.balanceOf(self.wallet_address).call()
        decimals = token_contract.functions.decimals().call()
        readable_balance = balance / (10 ** decimals)
        return round(readable_balance, 6)

    def get_all_balances(self) -> dict:
        balances = {}
        for token_name, token_address in self.tokens.items():
            balances[token_name] = self.get_token_balance(token_address)
        return balances
    
    def get_mon_balance(self) -> float:
        balance_wei = self.w3.eth.get_balance(self.wallet_address)
        balance_mon = self.w3.from_wei(balance_wei, "ether")
        return round(balance_mon, 6)

