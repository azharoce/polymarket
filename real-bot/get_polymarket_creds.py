#!/usr/bin/env python3
"""
Script untuk generate Polymarket API Credentials
Berdasarkan guide: https://docs.polymarket.com

Usage:
    python get_polymarket_creds.py

Requirements:
    pip install py-clob-client python-dotenv web3
"""

import os
import sys
import json

print("=" * 80)
print("🎯 POLYMARKET CREDENTIALS GENERATOR".center(80))
print("=" * 80)

# Load .env from parent directory first
from dotenv import load_dotenv
load_dotenv("../.env")

# ==============================================================================
# KONFIGURASI - EDIT INI SESUAI DATA KAMU
# ==============================================================================

# Layer 1: Private Key dari Phantom
# Cara dapat: Phantom → Settings → Manage Accounts → Export Private Key
# Atau di Metamask: Account Details → Export Private Key
PRIVATE_KEY = "GANTI_INI_DENGAN_PRIVATE_KEY_KAMU"  # GANTI INI

# Layer 1: Funder Address dari Polymarket Settings
# Cara dapat: polymarket.com/settings → cari "Wallet Address" atau "Funding"
FUNDER_ADDRESS = "GANTI_INI_DENGAN_FUNDER_ADDRESS"  # GANTI INI

# Signature Type: 0 untuk Phantom/MetaMask (EOA)
SIGNATURE_TYPE = 0

# ==============================================================================
# INSTALASI DEPENDENCIES
# ==============================================================================

def check_dependencies():
    """Cek dan install dependencies jika belum ada"""
    required = ["py_clob_client", "dotenv", "web3", "eth_account"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"\n📦 Installing missing packages: {', '.join(missing)}")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("✅ Dependencies installed!")

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

try:
    check_dependencies()
    
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds
    from web3 import Web3
    
    # Validasi PRIVATE_KEY - cek dari env dulu, lalu dari variabel
    pk_from_env = os.getenv("PRIVATE_KEY")
    if pk_from_env:
        PRIVATE_KEY = pk_from_env
    
    funder_from_env = os.getenv("FUNDER_ADDRESS")
    if funder_from_env:
        FUNDER_ADDRESS = funder_from_env
    
    if not PRIVATE_KEY or PRIVATE_KEY == "GANTI_INI_DENGAN_PRIVATE_KEY_KAMU":
        print("\n❌ ERROR: PRIVATE_KEY belum di-set!")
        print("   Buka file ini dan edit bagian PRIVATE_KEY")
        sys.exit(1)
    
    if not FUNDER_ADDRESS or FUNDER_ADDRESS == "GANTI_INI_DENGAN_FUNDER_ADDRESS":
        print("\n❌ ERROR: FUNDER_ADDRESS belum di-set!")
        print("   Buka polymarket.com/settings untuk dapat alamat wallet kamu")
        sys.exit(1)
    
    # Bersihkan private key dari prefix 0x jika ada
    pk_clean = PRIVATE_KEY.replace("0x", "")
    
    print(f"\n📋 KONFIGURASI:")
    print(f"   Private Key: {pk_clean[:8]}...{pk_clean[-4:]}")
    print(f"   Funder Address: {FUNDER_ADDRESS}")
    print(f"   Signature Type: {SIGNATURE_TYPE} (EOA/Phantom)")
    
    # Initialize ClobClient
    print("\n🔄 Menghubungi Polymarket CLOB...")
    client = ClobClient(
        host="https://clob.polymarket.com",
        chain_id=137,
        key=pk_clean,
        signature_type=SIGNATURE_TYPE
    )
    
    print("✅ Terhubung ke CLOB!")
    
    # Generate API Credentials
    print("\n🔑 Generating API Credentials...")
    creds = client.create_or_derive_api_creds()
    
    print("\n" + "=" * 80)
    print("✅ CREDENTIALS BERHASIL DIBUAT!".center(80))
    print("=" * 80)
    
    print(f"\n📋 CREDENTIALS:")
    print(f"   POLY_API_KEY         = {creds.api_key}")
    print(f"   POLY_API_SECRET      = {creds.api_secret}")
    print(f"   POLY_API_PASSPHRASE  = {creds.api_passphrase}")
    
    # Check USDC Balance
    try:
        w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
        USDC_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
        
        usdc_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT),
            abi=usdc_abi
        )
        
        # Get funder address from client
        funder_addr = client.get_address()
        balance = usdc.functions.balanceOf(funder_addr).call()
        balance_usdc = balance / 1e6
        
        print(f"\n💰 Saldo USDC di Polymarket: ${balance_usdc:.2f}")
    except Exception as e:
        print(f"\n⚠️ Gagal mengambil saldo: {e}")
    
    # Save to .env
    env_content = f"""# ================================================================================
# POLYMARKET BOT - AUTO-GENERATED ENV
# ================================================================================
# Generated by get_polymarket_creds.py

# Layer 1 - Wallet
POLY_PK={PRIVATE_KEY}
POLY_FUNDER_ADDRESS={FUNDER_ADDRESS}
POLY_SIGNATURE_TYPE={SIGNATURE_TYPE}

# Layer 2 - API Credentials
POLY_API_KEY={creds.api_key}
POLY_API_SECRET={creds.api_secret}
POLY_API_PASSPHRASE={creds.api_passphrase}

# Layer 3 - RPC & Endpoints
CLOB_HTTP_URL=https://clob.polymarket.com
CLOB_WS_URL=wss://clob.polymarket.com
CHAIN_ID=137
RPC_URL=https://polygon-rpc.com
WSS_URL=wss://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY

# Contract Addresses
USDC_CONTRACT=0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174

# Bot Config
DRY_RUN=true
SCAN_INTERVAL=60
MAX_CONSECUTIVE_LOSSES=3
"""
    
    env_file = ".env"
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print(f"\n💾 File .env berhasil disimpan!")
    print(f"\n📝 NEXT STEPS:")
    print(f"   1. Edit file .env jika perlu")
    print(f"   2. Run bot: python -m bot.autobet --real")
    print(f"   3. Atau simulation: python -m bot.autobet")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n🔧 TROUBLESHOOTING:")
    print("   - Pastikan PRIVATE_KEY benar (64 karakter hex)")
    print("   - Pastikan sudah login ke polymarket.comminimal sekali")
    print("   - Cek FUNDER_ADDRESS dari polymarket.com/settings")
    sys.exit(1)
