# AI Discord Bot - Multi-Model LLM System

A powerful Discord bot with support for multiple AI language models, featuring a web dashboard for model selection and management.

## 🌟 Features

### Multi-Model Support
- **OpenAI Models**: GPT-4o, GPT-4o-mini, GPT-3.5-turbo
- **Google Gemini**: Gemini 2.0 Flash, Gemini 1.5 Flash, Gemini Pro
- **Anthropic Claude**: Claude 3.5 Sonnet, Claude 3 Haiku
- **OpenRouter**: Access to 100+ models (Llama, Mistral, etc.)
- **Automatic Failover**: Seamless switching between models if one fails

### Web Dashboard
- **Model Selection**: Choose your preferred AI model
- **Real-time Statistics**: Usage, costs, response times
- **Model Comparison**: Side-by-side response testing
- **Health Monitoring**: Track model availability and performance
- **User Management**: Per-user model preferences

### Discord Integration
- **Per-User Preferences**: Each user can set their preferred model
- **Model Management Commands**: Full control via Discord commands
- **Status Monitoring**: Real-time model health checks
- **Usage Statistics**: Track model performance and costs

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the bot files
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit `config.py` with your API keys:

```python
# Discord Bot Token
DISCORD_TOKEN = "your_discord_bot_token"

# AI Model API Keys
OPENAI_API_KEY = "sk-your_openai_key"
GEMINI_API_KEY = "your_gemini_key"
OPENROUTER_API_KEY = "or-your_openrouter_key"
```

### 3. Start the System

```bash
# Start both Discord bot and web dashboard
python start_bot.py
```

The system will start:
- **Discord Bot**: Connects to Discord
- **Web Dashboard**: Available at http://localhost:5000
- **Demo Login**: username=`demo`, password=`demo`

## 📱 Usage

### Discord Commands

#### Model Management
- `!model` - Show your current model or set a new one
- `!models` - List all available AI models
- `!modelinfo <model>` - Get detailed information about a model
- `!modelstats` - Show model usage statistics (admin only)
- `!modelhealth` - Run health check on all models (admin only)

#### Chat Commands
- `!chat <message>` - Chat with AI using your preferred model
- `!reset` - Clear conversation memory
- `!persona <prompt>` - Set global behavior (owner only)

#### Music Commands
- `!play <song>` - Play music
- `!pause`, `!resume`, `!stop` - Control playback
- `!volume [0-100]` - Set volume

### Web Dashboard

1. **Login**: Use demo credentials or create your account
2. **Model Selection**: Choose from available models
3. **Statistics**: View usage and performance data
4. **Model Comparison**: Test different models side-by-side
5. **Health Monitoring**: Check model availability

## 🏗️ Architecture

### Model Manager (`model_manager.py`)
- Centralized model registry and management
- User preference storage
- Automatic failover and health monitoring
- Usage statistics and cost tracking

### Web Server (`web_server.py`)
- Flask-based dashboard
- REST API for model management
- User authentication and preferences
- Real-time statistics

### Discord Bot (`main.py`)
- Enhanced with model management commands
- Integrated with model manager
- Per-user model preferences
- Status monitoring

## 🔧 Configuration

### Model Configuration
Models are defined in `model_manager.py`. You can:
- Add new models
- Modify existing model settings
- Set default models
- Configure fallback chains

### User Preferences
User preferences are stored in `user_preferences.json`:
- Preferred model per user
- Fallback model chains
- Custom settings per model

### API Keys
Configure API keys in `config.py`:
- OpenAI API key for GPT models
- Google AI key for Gemini models
- OpenRouter key for additional models
- Anthropic key for Claude models (when implemented)

## 📊 Model Information

### Available Models

| Model | Provider | Max Tokens | Cost/1K | Features |
|-------|----------|------------|----------|----------|
| GPT-4o | OpenAI | 4,096 | $0.030 | Images, Functions |
| GPT-4o-mini | OpenAI | 4,096 | $0.00015 | Images, Functions |
| GPT-3.5-turbo | OpenAI | 4,096 | $0.0005 | Functions |
| Gemini 2.0 Flash | Google | 8,192 | $0.000075 | Images, Functions |
| Gemini 1.5 Flash | Google | 32,768 | $0.000075 | Images |
| Gemini Pro | Google | 30,720 | $0.0005 | Images |
| Claude 3.5 Sonnet | Anthropic | 8,192 | $0.003 | Images, Functions |
| Claude 3 Haiku | Anthropic | 4,096 | $0.00025 | Images |

### Model Status
- **🟢 Online**: Model is available and responding
- **🟡 Degraded**: Model has some issues but still working
- **🔴 Offline**: Model is unavailable
- **⚪ Unknown**: Status not yet determined

## 🔒 Security

### Authentication
- Web dashboard uses session-based authentication
- Discord commands respect user permissions
- Admin commands require administrator privileges

### API Key Management
- Store API keys securely in `config.py`
- Never commit API keys to version control
- Use environment variables for production

## 🚀 Deployment

### Local Development
```bash
python start_bot.py
```

### Production Deployment
1. Set up proper database for user preferences
2. Use environment variables for API keys
3. Configure reverse proxy for web dashboard
4. Set up SSL certificates
5. Use process manager (PM2, systemd, etc.)

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "start_bot.py"]
```

## 🛠️ Development

### Adding New Models
1. Add model definition to `model_manager.py`
2. Implement API handler in `api_handler.py`
3. Update dashboard UI if needed
4. Test model integration

### Extending Features
- Add new Discord commands
- Extend web dashboard functionality
- Implement additional AI providers
- Add more model comparison features

## 📈 Monitoring

### Health Checks
- Automatic model availability testing
- Response time monitoring
- Error rate tracking
- Usage statistics

### Logging
- Model usage logs
- Error tracking
- Performance metrics
- User activity

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues

**Bot not responding:**
- Check API keys in `config.py`
- Verify Discord bot permissions
- Check model status with `!modelhealth`

**Web dashboard not loading:**
- Ensure port 5000 is available
- Check Flask server logs
- Verify all dependencies are installed

**Model selection not working:**
- Check user preferences file
- Verify model IDs are correct
- Run health check on models

### Getting Help
- Check the Discord server for support
- Review the documentation
- Open an issue on GitHub
- Contact the development team

## 🔮 Future Features

- **Voice Integration**: Voice-to-text and text-to-speech
- **Image Generation**: Built-in image generation
- **Custom Models**: Support for local/private models
- **Advanced Analytics**: Detailed usage analytics
- **Multi-Language Support**: Internationalization
- **Mobile App**: Mobile dashboard companion

---

**Built by Interact Developments Inc.**  
Website: https://interactdevelopments.me/  
Discord: [Join our server](https://discord.gg/interactdev)

