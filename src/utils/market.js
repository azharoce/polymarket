const fetch = require('node-fetch');
require('dotenv').config();

// Polymarket API endpoints
const POLYMARKET_API = {
  BASE_URL: 'https://gamma-api.polymarket.com',
  MARKETS: '/markets',
  ORDER_BOOK: '/order-book',
  TRADES: '/trades'
};

// Fetch active markets from Polymarket
async function fetchMarkets() {
  try {
    const response = await fetch(`${POLYMARKET_API.BASE_URL}${POLYMARKET_API.MARKETS}?closed=false&archived=false`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch markets: ${response.status}`);
    }
    
    const markets = await response.json();
    console.log(`Fetched ${markets.length} active markets`);
    return markets;
  } catch (error) {
    console.error('Error fetching markets:', error.message);
    throw error;
  }
}

// Fetch order book for a specific market
async function fetchOrderBook(marketId) {
  try {
    const response = await fetch(`${POLYMARKET_API.BASE_URL}${POLYMARKET_API.ORDER_BOOK}?market_id=${marketId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch order book: ${response.status}`);
    }
    
    const orderBook = await response.json();
    return orderBook;
  } catch (error) {
    console.error('Error fetching order book:', error.message);
    throw error;
  }
}

// Subscribe to market updates via WebSocket
function subscribeToMarketUpdates(marketId, onUpdate) {
  // TODO: Implement WebSocket connection for real-time updates
  // Polymarket uses WebSocket for real-time market data
  console.log(`Subscribing to updates for market: ${marketId}`);
  
  // Placeholder for WebSocket implementation
  const ws = new WebSocket('wss://ws-subscriptions.polymarket.com/');
  
  ws.onopen = () => {
    console.log('WebSocket connected');
    // Subscribe to specific market updates
    ws.send(JSON.stringify({
      market_id: marketId,
      subscription_type: 'order_book'
    }));
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onUpdate(data);
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
  
  ws.onclose = () => {
    console.log('WebSocket disconnected');
  };
  
  return ws;
}

// Place a market order on Polymarket
async function placeOrder(orderParams, wallet) {
  try {
    // Sign the order using EIP-712
    const { signOrder } = require('./auth');
    const signature = await signOrder(orderParams, wallet);
    
    // TODO: Implement actual order placement via Polymarket API
    // This would typically involve sending the signed order to Polymarket's API
    
    console.log('Placing order with signature:', signature);
    
    // Placeholder response
    return {
      success: true,
      orderId: `order_${Date.now()}`,
      signature
    };
  } catch (error) {
    console.error('Error placing order:', error.message);
    throw error;
  }
}

module.exports = {
  fetchMarkets,
  fetchOrderBook,
  subscribeToMarketUpdates,
  placeOrder
};