"""
Subscription Dashboard for Discord Bot
Web interface for managing subscriptions and payments
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import time
from datetime import datetime, timedelta
from subscription_manager import subscription_manager, SubscriptionTier
from payment_handler import payment_handler

app = Flask(__name__)

@app.route('/')
def index():
    """Main dashboard page"""
    stats = subscription_manager.get_subscription_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/api/stats')
def api_stats():
    """API endpoint for subscription statistics"""
    stats = subscription_manager.get_subscription_stats()
    return jsonify(stats)

@app.route('/api/user/<user_id>')
def api_user_info(user_id):
    """Get user subscription and usage information"""
    subscription = subscription_manager.get_user_subscription(user_id)
    usage_summary = subscription_manager.get_usage_summary(user_id)
    current_tier = subscription_manager.get_user_tier(user_id)
    
    return jsonify({
        'user_id': user_id,
        'tier': current_tier.value,
        'subscription': {
            'status': subscription.status.value if subscription else 'none',
            'tier': subscription.tier.value if subscription else 'free',
            'start_date': subscription.start_date if subscription else None,
            'end_date': subscription.end_date if subscription else None
        },
        'usage': usage_summary
    })

@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    """Create a new subscription"""
    data = request.get_json()
    user_id = data.get('user_id')
    tier = data.get('tier', 'premium')
    duration_days = data.get('duration_days', 30)
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        tier_enum = SubscriptionTier(tier)
        success = subscription_manager.create_subscription(
            user_id=user_id,
            tier=tier_enum,
            duration_days=duration_days
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Subscription created successfully'})
        else:
            return jsonify({'error': 'Failed to create subscription'}), 500
            
    except ValueError:
        return jsonify({'error': 'Invalid tier'}), 400

@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    """Cancel a subscription"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    success = subscription_manager.cancel_subscription(user_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Subscription cancelled successfully'})
    else:
        return jsonify({'error': 'No active subscription found'}), 404

@app.route('/api/usage/<user_id>')
def api_usage(user_id):
    """Get user usage statistics"""
    usage_summary = subscription_manager.get_usage_summary(user_id)
    return jsonify(usage_summary)

@app.route('/payment/create', methods=['POST'])
def create_payment():
    """Create a payment intent"""
    data = request.get_json()
    user_id = data.get('user_id')
    amount = data.get('amount', 999)  # Default to $9.99
    tier = data.get('tier', 'premium')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    # Create payment intent
    payment_data = payment_handler.create_payment_intent(
        user_id=user_id,
        amount=amount,
        description=f"Discord Bot {tier.title()} Subscription"
    )
    
    if payment_data:
        return jsonify(payment_data)
    else:
        return jsonify({'error': 'Payment processing not available'}), 500

@app.route('/payment/status/<payment_id>')
def payment_status(payment_id):
    """Check payment status"""
    status = payment_handler.get_payment_status(payment_id)
    if status:
        return jsonify({'status': status.value})
    else:
        return jsonify({'error': 'Payment not found'}), 404

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    signature = request.headers.get('Stripe-Signature')
    
    if payment_handler.handle_webhook(payload, signature):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Webhook verification failed'}), 400

@app.route('/admin')
def admin_panel():
    """Admin panel for managing subscriptions"""
    stats = subscription_manager.get_subscription_stats()
    return render_template('admin.html', stats=stats)

@app.route('/admin/users')
def admin_users():
    """List all users with subscriptions"""
    # This would typically be paginated in a real application
    users = []
    for user_id, subscription in subscription_manager.subscriptions.items():
        usage = subscription_manager.get_usage_summary(user_id)
        users.append({
            'user_id': user_id,
            'subscription': subscription,
            'usage': usage
        })
    
    return jsonify(users)

@app.route('/admin/cleanup', methods=['POST'])
def admin_cleanup():
    """Clean up expired subscriptions"""
    subscription_manager.cleanup_expired_subscriptions()
    return jsonify({'success': True, 'message': 'Cleanup completed'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
