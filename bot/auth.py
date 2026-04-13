import os
import json
import requests
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from bot.config import API_HEADERS, Config, logger

w3 = Web3(Web3.HTTPProvider(os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")))

def load_wallet() -> LocalAccount:
    private_key = os.getenv("PRIVATE_KEY", "")
    if not private_key:
        logger.warning("PRIVATE_KEY not found - running in SCAN ONLY mode")
        return None
    
    key_without_prefix = private_key.replace("0x", "")
    
    if len(key_without_prefix) != 64:
        logger.warning(f"PRIVATE_KEY length {len(key_without_prefix)} != 64 - running in SCAN ONLY mode")
        return None
    
    try:
        account: LocalAccount = Account.from_key(key_without_prefix)
        logger.info(f"Wallet loaded: {account.address}")
        return account
    except Exception as e:
        logger.warning(f"Failed to load wallet: {e} - running in SCAN ONLY mode")
        return None

def get_account_info(wallet: LocalAccount) -> dict:
    logger.info("Fetching account info...")
    return {
        "address": wallet.address,
        "usdcBalance": "1000000",  # Placeholder - fetch from contract
    }

def sign_order(order_params: dict, wallet: LocalAccount) -> str:
    message = json.dumps(order_params, sort_keys=True)
    signed = wallet.sign_message(message)
    logger.info(f"Order signed: {signed.signature.hex()}")
    return signed.signature.hex()
