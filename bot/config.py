import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

POLYMARKET_API_KEY = os.getenv("RELAYER_API_KEY", "019d2216-8d1b-7ed1-b2a0-76932b1d41a3")
POLYMARKET_API_KEY_ADDRESS = os.getenv("RELAYER_API_KEY_ADDRESS", "0x86cE9823998f6F323151aA613e751156Dc1b9486")
POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")

API_HEADERS = {
    "RELAYER_API_KEY": POLYMARKET_API_KEY,
    "RELAYER_API_KEY_ADDRESS": POLYMARKET_API_KEY_ADDRESS,
    "Content-Type": "application/json"
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

class Config:
    API_BASE_URL = "https://clob.polymarket.com"
    GAMMA_API_URL = "https://gamma-api.polymarket.com"
    WS_URL = "wss://ws-subscriptions.polymarket.com"
    
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "0.05"))
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
    STOP_LOSS_PERCENTAGE = float(os.getenv("STOP_LOSS_PERCENTAGE", "0.02"))
    MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
    
    DEFAULT_MIN_PROBABILITY = float(os.getenv("DEFAULT_MIN_PROBABILITY", "0.05"))
    DEFAULT_MAX_PROBABILITY = float(os.getenv("DEFAULT_MAX_PROBABILITY", "0.95"))
