const { ethers } = require('ethers');
require('dotenv').config();

// Polymarket contract addresses (Polygon mainnet)
const POLYMARKET_CONTRACTS = {
  USDC: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
  // Add other relevant contracts as needed
};

// Wallet connection and authentication
async function connectWallet() {
  if (!process.env.PRIVATE_KEY) {
    throw new Error('PRIVATE_KEY not found in environment variables');
  }

  // Connect to Polygon mainnet
  const provider = new ethers.JsonRpcProvider(process.env.POLYGON_RPC_URL || 'https://polygon-rpc.com');
  const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
  
  console.log('Wallet connected:', wallet.address);
  return wallet;
}

// Get account information including USDC balance
async function getAccountInfo(wallet) {
  const usdcContract = new ethers.Contract(
    POLYMARKET_CONTRACTS.USDC,
    ['function balanceOf(address) view returns (uint256)'],
    wallet
  );
  
  const balance = await usdcContract.balanceOf(wallet.address);
  const usdcBalance = ethers.formatUnits(balance, 6); // USDC has 6 decimals
  
  return {
    address: wallet.address,
    usdcBalance: ethers.parseUnits(usdcBalance, 6) // Return as wei equivalent for internal use
  };
}

// Sign EIP-712 order for Polymarket
async function signOrder(orderParams, wallet) {
  // TODO: Implement EIP-712 signing for Polymarket orders
  // This will require the specific order structure from Polymarket API
  console.log('Signing order:', orderParams);
  
  // Placeholder implementation
  const signature = await wallet.signMessage(
    ethers.getBytes(JSON.stringify(orderParams))
  );
  
  return signature;
}

module.exports = {
  connectWallet,
  getAccountInfo,
  signOrder
};