"""
Subscription Configuration for Discord Bot
Centralized configuration for subscription settings
"""

import os
from typing import Dict, Any

# Subscription Settings
SUBSCRIPTION_CONFIG = {
    # Free tier limits
    'FREE_DAILY_LIMIT': 150,
    'FREE_MODELS': [
        'gpt-4o-mini',
        'gpt-3.5-turbo', 
        'gemini-1.5-flash',
        'gemini-pro',
        'claude-3-haiku'
    ],
    
    # Premium models (require subscription)
    'PREMIUM_MODELS': [
        'mistral-large',
        'llama-3.1-70b',
        'mistralai/mistral-large-2407',
        'gpt-4o',
        'claude-3.5-sonnet'
    ],
    
    # Subscription pricing (in cents)
    'PRICING': {
        'premium': 999,  # $9.99/month
        'pro': 1999      # $19.99/month
    },
    
    # Subscription durations (in days)
    'DURATIONS': {
        'monthly': 30,
        'yearly': 365
    },
    
    # Payment settings
    'PAYMENT': {
        'currency': 'usd',
        'stripe_webhook_secret': os.getenv('STRIPE_WEBHOOK_SECRET'),
        'stripe_publishable_key': os.getenv('STRIPE_PUBLISHABLE_KEY'),
        'stripe_secret_key': os.getenv('STRIPE_SECRET_KEY')
    },
    
    # Feature flags
    'FEATURES': {
        'enable_payments': True,
        'enable_webhook': True,
        'enable_dashboard': True,
        'auto_cleanup_expired': True
    },
    
    # Dashboard settings
    'DASHBOARD': {
        'host': '0.0.0.0',
        'port': 5001,
        'debug': False
    },
    
    # Usage tracking
    'USAGE_TRACKING': {
        'reset_hour': 0,  # UTC hour to reset daily usage
        'retention_days': 90,  # How long to keep usage data
        'cleanup_interval_hours': 24  # How often to run cleanup
    }
}

def get_config(key: str = None) -> Any:
    """Get configuration value(s)"""
    if key:
        return SUBSCRIPTION_CONFIG.get(key)
    return SUBSCRIPTION_CONFIG

def update_config(key: str, value: Any):
    """Update configuration value"""
    SUBSCRIPTION_CONFIG[key] = value

def is_premium_model(model_id: str) -> bool:
    """Check if a model requires premium subscription"""
    return model_id in SUBSCRIPTION_CONFIG['PREMIUM_MODELS']

def is_free_model(model_id: str) -> bool:
    """Check if a model is available for free users"""
    return model_id in SUBSCRIPTION_CONFIG['FREE_MODELS']

def get_subscription_price(tier: str) -> int:
    """Get subscription price in cents"""
    return SUBSCRIPTION_CONFIG['PRICING'].get(tier, 0)

def get_daily_limit(tier: str) -> int:
    """Get daily message limit for tier"""
    if tier == 'free':
        return SUBSCRIPTION_CONFIG['FREE_DAILY_LIMIT']
    return float('inf')  # Unlimited for paid tiers
