"""
Subscription Management System for Discord Bot
Handles user subscriptions, usage tracking, and premium model access
"""

import json
import time
import asyncio
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import os
from datetime import datetime, timedelta

class SubscriptionTier(Enum):
    """Available subscription tiers"""
    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"
    ULTRA_PREMIUM = "ultra_premium"

class SubscriptionStatus(Enum):
    """Subscription status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"

@dataclass
class SubscriptionInfo:
    """User subscription information"""
    user_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    start_date: float
    end_date: float
    auto_renew: bool = True
    payment_method: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None

@dataclass
class UsageStats:
    """Daily usage statistics"""
    user_id: str
    date: str  # YYYY-MM-DD format
    messages_used: int
    premium_messages_used: int
    last_reset: float
    nsfw_messages_used: int = 0  # NSFW message count

class SubscriptionManager:
    """Manages user subscriptions and usage tracking"""
    
    def __init__(self, data_file: str = "subscription_data.json"):
        self.data_file = data_file
        self.subscriptions: Dict[str, SubscriptionInfo] = {}
        self.usage_stats: Dict[str, UsageStats] = {}
        # Users with unlimited, maxed-out access regardless of tier
        self.whitelist: List[str] = []
        
        # Configuration
        self.FREE_DAILY_LIMIT = 150
        self.NSFW_DAILY_LIMIT = 30  # NSFW messages per day for free users
        self.PREMIUM_MODELS = ["mistral-large", "llama-3.1-70b", "mistralai/mistral-large-2407"]
        self.ULTRA_PREMIUM_MODELS = ["x-ai/grok-2.121", "x-ai/grok-beta"]  # Grok AI models
        
        # Subscription pricing (in cents)
        self.PRICES = {
            SubscriptionTier.PREMIUM: 999,  # $9.99/month
            SubscriptionTier.PRO: 1999,      # $19.99/month
            SubscriptionTier.ULTRA_PREMIUM: 33300  # $99.90 per 3 months ($33.30/month)
        }
        
        self._load_data()
        # Seed owner to whitelist if configured
        try:
            from config import OWNER_USER_ID
            if OWNER_USER_ID and OWNER_USER_ID > 0:
                owner_str = str(OWNER_USER_ID)
                if owner_str not in self.whitelist:
                    self.whitelist.append(owner_str)
                    self._save_data()
        except Exception:
            # Config may not be available in some contexts; ignore
            pass
    
    def _load_data(self):
        """Load subscription and usage data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load subscriptions
                    for user_id, sub_data in data.get('subscriptions', {}).items():
                        sub_data['tier'] = SubscriptionTier(sub_data['tier'])
                        sub_data['status'] = SubscriptionStatus(sub_data['status'])
                        self.subscriptions[user_id] = SubscriptionInfo(**sub_data)
                    
                    # Load usage stats
                    for key, usage_data in data.get('usage_stats', {}).items():
                        self.usage_stats[key] = UsageStats(**usage_data)
                    
                    # Load whitelist
                    self.whitelist = data.get('whitelist', []) or []
                        
            except Exception as e:
                print(f"Error loading subscription data: {e}")
    
    def _save_data(self):
        """Save subscription and usage data to file"""
        try:
            data = {
                'subscriptions': {
                    user_id: asdict(sub) for user_id, sub in self.subscriptions.items()
                },
                'usage_stats': {
                    key: asdict(usage) for key, usage in self.usage_stats.items()
                },
                'whitelist': self.whitelist
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving subscription data: {e}")
    
    def get_user_subscription(self, user_id: str) -> Optional[SubscriptionInfo]:
        """Get user's subscription information"""
        return self.subscriptions.get(user_id)
    
    def get_user_tier(self, user_id: str) -> SubscriptionTier:
        """Get user's subscription tier"""
        # Whitelisted users have maxed-out tier
        if self.is_whitelisted(user_id):
            return SubscriptionTier.ULTRA_PREMIUM
        subscription = self.get_user_subscription(user_id)
        if subscription and subscription.status == SubscriptionStatus.ACTIVE:
            if subscription.end_date > time.time():
                return subscription.tier
        return SubscriptionTier.FREE
    
    def is_premium_user(self, user_id: str) -> bool:
        """Check if user has active premium subscription"""
        if self.is_whitelisted(user_id):
            return True
        tier = self.get_user_tier(user_id)
        return tier in [SubscriptionTier.PREMIUM, SubscriptionTier.PRO, SubscriptionTier.ULTRA_PREMIUM]
    
    def can_use_premium_model(self, user_id: str, model_id: str) -> bool:
        """Check if user can use a premium model"""
        # Check if it's an ultra-premium model
        if model_id in self.ULTRA_PREMIUM_MODELS:
            return self.get_user_tier(user_id) == SubscriptionTier.ULTRA_PREMIUM
        
        # Check if it's a premium model
        if model_id not in self.PREMIUM_MODELS:
            return True  # Non-premium models are always available
        
        return self.is_premium_user(user_id)
    
    def get_daily_usage(self, user_id: str) -> UsageStats:
        """Get user's daily usage statistics"""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{user_id}:{today}"
        
        if key not in self.usage_stats:
            self.usage_stats[key] = UsageStats(
                user_id=user_id,
                date=today,
                messages_used=0,
                premium_messages_used=0,
                last_reset=time.time()
            )
        
        return self.usage_stats[key]
    
    def can_send_message(self, user_id: str, is_premium_model: bool = False, is_nsfw: bool = False) -> bool:
        """Check if user can send a message"""
        # Whitelist bypasses all limits
        if self.is_whitelisted(user_id):
            return True
        usage = self.get_daily_usage(user_id)
        
        if is_premium_model:
            # Premium users have unlimited premium model usage
            if self.is_premium_user(user_id):
                return True
            # Free users can't use premium models
            return False
        
        # Check NSFW limits
        if is_nsfw:
            if self.is_premium_user(user_id):
                return True  # Premium users have unlimited NSFW access
            return usage.nsfw_messages_used < self.NSFW_DAILY_LIMIT
        
        # Check daily limit for free users
        if not self.is_premium_user(user_id):
            return usage.messages_used < self.FREE_DAILY_LIMIT
        
        # Premium users have higher limits (or unlimited)
        return True

    # -------- Whitelist Management --------
    def is_whitelisted(self, user_id: str) -> bool:
        """Check if a user is whitelisted for unlimited access"""
        return str(user_id) in self.whitelist

    def add_to_whitelist(self, user_id: str) -> bool:
        """Add a user to the whitelist"""
        uid = str(user_id)
        if uid not in self.whitelist:
            self.whitelist.append(uid)
            self._save_data()
            return True
        return False

    def remove_from_whitelist(self, user_id: str) -> bool:
        """Remove a user from the whitelist"""
        uid = str(user_id)
        if uid in self.whitelist:
            self.whitelist.remove(uid)
            self._save_data()
            return True
        return False

    def get_whitelist(self) -> List[str]:
        """Get the current whitelist"""
        return list(self.whitelist)
    
    def record_message_usage(self, user_id: str, is_premium_model: bool = False, is_nsfw: bool = False):
        """Record a message usage"""
        usage = self.get_daily_usage(user_id)
        
        if is_premium_model:
            usage.premium_messages_used += 1
        else:
            usage.messages_used += 1
        
        if is_nsfw:
            usage.nsfw_messages_used += 1
        
        self._save_data()
    
    def get_usage_summary(self, user_id: str) -> Dict[str, Any]:
        """Get user's usage summary"""
        usage = self.get_daily_usage(user_id)
        subscription = self.get_user_subscription(user_id)
        tier = self.get_user_tier(user_id)
        
        return {
            'tier': tier.value,
            'daily_messages_used': usage.messages_used,
            'daily_premium_messages_used': usage.premium_messages_used,
            'daily_limit': self.FREE_DAILY_LIMIT if tier == SubscriptionTier.FREE else "Unlimited",
            'premium_models_available': self.is_premium_user(user_id),
            'subscription_status': subscription.status.value if subscription else "none",
            'subscription_end_date': subscription.end_date if subscription else None
        }
    
    def create_subscription(
        self, 
        user_id: str, 
        tier: SubscriptionTier, 
        duration_days: Optional[int] = None,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None
    ) -> bool:
        """Create a new subscription"""
        try:
            # Set default duration based on tier if not specified
            if duration_days is None:
                if tier == SubscriptionTier.ULTRA_PREMIUM:
                    duration_days = 90  # 3 months for ultra-premium
                else:
                    duration_days = 30  # 1 month for premium/pro
            
            start_time = time.time()
            end_time = start_time + (duration_days * 24 * 60 * 60)
            
            subscription = SubscriptionInfo(
                user_id=user_id,
                tier=tier,
                status=SubscriptionStatus.ACTIVE,
                start_date=start_time,
                end_date=end_time,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id
            )
            
            self.subscriptions[user_id] = subscription
            self._save_data()
            return True
            
        except Exception as e:
            print(f"Error creating subscription: {e}")
            return False
    
    def cancel_subscription(self, user_id: str) -> bool:
        """Cancel user's subscription"""
        if user_id in self.subscriptions:
            self.subscriptions[user_id].status = SubscriptionStatus.CANCELLED
            self.subscriptions[user_id].auto_renew = False
            self._save_data()
            return True
        return False
    
    def extend_subscription(self, user_id: str, days: int) -> bool:
        """Extend user's subscription"""
        if user_id in self.subscriptions:
            subscription = self.subscriptions[user_id]
            if subscription.status == SubscriptionStatus.ACTIVE:
                subscription.end_date += (days * 24 * 60 * 60)
                self._save_data()
                return True
        return False
    
    def get_subscription_price(self, tier: SubscriptionTier) -> int:
        """Get subscription price in cents"""
        return self.PRICES.get(tier, 0)
    
    def get_premium_models(self) -> List[str]:
        """Get list of premium model IDs"""
        return self.PREMIUM_MODELS.copy()
    
    def get_ultra_premium_models(self) -> List[str]:
        """Get list of ultra-premium model IDs"""
        return self.ULTRA_PREMIUM_MODELS.copy()
    
    def cleanup_expired_subscriptions(self):
        """Clean up expired subscriptions"""
        current_time = time.time()
        expired_count = 0
        
        for user_id, subscription in self.subscriptions.items():
            if (subscription.status == SubscriptionStatus.ACTIVE and 
                subscription.end_date < current_time):
                subscription.status = SubscriptionStatus.EXPIRED
                expired_count += 1
        
        if expired_count > 0:
            print(f"Marked {expired_count} subscriptions as expired")
            self._save_data()
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        stats = {
            'total_users': len(self.subscriptions),
            'active_subscriptions': 0,
            'free_users': 0,
            'premium_users': 0,
            'pro_users': 0,
            'ultra_premium_users': 0,
            'expired_subscriptions': 0
        }
        
        current_time = time.time()
        
        for subscription in self.subscriptions.values():
            if subscription.status == SubscriptionStatus.ACTIVE and subscription.end_date > current_time:
                stats['active_subscriptions'] += 1
                if subscription.tier == SubscriptionTier.PREMIUM:
                    stats['premium_users'] += 1
                elif subscription.tier == SubscriptionTier.PRO:
                    stats['pro_users'] += 1
                elif subscription.tier == SubscriptionTier.ULTRA_PREMIUM:
                    stats['ultra_premium_users'] += 1
            elif subscription.status == SubscriptionStatus.EXPIRED:
                stats['expired_subscriptions'] += 1
        
        # Count free users (users with no active subscription)
        stats['free_users'] = stats['total_users'] - stats['active_subscriptions']
        
        return stats

# Global subscription manager instance
subscription_manager = SubscriptionManager()
