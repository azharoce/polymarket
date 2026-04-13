// Risk management module - protects capital and stops bot if losses are too high
require('dotenv').config();

// Risk parameters from environment or defaults
const RISK_PARAMS = {
  MAX_DAILY_LOSS: parseFloat(process.env.MAX_DAILY_LOSS) || 0.05, // 5% of balance
  MAX_POSITION_SIZE: parseFloat(process.env.MAX_POSITION_SIZE) || 0.1, // 10% of balance per trade
  STOP_LOSS_PERCENTAGE: parseFloat(process.env.STOP_LOSS_PERCENTAGE) || 0.02, // 2% stop loss
  MAX_CONSECUTIVE_LOSSES: parseInt(process.env.MAX_CONSECUTIVE_LOSSES) || 3, // Stop after N losses
  DAILY_RESET_HOUR: parseInt(process.env.DAILY_RESET_HOUR) || 0 // Reset daily stats at UTC hour
};

// Track trading statistics
let dailyStats = {
  startBalance: 0,
  currentBalance: 0,
  dailyPnL: 0,
  tradesCount: 0,
  winningTrades: 0,
  losingTrades: 0,
  consecutiveLosses: 0,
  lastReset: new Date()
};

/**
 * Initialize risk management with starting balance
 * @param {number} startingBalance - Starting balance in USDC (wei format)
 */
function initializeRisk(startingBalance) {
  dailyStats.startBalance = startingBalance;
  dailyStats.currentBalance = startingBalance;
  dailyStats.lastReset = new Date();
  console.log(`Risk management initialized with starting balance: ${startingBalance}`);
}

/**
 * Check if trading is allowed based on risk parameters
 * @returns {Object} Permission to trade and reason if not allowed
 */
function canTrade() {
  const now = new Date();
  
  // Check if we need to reset daily stats
  if (now.getUTCHours() >= RISK_PARAMS.DAILY_RESET_HOUR && 
      dailyStats.lastReset.getDate() !== now.getDate()) {
    resetDailyStats();
  }
  
  // Check daily loss limit
  const dailyLossPercentage = Math.abs(dailyStats.dailyPnL) / dailyStats.startBalance;
  if (dailyStats.dailyPnL < 0 && dailyLossPercentage > RISK_PARAMS.MAX_DAILY_LOSS) {
    return {
      allowed: false,
      reason: `Daily loss limit exceeded: ${(dailyLossPercentage * 100).toFixed(2)}%`
    };
  }
  
  // Check consecutive losses
  if (dailyStats.consecutiveLosses >= RISK_PARAMS.MAX_CONSECUTIVE_LOSSES) {
    return {
      allowed: false,
      reason: `Maximum consecutive losses reached: ${dailyStats.consecutiveLosses}`
    };
  }
  
  return { allowed: true, reason: 'OK' };
}

/**
 * Calculate position size based on risk parameters
 * @param {number} balance - Current balance in USDC (wei format)
 * @param {number} confidence - Signal confidence (0 to 1)
 * @returns {number} Position size in USDC (wei format)
 */
function calculatePositionSize(balance, confidence = 1) {
  // Base position size as percentage of balance
  let positionSize = balance * RISK_PARAMS.MAX_POSITION_SIZE;
  
  // Adjust by confidence (higher confidence = larger position)
  positionSize *= confidence;
  
  // Ensure we don't exceed balance
  return Math.min(positionSize, balance * 0.95); // Never use more than 95% of balance
}

/**
 * Update trade result and adjust statistics
 * @param {number} pnl - Profit/loss from trade in USDC (wei format)
 */
function updateTradeResult(pnl) {
  dailyStats.tradesCount++;
  dailyStats.dailyPnL += pnl;
  dailyStats.currentBalance += pnl;
  
  if (pnl > 0) {
    dailyStats.winningTrades++;
    dailyStats.consecutiveLosses = 0; // Reset consecutive losses on win
  } else {
    dailyStats.losingTrades++;
    dailyStats.consecutiveLosses++;
  }
  
  console.log(`Trade updated. PnL: ${pnl}, Daily PnL: ${dailyStats.dailyPnL}`);
}

/**
 * Reset daily statistics
 */
function resetDailyStats() {
  console.log('Resetting daily statistics...');
  dailyStats.startBalance = dailyStats.currentBalance;
  dailyStats.dailyPnL = 0;
  dailyStats.tradesCount = 0;
  dailyStats.winningTrades = 0;
  dailyStats.losingTrades = 0;
  dailyStats.consecutiveLosses = 0;
  dailyStats.lastReset = new Date();
}

/**
 * Get current risk statistics
 * @returns {Object} Current risk statistics
 */
function getRiskStats() {
  return {
    ...dailyStats,
    dailyLossPercentage: Math.abs(dailyStats.dailyPnL) / dailyStats.startBalance,
    winRate: dailyStats.tradesCount > 0 ? 
      (dailyStats.winningTrades / dailyStats.tradesCount) * 100 : 0
  };
}

module.exports = {
  initializeRisk,
  canTrade,
  calculatePositionSize,
  updateTradeResult,
  resetDailyStats,
  getRiskStats,
  RISK_PARAMS
};