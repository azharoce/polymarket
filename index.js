// Polymarket Trading Bot - Entry Point
require('dotenv').config();
const { connectWallet, getAccountInfo, signOrder } = require('./src/auth');
const { fetchMarkets, fetchOrderBook, subscribeToMarketUpdates, placeOrder } = require('./src/utils/market');
const { executeStrategy } = require('./src/strategy');
const { initializeRisk, canTrade, calculatePositionSize, updateTradeResult, getRiskStats } = require('./src/risk');

// Main async function to initialize and run the bot
async function main() {
  console.log('Starting Polymarket Trading Bot...');
  
  let wallet;
  let startingBalance;
  
  try {
    // STEP 1: Auth dulu (tanpa auth tidak bisa apa-apa)
    console.log('\n=== STEP 1: Authentication ===');
    wallet = await connectWallet();
    const accountInfo = await getAccountInfo(wallet);
    startingBalance = accountInfo.usdcBalance;
    
    console.log('Connected wallet:', accountInfo.address);
    console.log('USDC Balance:', ethers.formatUnits(startingBalance, 6));
    
    // Initialize risk management
    initializeRisk(startingBalance);
    
    // STEP 2: Fetch market + subscribe WebSocket
    console.log('\n=== STEP 2: Market Data Subscription ===');
    const markets = await fetchMarkets();
    
    if (markets.length === 0) {
      throw new Error('No active markets found');
    }
    
    // Use the first market for demonstration
    const selectedMarket = markets[0];
    console.log(`Selected market: ${selectedMarket.question} (ID: ${selectedMarket.id})`);
    
    // Fetch initial order book
    const orderBook = await fetchOrderBook(selectedMarket.id);
    console.log('Initial order book fetched');
    
    // Set up WebSocket subscription for real-time updates
    const ws = subscribeToMarketUpdates(selectedMarket.id, (data) => {
      console.log('Received WebSocket update:', data);
      // In a real implementation, you would update your local order book here
    });
    
    // STEP 3: Eksekusi order manual (test kecil)
    console.log('\n=== STEP 3: Manual Order Execution (Test) ===');
    console.log('Performing a small test order...');
    
    // Create a minimal test order (this won't actually be placed on Polymarket)
    // In a real implementation, you would create a proper order object
    const testOrderParams = {
      market_id: selectedMarket.id,
      side: 'BUY', // or 'SELL'
      price: '0.5', // 0.5 USDC per share (50% probability)
      size: '10', // 10 shares
      token_id: '1', // YES token (1) or NO token (2)
      nonce: Date.now().toString()
    };
    
    console.log('Test order parameters:', testOrderParams);
    
    // Sign the order (but don't actually place it for safety in this example)
    const signature = await signOrder(testOrderParams, wallet);
    console.log('Order signed successfully (not placed for safety):');
    console.log('Signature:', signature);
    
    // In a real bot, you would uncomment this to actually place the order:
    // const orderResult = await placeOrder(testOrderParams, wallet);
    // console.log('Order placed:', orderResult);
    
    console.log('\n⚠️  NOTE: Order was signed but not placed for safety in this example.');
    console.log('To enable actual trading, uncomment the placeOrder call in index.js');
    
    // STEP 4: Baru pasang strategy & risk management
    console.log('\n=== STEP 4: Strategy & Risk Management ===');
    
    // Execute strategy for the selected market
    const signal = await executeStrategy(selectedMarket.id, wallet);
    console.log('Strategy signal generated:', signal);
    
    // Check if trading is allowed based on risk parameters
    const tradePermission = canTrade();
    console.log('Risk check:', tradePermission);
    
    if (tradePermission.allowed) {
      // Calculate position size based on signal confidence
      const positionSize = calculatePositionSize(startingBalance, signal.confidence);
      console.log(`Calculated position size: ${ethers.formatUnits(positionSize, 6)} USDC`);
      
      // In a real implementation, you would place the order here based on the signal
      if (signal.action !== 'HOLD' && signal.confidence > 0.7) {
        console.log(`✅ Strong signal detected: ${signal.action}`);
        console.log('Would place order based on strategy...');
        // Actual order placement would happen here
      } else {
        console.log('⏸️  Signal too weak or HOLD - no trade executed');
      }
    } else {
      console.log(`🛑 Trading not allowed: ${tradePermission.reason}`);
    }
    
    // Display risk statistics
    console.log('\n=== Risk Statistics ===');
    console.log(getRiskStats());
    
    console.log('\n🎉 Bot initialization complete!');
    console.log('In a production bot, you would now:');
    console.log('1. Continue running the strategy loop');
    console.log('2. Monitor WebSocket for market updates');
    console.log('3. Execute trades based on signals + risk management');
    console.log('4. Log all activity and send notifications');
    
    // Keep the WebSocket connection alive for demo purposes
    // In a real bot, you would maintain this connection and handle reconnections
    setTimeout(() => {
      console.log('\n⏳ Demo complete. WebSocket connection would remain open in production.');
      process.exit(0);
    }, 5000);
    
  } catch (error) {
    console.error('❌ Failed to initialize bot:', error.message);
    process.exit(1);
  }
}

// Import ethers for formatting (needed in main function)
const { ethers } = require('ethers');

// Run the bot
main();