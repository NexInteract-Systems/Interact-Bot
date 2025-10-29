# Discord Bot Subscription System

A comprehensive subscription management system for your Discord AI bot with usage tracking, premium model access, and payment processing.

## 🚀 Features

### Core Features
- **Free Tier**: 150 messages per day with access to standard models
- **Premium Tier**: Unlimited messages + access to premium models (Mistral Large, Llama 3.1 70B)
- **Pro Tier**: Everything in Premium + priority support + advanced features
- **Usage Tracking**: Real-time daily usage monitoring
- **Payment Processing**: Stripe integration for secure payments
- **Web Dashboard**: Beautiful web interface for subscription management

### Premium Models
- **Mistral Large** - Advanced reasoning capabilities
- **Llama 3.1 70B** - Meta's flagship open-source model
- **Mistral Large 2** - Latest Mistral AI capabilities
- **GPT-4o** - OpenAI's most capable model
- **Claude 3.5 Sonnet** - Anthropic's flagship model

## 📋 Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   # Stripe Configuration (Optional - for payment processing)
   export STRIPE_SECRET_KEY="sk_test_..."
   export STRIPE_PUBLISHABLE_KEY="pk_test_..."
   export STRIPE_WEBHOOK_SECRET="whsec_..."
   ```

3. **Start the Bot**
   ```bash
   python main.py
   ```

4. **Start the Dashboard** (Optional)
   ```bash
   python subscription_dashboard.py
   ```

## 🎮 Discord Commands

### User Commands
- `!subscribe` - View subscription plans and current status
- `!usage` - Check your daily usage and limits
- `!upgrade` - Upgrade to premium subscription
- `!cancel` - Cancel your subscription

### Admin Commands
- `!subscriptionstats` - View subscription statistics
- `!cleanup` - Clean up expired subscriptions

## 💳 Payment Integration

### Stripe Setup
1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe dashboard
3. Set up webhook endpoints for payment events
4. Configure your environment variables

### Payment Flow
1. User runs `!upgrade` command
2. Bot creates Stripe checkout session
3. User completes payment on Stripe
4. Webhook confirms payment
5. Subscription is automatically activated

## 📊 Usage Tracking

### Daily Limits
- **Free Users**: 150 messages per day
- **Premium Users**: Unlimited messages
- **Pro Users**: Unlimited messages + priority support

### Usage Monitoring
- Real-time usage tracking
- Daily reset at midnight UTC
- Usage history retention (90 days)
- Automatic cleanup of expired data

## 🖥️ Web Dashboard

Access the dashboard at `http://localhost:5001`

### Features
- **Statistics Overview**: Total users, active subscriptions, conversion rates
- **Subscription Management**: Create, modify, cancel subscriptions
- **Usage Analytics**: Detailed usage statistics
- **Payment Processing**: Stripe integration
- **Admin Panel**: User management and system administration

## 🔧 Configuration

### Subscription Settings
Edit `subscription_config.py` to customize:

```python
SUBSCRIPTION_CONFIG = {
    'FREE_DAILY_LIMIT': 150,
    'PREMIUM_MODELS': ['mistral-large', 'llama-3.1-70b'],
    'PRICING': {
        'premium': 999,  # $9.99/month
        'pro': 1999      # $19.99/month
    }
}
```

### Model Configuration
- **Free Models**: Available to all users
- **Premium Models**: Require active subscription
- **Model Fallback**: Automatic fallback to available models

## 📁 File Structure

```
├── subscription_manager.py      # Core subscription logic
├── payment_handler.py          # Stripe payment processing
├── subscription_dashboard.py   # Web dashboard
├── subscription_config.py      # Configuration settings
├── templates/
│   └── dashboard.html         # Dashboard HTML template
├── subscription_data.json     # User subscription data
└── payment_data.json         # Payment transaction data
```

## 🔒 Security Features

- **Secure Payment Processing**: Stripe handles all payment data
- **Webhook Verification**: Stripe webhook signature verification
- **Data Encryption**: Sensitive data encrypted at rest
- **Access Control**: Admin-only commands and features
- **Rate Limiting**: Built-in usage limits and tracking

## 📈 Analytics & Monitoring

### Subscription Metrics
- Total users and active subscriptions
- Conversion rates (free to paid)
- Revenue tracking
- Usage patterns and trends

### System Health
- Model availability monitoring
- Payment processing status
- Error tracking and logging
- Performance metrics

## 🚀 Deployment

### Production Setup
1. **Environment Variables**
   ```bash
   export STRIPE_SECRET_KEY="sk_live_..."
   export STRIPE_PUBLISHABLE_KEY="pk_live_..."
   export STRIPE_WEBHOOK_SECRET="whsec_..."
   ```

2. **Database** (Optional)
   - Consider migrating to PostgreSQL for production
   - Implement proper backup strategies
   - Set up monitoring and alerting

3. **Web Server**
   - Use Gunicorn or similar for production
   - Set up reverse proxy (nginx)
   - Configure SSL certificates

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## 🛠️ Development

### Adding New Features
1. **New Subscription Tiers**: Update `subscription_config.py`
2. **New Premium Models**: Add to `PREMIUM_MODELS` list
3. **Custom Pricing**: Modify pricing configuration
4. **Additional Commands**: Add to `main.py`

### Testing
```bash
# Test subscription system
python -c "from subscription_manager import subscription_manager; print('OK')"

# Test payment processing
python -c "from payment_handler import payment_handler; print('OK')"

# Test dashboard
python subscription_dashboard.py
```

## 📞 Support

- **Documentation**: This README and inline code comments
- **Issues**: GitHub Issues for bug reports
- **Contact**: support@interactdevelopments.me
- **Website**: https://interactdevelopments.me/

## 📄 License

This subscription system is part of the Interact Developments Discord Bot project.

## 🔄 Updates

### Version 1.0.0
- Initial subscription system implementation
- Stripe payment integration
- Web dashboard
- Usage tracking
- Premium model access

### Future Updates
- [ ] Multiple payment methods
- [ ] Subscription analytics
- [ ] Automated billing
- [ ] API access for developers
- [ ] Mobile app integration

---

**Built by Interact Developments Inc.**  
*Creating innovative Discord solutions since 2019*
