"""
Payment Processing Handler for Discord Bot Subscriptions
Handles Stripe integration and payment processing
"""

import os
import json
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import stripe
except ImportError:
    stripe = None

class PaymentStatus(Enum):
    """Payment status"""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class PaymentInfo:
    """Payment information"""
    payment_id: str
    user_id: str
    amount: int  # in cents
    currency: str
    status: PaymentStatus
    stripe_payment_intent_id: Optional[str] = None
    created_at: float = 0.0
    completed_at: Optional[float] = None

class PaymentHandler:
    """Handles payment processing for subscriptions"""
    
    def __init__(self, stripe_secret_key: Optional[str] = None):
        self.stripe_secret_key = stripe_secret_key or os.getenv('STRIPE_SECRET_KEY')
        self.stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        # Initialize Stripe if available
        if stripe and self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key
            self.stripe_enabled = True
        else:
            self.stripe_enabled = False
            print("⚠️ Stripe not configured. Payment processing disabled.")
        
        # Payment data storage
        self.payments_file = "payment_data.json"
        self.payments: Dict[str, PaymentInfo] = {}
        self._load_payments()
    
    def _load_payments(self):
        """Load payment data from file"""
        if os.path.exists(self.payments_file):
            try:
                with open(self.payments_file, 'r') as f:
                    data = json.load(f)
                    for payment_id, payment_data in data.items():
                        payment_data['status'] = PaymentStatus(payment_data['status'])
                        self.payments[payment_id] = PaymentInfo(**payment_data)
            except Exception as e:
                print(f"Error loading payment data: {e}")
    
    def _save_payments(self):
        """Save payment data to file"""
        try:
            data = {
                payment_id: {
                    'payment_id': payment.payment_id,
                    'user_id': payment.user_id,
                    'amount': payment.amount,
                    'currency': payment.currency,
                    'status': payment.status.value,
                    'stripe_payment_intent_id': payment.stripe_payment_intent_id,
                    'created_at': payment.created_at,
                    'completed_at': payment.completed_at
                }
                for payment_id, payment in self.payments.items()
            }
            with open(self.payments_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving payment data: {e}")
    
    def create_payment_intent(
        self, 
        user_id: str, 
        amount: int, 
        currency: str = "usd",
        description: str = "Discord Bot Subscription"
    ) -> Optional[Dict[str, Any]]:
        """Create a Stripe payment intent"""
        if not self.stripe_enabled:
            return None
        
        try:
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                description=description,
                metadata={
                    'user_id': user_id,
                    'service': 'discord_bot_subscription'
                }
            )
            
            # Store payment info
            payment_id = f"pi_{int(time.time())}_{user_id}"
            payment_info = PaymentInfo(
                payment_id=payment_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
                status=PaymentStatus.PENDING,
                stripe_payment_intent_id=intent.id,
                created_at=time.time()
            )
            
            self.payments[payment_id] = payment_info
            self._save_payments()
            
            return {
                'payment_id': payment_id,
                'client_secret': intent.client_secret,
                'publishable_key': self.stripe_publishable_key,
                'amount': amount,
                'currency': currency
            }
            
        except Exception as e:
            print(f"Error creating payment intent: {e}")
            return None
    
    def create_checkout_session(
        self, 
        user_id: str, 
        price_id: str,
        success_url: str,
        cancel_url: str
    ) -> Optional[Dict[str, Any]]:
        """Create a Stripe checkout session"""
        if not self.stripe_enabled:
            return None
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user_id,
                    'service': 'discord_bot_subscription'
                }
            )
            
            return {
                'session_id': session.id,
                'url': session.url
            }
            
        except Exception as e:
            print(f"Error creating checkout session: {e}")
            return None
    
    def get_payment_status(self, payment_id: str) -> Optional[PaymentStatus]:
        """Get payment status"""
        payment = self.payments.get(payment_id)
        return payment.status if payment else None
    
    def update_payment_status(self, payment_id: str, status: PaymentStatus):
        """Update payment status"""
        if payment_id in self.payments:
            self.payments[payment_id].status = status
            if status == PaymentStatus.SUCCEEDED:
                self.payments[payment_id].completed_at = time.time()
            self._save_payments()
    
    def handle_webhook(self, payload: str, signature: str) -> bool:
        """Handle Stripe webhook events"""
        if not self.stripe_enabled or not self.webhook_secret:
            return False
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                # Find and update payment status
                for payment_id, payment in self.payments.items():
                    if payment.stripe_payment_intent_id == payment_intent['id']:
                        self.update_payment_status(payment_id, PaymentStatus.SUCCEEDED)
                        return True
            
            elif event['type'] == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                # Find and update payment status
                for payment_id, payment in self.payments.items():
                    if payment.stripe_payment_intent_id == payment_intent['id']:
                        self.update_payment_status(payment_id, PaymentStatus.FAILED)
                        return True
            
            return True
            
        except Exception as e:
            print(f"Error handling webhook: {e}")
            return False
    
    def get_payment_history(self, user_id: str) -> list:
        """Get user's payment history"""
        user_payments = [
            payment for payment in self.payments.values()
            if payment.user_id == user_id
        ]
        return sorted(user_payments, key=lambda x: x.created_at, reverse=True)
    
    def is_payment_successful(self, payment_id: str) -> bool:
        """Check if payment was successful"""
        status = self.get_payment_status(payment_id)
        return status == PaymentStatus.SUCCEEDED
    
    def get_stripe_config(self) -> Dict[str, Any]:
        """Get Stripe configuration for frontend"""
        return {
            'enabled': self.stripe_enabled,
            'publishable_key': self.stripe_publishable_key,
            'currency': 'usd'
        }

# Global payment handler instance
payment_handler = PaymentHandler()
