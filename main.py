import discord
import asyncio
import time
from discord.ext import commands
import api_handler
import music
from model_manager import model_manager
from subscription_manager import subscription_manager, SubscriptionTier
from config import DISCORD_TOKEN
from config import GLOBAL_PERSONA
from config import OWNER_USER_ID
from config import FFMPEG_PATH
from config import BOT_STATUS, ACTIVITY_TYPE, ACTIVITY_NAME, ACTIVITY_STREAM_URL

# Set console encoding to UTF-8 to handle Unicode characters
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# -- Bot Setup --
intents = discord.Intents.default()
intents.message_content = True  # Now enabled in Discord Developer Portal
intents.members = True  # Required for member join/leave and moderation actions
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # Disable default help

# -- Bot State --
# This dictionary will store the mode for each server (guild)
# True for 18+, False for Under 18
server_modes = {}
user_modes = {}  # Track individual user modes for DMs
# Per-server auto chat channel mapping: guild_id -> channel_id
auto_chat_channels = {}
# Welcome settings per server: guild_id -> { 'channel_id': int, 'welcome_message': str }
welcome_settings = {}
# Conversation memory per channel/DM: channel_id -> list of turns [{role, content}]
conversations = {}
# Global persona/system prompt applied across all channels and DMs
global_persona = GLOBAL_PERSONA if (GLOBAL_PERSONA and GLOBAL_PERSONA.strip()) else None

MAX_TURNS = 20  # cap memory per channel to avoid unbounded growth

# -- Welcome Settings Persistence --
WELCOME_SETTINGS_FILE = "welcome_config.json"

def _load_welcome_settings():
    global welcome_settings
    try:
        import json, os
        if os.path.exists(WELCOME_SETTINGS_FILE):
            with open(WELCOME_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # keys are strings in json; keep as strings for guild_id
                welcome_settings = {int(k): v for k, v in data.items()}
    except Exception as e:
        print(f"Failed to load welcome settings: {e}")

def _save_welcome_settings():
    try:
        import json
        with open(WELCOME_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({str(k): v for k, v in welcome_settings.items()}, f, indent=2)
    except Exception as e:
        print(f"Failed to save welcome settings: {e}")

# -- NSFW Self-Attestation Persistence --
NSFW_ATTEST_FILE = "nsfw_attestations.json"
nsfw_attested_users: set[str] = set()

def _load_nsfw_attestations():
    global nsfw_attested_users
    try:
        import json, os
        if os.path.exists(NSFW_ATTEST_FILE):
            with open(NSFW_ATTEST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Store as set of string user IDs
                nsfw_attested_users = set(str(uid) for uid in (data or []))
    except Exception as e:
        print(f"Failed to load NSFW attestations: {e}")

def _save_nsfw_attestations():
    try:
        import json
        with open(NSFW_ATTEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(nsfw_attested_users)), f, indent=2)
    except Exception as e:
        print(f"Failed to save NSFW attestations: {e}")

def add_company_footer(embed: discord.Embed) -> discord.Embed:
    """Add the company footer to any embed."""
    embed.set_footer(text="Built by Interact Developments Inc. • https://interactdevelopments.me/")
    return embed

def _context_id_from_interaction(interaction: discord.Interaction):
    return interaction.channel.id if interaction.channel else None

def _context_id_from_message(message: discord.Message):
    return message.channel.id

def _status_from_config():
    value = (BOT_STATUS or "online").strip().lower()
    if value == "idle":
        return discord.Status.idle
    if value == "dnd":
        return discord.Status.do_not_disturb
    if value == "invisible":
        return discord.Status.invisible
    return discord.Status.online

def _activity_from_config():
    activity_type = (ACTIVITY_TYPE or "none").strip().lower()
    name = ACTIVITY_NAME or ""
    if activity_type == "playing":
        return discord.Game(name=name)
    if activity_type == "listening":
        return discord.Activity(type=discord.ActivityType.listening, name=name)
    if activity_type == "watching":
        return discord.Activity(type=discord.ActivityType.watching, name=name)
    if activity_type == "competing":
        return discord.Activity(type=discord.ActivityType.competing, name=name)
    if activity_type == "streaming":
        url = ACTIVITY_STREAM_URL or "https://twitch.tv/"
        return discord.Streaming(name=name, url=url)
    return None

@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    # Record start time for uptime calculation
    bot.start_time = time.time()
    
    print(f'{bot.user.name} has connected to Discord!')
    print(f'Bot ID: {bot.user.id}')
    print('Servers:')
    for guild in bot.guilds:
        try:
            print(f'- {guild.name} (id: {guild.id})')
        except UnicodeEncodeError:
            # Handle guild names with special characters
            safe_name = guild.name.encode('ascii', 'replace').decode('ascii')
            print(f'- {safe_name} (id: {guild.id})')
        # Default to "Under 18" mode for all servers on startup
        server_modes[guild.id] = False 
    
    # Set bot activity status - multiple attempts to ensure it works
    try:
        activity = _activity_from_config()
        status = _status_from_config()
        await bot.change_presence(activity=activity, status=status)
        print(f"✅ Bot status set to: {status}")
        
        # Wait and try again to ensure status is set
        await asyncio.sleep(2)
        await bot.change_presence(activity=activity, status=status)
        print("✅ Bot status confirmed")
        
    except Exception as e:
        print(f"❌ Error setting bot status: {e}")
    
    # Sync slash commands with better error handling
    try:
        print("Syncing slash commands...")
        synced = await bot.tree.sync()
        print(f'✅ Successfully synced {len(synced)} command(s) globally')
        for cmd in synced:
            print(f"  - {cmd.name}: {cmd.description}")
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
        print("Trying to sync commands per guild...")
        try:
            for guild in bot.guilds:
                synced = await bot.tree.sync(guild=guild)
                print(f'Synced {len(synced)} command(s) for {guild.name}')
        except Exception as guild_error:
            print(f'Failed to sync guild commands: {guild_error}')
    
    # Load persisted configs
    _load_welcome_settings()
    _load_nsfw_attestations()

    print('Bot is ready to chat! You can:')
    print('- Mention the bot (@botname) to chat')
    print('- Use /chat slash command')
    print('- Use !togglemode to switch between SFW/NSFW modes')
    print('- Use !join !play <spotify url or search> !pause !resume !stop !leave')
    print('- Use !image <prompt> or /image <prompt> to generate an image')
    print('- Use !persona <prompt> to set a global behavior/system prompt (owner only)')


@bot.command(name='sync', help='Sync slash commands (Admin only)')
@commands.has_permissions(administrator=True)
async def sync_commands(ctx):
    """Manually sync slash commands."""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f'✅ Synced {len(synced)} slash command(s)')
    except Exception as e:
        await ctx.send(f'❌ Failed to sync: {e}')

@bot.command(name='reset', help='Reset conversation memory for this channel')
async def reset_memory(ctx):
    cid = ctx.channel.id
    conversations.pop(cid, None)
    await ctx.send('🧹 Conversation memory cleared for this channel.')

@bot.command(name='persona', help='Set a global behavior/system prompt (owner only)')
async def set_persona(ctx, *, prompt: str = None):
    # If hardcoded persona is set, disallow runtime changes
    if GLOBAL_PERSONA and GLOBAL_PERSONA.strip():
        return await ctx.send('🔒 Global persona is locked in config and cannot be changed here.')
    # Enforce owner-only access if configured
    if OWNER_USER_ID and OWNER_USER_ID > 0 and ctx.author.id != OWNER_USER_ID:
        return await ctx.send('❌ Only the bot owner can set the persona in this server.')
    # Fallback: if no OWNER_USER_ID, restrict to admins
    if not (OWNER_USER_ID and OWNER_USER_ID > 0):
        perms = ctx.author.guild_permissions if ctx.guild else None
        if not (perms and perms.administrator):
            return await ctx.send('❌ You must be an administrator to set the persona.')
    if not prompt or not prompt.strip():
        return await ctx.send('Usage: !persona <prompt>')
    global global_persona
    global_persona = prompt.strip()
    await ctx.send('✅ Global persona/system prompt set for all channels and DMs.')

# -------- NSFW Self-Attestation --------
@bot.command(name='attest', help='Self-attest you are 18+ to use NSFW features')
async def attest(ctx):
    user_id = str(ctx.author.id)
    if user_id in nsfw_attested_users:
        return await ctx.send('✅ You have already self-attested for 18+ content.')
    nsfw_attested_users.add(user_id)
    _save_nsfw_attestations()
    await ctx.send('✅ Self-attestation recorded. You can use NSFW features in Discord-marked NSFW channels.')

@bot.tree.command(name="attest", description="Self-attest you are 18+ to use NSFW features")
async def slash_attest(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in nsfw_attested_users:
        return await interaction.response.send_message('✅ You have already self-attested for 18+ content.', ephemeral=True)
    nsfw_attested_users.add(user_id)
    _save_nsfw_attestations()
    await interaction.response.send_message('✅ Self-attestation recorded. You can use NSFW features in Discord-marked NSFW channels.', ephemeral=True)

# -------- Model Management Commands --------
@bot.command(name='model', help='Set your preferred AI model')
async def set_model(ctx, *, model_name: str = None):
    """Set user's preferred AI model"""
    if not model_name:
        # Show current model and available options
        user_id = str(ctx.author.id)
        current_model_id = model_manager.get_user_preference(user_id)
        current_model = model_manager.get_model_info(current_model_id)
        
        embed = discord.Embed(
            title="🤖 Current AI Model",
            description=f"**{current_model.name if current_model else 'Unknown'}**",
            color=0x0099ff
        )
        
        if current_model:
            embed.add_field(name="Provider", value=current_model.provider.value.title(), inline=True)
            embed.add_field(name="Status", value=f"🟢 {current_model.status.value.title()}", inline=True)
            embed.add_field(name="Max Tokens", value=f"{current_model.max_tokens:,}", inline=True)
            embed.add_field(name="Cost per 1K tokens", value=f"${current_model.cost_per_1k_tokens:.4f}", inline=True)
            embed.add_field(name="Usage Count", value=str(current_model.usage_count), inline=True)
            embed.add_field(name="Avg Response Time", value=f"{current_model.avg_response_time:.2f}s", inline=True)
        
        embed.add_field(
            name="Available Models", 
            value="Use `!models` to see all available models\nUse `!model <model_name>` to change your model",
            inline=False
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
    
    # Set new model
    user_id = str(ctx.author.id)
    success = model_manager.set_user_preference(user_id, model_name)
    
    if success:
        # Get the actual model ID that was set
        actual_model_id = model_manager.find_model_by_name(model_name)
        model_info = model_manager.get_model_info(actual_model_id)
        embed = discord.Embed(
            title="✅ Model Updated",
            description=f"Your preferred model is now **{model_info.name}**",
            color=0x00ff00
        )
        embed.add_field(name="Provider", value=model_info.provider.value.title(), inline=True)
        embed.add_field(name="Description", value=model_info.description, inline=False)
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Invalid Model",
            description=f"Model '{model_name}' not found. Use `!models` to see available models.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)

@bot.command(name='models', help='List all available AI models')
async def list_models(ctx):
    """List all available AI models with their status"""
    embed = discord.Embed(
        title="🤖 Available AI Models",
        description="Here are all the available AI models organized by content type:",
        color=0x0099ff
    )
    
    # Define SFW and NSFW models based on our implementation
    sfw_models = [
        "google/gemma-3n-e2b-it:free",
        "nvidia/nemotron-nano-9b-v2:free"
    ]
    
    nsfw_models = [
        "google/gemma-3n-e2b-it:free",
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
    ]
    
    # Get SFW models
    sfw_list = []
    for model_id in sfw_models:
        if model_id in model_manager.models:
            model = model_manager.models[model_id]
            status_emoji = {
                'online': '🟢',
                'offline': '🔴', 
                'degraded': '🟡',
                'unknown': '⚪'
            }.get(model.status.value, '⚪')
            
            cost_info = "🆓 FREE" if model.cost_per_1k_tokens == 0 else f"${model.cost_per_1k_tokens:.4f}/1k tokens"
            sfw_list.append(f"{status_emoji} **{model.name}** - {cost_info}")
    
    # Get NSFW models
    nsfw_list = []
    for model_id in nsfw_models:
        if model_id in model_manager.models:
            model = model_manager.models[model_id]
            status_emoji = {
                'online': '🟢',
                'offline': '🔴', 
                'degraded': '🟡',
                'unknown': '⚪'
            }.get(model.status.value, '⚪')
            
            cost_info = "🆓 FREE" if model.cost_per_1k_tokens == 0 else f"${model.cost_per_1k_tokens:.4f}/1k tokens"
            nsfw_list.append(f"{status_emoji} **{model.name}** - {cost_info}")
    
    # Add SFW section
    embed.add_field(
        name="🛡️ SFW Models (Safe for Work)",
        value="\n".join(sfw_list) if sfw_list else "No SFW models available",
        inline=False
    )
    
    # Add NSFW section
    embed.add_field(
        name="🔞 NSFW Models (18+ Content)",
        value="\n".join(nsfw_list) if nsfw_list else "No NSFW models available",
        inline=False
    )
    
    # Add model details
    embed.add_field(
        name="📊 Model Details",
        value="• **Google Gemma 3n 2B**: Fast, efficient 2B parameter model\n• **NVIDIA Nemotron Nano 9B**: High-quality 9B parameter model\n• **Dolphin Mistral 24B**: Advanced 24B parameter model for complex tasks",
        inline=False
    )
    
    embed.add_field(
        name="💡 Usage",
        value="• Use `!model <model_name>` to set your preferred model\n• Use `!model` to see your current model\n• Use `!modelinfo <model_name>` for detailed info\n• Use `!togglemode` to switch between SFW/NSFW modes",
        inline=False
    )
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='modelinfo', help='Get detailed information about a specific model')
async def model_info(ctx, *, model_name: str = None):
    """Get detailed information about a specific model"""
    if not model_name:
        await ctx.send("Usage: `!modelinfo <model_name>`")
        return
    
    # Use the improved model lookup
    model_id = model_manager.find_model_by_name(model_name)
    if not model_id:
        embed = discord.Embed(
            title="❌ Model Not Found",
            description=f"Model '{model_name}' not found. Use `!models` to see available models.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
    
    model = model_manager.get_model_info(model_id)
    
    if not model:
        embed = discord.Embed(
            title="❌ Model Not Found",
            description=f"Model '{model_name}' not found. Use `!models` to see available models.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
    
    # Status color
    status_colors = {
        'online': 0x00ff00,
        'offline': 0xff0000,
        'degraded': 0xff9900,
        'unknown': 0x666666
    }
    
    embed = discord.Embed(
        title=f"🤖 {model.name}",
        description=model.description,
        color=status_colors.get(model.status.value, 0x666666)
    )
    
    embed.add_field(name="Provider", value=model.provider.value.title(), inline=True)
    embed.add_field(name="Status", value=f"🟢 {model.status.value.title()}", inline=True)
    embed.add_field(name="Max Tokens", value=f"{model.max_tokens:,}", inline=True)
    embed.add_field(name="Cost per 1K tokens", value=f"${model.cost_per_1k_tokens:.4f}", inline=True)
    embed.add_field(name="Usage Count", value=str(model.usage_count), inline=True)
    embed.add_field(name="Error Count", value=str(model.error_count), inline=True)
    embed.add_field(name="Avg Response Time", value=f"{model.avg_response_time:.2f}s", inline=True)
    embed.add_field(name="Last Used", value=f"<t:{int(model.last_used)}:R>" if model.last_used else "Never", inline=True)
    
    # Features
    features = []
    if model.supports_images:
        features.append("🖼️ Images")
    if model.supports_functions:
        features.append("⚙️ Functions")
    if features:
        embed.add_field(name="Features", value=" ".join(features), inline=False)
    
    embed.add_field(
        name="Set as Preferred",
        value=f"Use `!model {model.name}` to set this as your preferred model",
        inline=False
    )
    
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='modelstats', help='Show model usage statistics (admin only)')
@commands.has_permissions(administrator=True)
async def model_stats(ctx):
    """Show comprehensive model statistics"""
    stats = model_manager.get_model_stats()
    
    embed = discord.Embed(
        title="📊 Model Statistics",
        description="Comprehensive statistics for all AI models",
        color=0x0099ff
    )
    
    embed.add_field(name="Total Models", value=str(stats['total_models']), inline=True)
    embed.add_field(name="Online Models", value=str(stats['online_models']), inline=True)
    embed.add_field(name="Offline Models", value=str(stats['offline_models']), inline=True)
    embed.add_field(name="Degraded Models", value=str(stats['degraded_models']), inline=True)
    
    # Top 3 most used models
    top_models = sorted(
        stats['models'].items(), 
        key=lambda x: x[1]['usage_count'], 
        reverse=True
    )[:3]
    
    if top_models:
        top_models_text = []
        for i, (model_id, model_stats) in enumerate(top_models, 1):
            top_models_text.append(f"{i}. **{model_stats['name']}** - {model_stats['usage_count']} uses")
        
        embed.add_field(
            name="🏆 Most Used Models",
            value="\n".join(top_models_text),
            inline=False
        )
    
    embed.add_field(
        name="🔧 Management",
        value="• Use `!modelhealth` to run a health check\n• Use `!models` to see all models\n• Dashboard: http://localhost:5000",
        inline=False
    )
    
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='modelhealth', help='Run health check on all models (admin only)')
@commands.has_permissions(administrator=True)
async def model_health(ctx):
    """Run health check on all models"""
    embed = discord.Embed(
        title="🏥 Running Model Health Check",
        description="Checking all AI models... This may take a moment.",
        color=0xffff00
    )
    embed = add_company_footer(embed)
    message = await ctx.send(embed=embed)
    
    try:
        await model_manager.health_check()
        
        # Get updated stats
        stats = model_manager.get_model_stats()
        
        embed = discord.Embed(
            title="✅ Health Check Complete",
            description="All models have been checked for availability.",
            color=0x00ff00
        )
        
        embed.add_field(name="Online Models", value=str(stats['online_models']), inline=True)
        embed.add_field(name="Offline Models", value=str(stats['offline_models']), inline=True)
        embed.add_field(name="Degraded Models", value=str(stats['degraded_models']), inline=True)
        
        # Show any offline models
        offline_models = [
            model_stats['name'] 
            for model_stats in stats['models'].values() 
            if model_stats['status'] == 'offline'
        ]
        
        if offline_models:
            embed.add_field(
                name="⚠️ Offline Models",
                value=", ".join(offline_models),
                inline=False
            )
        
        embed = add_company_footer(embed)
        await message.edit(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Health Check Failed",
            description=f"Error during health check: {str(e)}",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await message.edit(embed=embed)

# -------- Subscription Commands --------
@bot.command(name='subscribe', help='View subscription plans and upgrade options')
async def subscribe_info(ctx):
    """Show subscription information and plans"""
    user_id = str(ctx.author.id)
    current_tier = subscription_manager.get_user_tier(user_id)
    usage_summary = subscription_manager.get_usage_summary(user_id)
    
    embed = discord.Embed(
        title="💎 Subscription Plans",
        description="Choose the perfect plan for your AI needs!",
        color=0x0099ff
    )
    
    # Current status
    if current_tier == SubscriptionTier.FREE:
        status_emoji = "🆓"
    elif current_tier == SubscriptionTier.PREMIUM:
        status_emoji = "💎"
    elif current_tier == SubscriptionTier.PRO:
        status_emoji = "👑"
    elif current_tier == SubscriptionTier.ULTRA_PREMIUM:
        status_emoji = "🔥"
    else:
        status_emoji = "🆓"
    
    embed.add_field(
        name="Your Current Plan",
        value=f"{status_emoji} **{current_tier.value.replace('_', ' ').title()}**\n"
              f"Daily Messages: {usage_summary['daily_messages_used']}/{usage_summary['daily_limit']}\n"
              f"Premium Models: {'✅ Available' if usage_summary['premium_models_available'] else '❌ Not Available'}",
        inline=False
    )
    
    # Free plan
    embed.add_field(
        name="🆓 Free Plan",
        value="• 150 messages per day\n"
              "• Access to standard models\n"
              "• Basic AI assistance\n"
              "• **$0/month**",
        inline=True
    )
    
    # Premium plan
    embed.add_field(
        name="💎 Premium Plan",
        value="• Unlimited messages\n"
              "• Access to premium models\n"
              "• Mistral Large & Llama 3.1 70B\n"
              "• **$9.99/month**",
        inline=True
    )
    
    # Pro plan
    embed.add_field(
        name="👑 Pro Plan",
        value="• Everything in Premium\n"
              "• Priority support\n"
              "• Advanced features\n"
              "• **$19.99/month**",
        inline=True
    )
    
    # Ultra-Premium plan
    embed.add_field(
        name="🔥 Ultra-Premium Plan",
        value="• Everything in Pro\n"
              "• **Grok AI** - Truly uncensored AI\n"
              "• No content restrictions\n"
              "• **$99.90 per 3 months**",
        inline=True
    )
    
    embed.add_field(
        name="🚀 Premium Models",
        value="• **Mistral Large** - Advanced reasoning\n"
              "• **Llama 3.1 70B** - Meta's flagship model\n"
              "• **Grok AI** - Uncensored AI access (Ultra-Premium only)",
        inline=False
    )
    
    embed.add_field(
        name="💳 How to Subscribe",
        value="Use `/upgrade` to start your subscription!\n"
              "Secure payment processing via Stripe",
        inline=False
    )
    
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='usage', help='Check your current usage and limits')
async def usage_info(ctx):
    """Show user's current usage statistics"""
    user_id = str(ctx.author.id)
    usage_summary = subscription_manager.get_usage_summary(user_id)
    current_tier = subscription_manager.get_user_tier(user_id)
    
    embed = discord.Embed(
        title="📊 Your Usage Statistics",
        description=f"Current Plan: **{current_tier.value.title()}**",
        color=0x0099ff
    )
    
    # Daily usage
    daily_limit = usage_summary['daily_limit']
    daily_used = usage_summary['daily_messages_used']
    
    if daily_limit == "Unlimited":
        usage_text = f"**{daily_used}** messages used today\n✅ Unlimited access"
        usage_color = 0x00ff00
    else:
        remaining = int(daily_limit) - daily_used
        usage_percentage = (daily_used / int(daily_limit)) * 100
        
        if usage_percentage >= 90:
            usage_color = 0xff0000
        elif usage_percentage >= 70:
            usage_color = 0xff9900
        else:
            usage_color = 0x00ff00
        
        usage_text = f"**{daily_used}/{daily_limit}** messages used\n**{remaining}** remaining"
    
    embed.add_field(
        name="📈 Daily Usage",
        value=usage_text,
        inline=True
    )
    
    # Premium usage
    premium_used = usage_summary['daily_premium_messages_used']
    if usage_summary['premium_models_available']:
        premium_text = f"**{premium_used}** premium messages\n✅ Premium models available"
    else:
        premium_text = f"**{premium_used}** premium messages\n❌ Premium subscription required"
    
    embed.add_field(
        name="💎 Premium Usage",
        value=premium_text,
        inline=True
    )
    
    # Subscription info
    if usage_summary['subscription_status'] != 'none':
        end_date = usage_summary['subscription_end_date']
        if end_date:
            from datetime import datetime
            end_datetime = datetime.fromtimestamp(end_date)
            end_str = end_datetime.strftime("%Y-%m-%d")
            embed.add_field(
                name="📅 Subscription",
                value=f"Status: **{usage_summary['subscription_status'].title()}**\n"
                      f"Expires: **{end_str}**",
                inline=False
            )
    
    # Upgrade prompt for free users
    if current_tier == SubscriptionTier.FREE:
        embed.add_field(
            name="🚀 Upgrade Now",
            value="Get unlimited access to premium models!\nUse `/subscribe` to view plans",
            inline=False
        )
    
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='upgrade', help='Upgrade to premium subscription')
async def upgrade_subscription(ctx):
    """Show upgrade options and payment links"""
    user_id = str(ctx.author.id)
    current_tier = subscription_manager.get_user_tier(user_id)
    
    if current_tier in [SubscriptionTier.PREMIUM, SubscriptionTier.PRO, SubscriptionTier.ULTRA_PREMIUM]:
        embed = discord.Embed(
            title="✅ Already Subscribed",
            description=f"You already have a **{current_tier.value.replace('_', ' ').title()}** subscription!",
            color=0x00ff00
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🚀 Upgrade to Premium",
        description="Get unlimited access to the most powerful AI models!",
        color=0x0099ff
    )
    
    embed.add_field(
        name="💎 Premium Benefits",
        value="• **Unlimited messages** (vs 150/day free)\n"
              "• **Mistral Large** - Advanced reasoning\n"
              "• **Llama 3.1 70B** - Meta's flagship model\n"
              "• **Mistral Large 2** - Latest capabilities\n"
              "• **Priority support**",
        inline=False
    )
    
    embed.add_field(
        name="🔥 Ultra-Premium Benefits",
        value="• **Grok AI** - Truly uncensored AI\n"
              "• **No content restrictions**\n"
              "• **All premium models included**\n"
              "• **Best for power users**",
        inline=False
    )
    
    embed.add_field(
        name="💰 Pricing",
        value="**Premium Plan: $9.99/month**\n"
              "**Pro Plan: $19.99/month**\n"
              "**Ultra-Premium: $99.90 per 3 months ($33.30/month)**\n\n"
              "Cancel anytime, no commitments!",
        inline=False
    )
    
    embed.add_field(
        name="💳 Payment Options",
        value="🔗 **Stripe Checkout** (Coming Soon)\n"
              "💳 Credit/Debit Cards\n"
              "🏦 Bank Transfers\n"
              "📱 Mobile Payments",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Security & Privacy",
        value="• Secure payment processing\n"
              "• No data collection\n"
              "• Cancel anytime\n"
              "• 30-day money-back guarantee",
        inline=False
    )
    
    embed.add_field(
        name="📞 Contact Support",
        value="Need help? Contact us at:\n"
              "📧 support@interactdevelopments.me\n"
              "🌐 https://interactdevelopments.me/",
        inline=False
    )
    
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='cancel', help='Cancel your subscription')
async def cancel_subscription(ctx):
    """Cancel user's subscription"""
    user_id = str(ctx.author.id)
    subscription = subscription_manager.get_user_subscription(user_id)
    
    if not subscription or subscription.status.value != 'active':
        embed = discord.Embed(
            title="❌ No Active Subscription",
            description="You don't have an active subscription to cancel.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="⚠️ Cancel Subscription",
        description=f"Are you sure you want to cancel your **{subscription.tier.value.title()}** subscription?",
        color=0xff9900
    )
    
    embed.add_field(
        name="What happens when you cancel:",
        value="• Your subscription will remain active until the end of your billing period\n"
              "• You'll lose access to premium models\n"
              "• You'll be limited to 150 messages per day\n"
              "• You can resubscribe anytime",
        inline=False
    )
    
    embed.add_field(
        name="Contact Support",
        value="To cancel your subscription, please contact:\n"
              "📧 support@interactdevelopments.me\n"
              "🌐 https://interactdevelopments.me/",
        inline=False
    )
    
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='subscriptionstats', help='Show subscription statistics (admin only)')
@commands.has_permissions(administrator=True)
async def subscription_stats(ctx):
    """Show subscription statistics for administrators"""
    stats = subscription_manager.get_subscription_stats()
    
    embed = discord.Embed(
        title="📊 Subscription Statistics",
        description="Overview of user subscriptions and usage",
        color=0x0099ff
    )
    
    embed.add_field(name="Total Users", value=str(stats['total_users']), inline=True)
    embed.add_field(name="Active Subscriptions", value=str(stats['active_subscriptions']), inline=True)
    embed.add_field(name="Free Users", value=str(stats['free_users']), inline=True)
    
    embed.add_field(name="Premium Users", value=str(stats['premium_users']), inline=True)
    embed.add_field(name="Pro Users", value=str(stats['pro_users']), inline=True)
    embed.add_field(name="Expired Subscriptions", value=str(stats['expired_subscriptions']), inline=True)
    
    # Calculate conversion rate
    if stats['total_users'] > 0:
        conversion_rate = (stats['active_subscriptions'] / stats['total_users']) * 100
        embed.add_field(
            name="Conversion Rate",
            value=f"{conversion_rate:.1f}%",
            inline=True
        )
    
    embed.add_field(
        name="Management",
        value="• Use `/cleanup` to clean expired subscriptions\n"
              "• Use `/usage` to check individual user usage",
        inline=False
    )
    
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='cleanup', help='Clean up expired subscriptions (admin only)')
@commands.has_permissions(administrator=True)
async def cleanup_subscriptions(ctx):
    """Clean up expired subscriptions"""
    embed = discord.Embed(
        title="🧹 Cleaning Up Subscriptions",
        description="Removing expired subscriptions...",
        color=0xffff00
    )
    embed = add_company_footer(embed)
    message = await ctx.send(embed=embed)
    
    try:
        subscription_manager.cleanup_expired_subscriptions()
        
        embed = discord.Embed(
            title="✅ Cleanup Complete",
            description="Expired subscriptions have been cleaned up successfully.",
            color=0x00ff00
        )
        embed = add_company_footer(embed)
        await message.edit(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Cleanup Failed",
            description=f"Error during cleanup: {str(e)}",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await message.edit(embed=embed)

# -------- Moderation Commands --------
@bot.command(name='kick', help='Kick a member (Admin only)')
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason: str = None):
    try:
        await member.kick(reason=reason or f"Kicked by {ctx.author}")
        await ctx.send(f"✅ Kicked {member.mention}. Reason: {reason or 'No reason provided'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to kick: {e}")

@bot.command(name='ban', help='Ban a member (Admin only)')
@commands.has_permissions(ban_members=True)
async def ban_member(ctx, member: discord.Member, *, reason: str = None):
    try:
        await member.ban(reason=reason or f"Banned by {ctx.author}")
        await ctx.send(f"✅ Banned {member.mention}. Reason: {reason or 'No reason provided'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to ban: {e}")

@bot.command(name='unban', help='Unban a user by name#discriminator or ID (Admin only)')
@commands.has_permissions(ban_members=True)
async def unban_member(ctx, *, user: str):
    try:
        banned_entries = await ctx.guild.bans()
        # Try by ID first
        target = None
        try:
            uid = int(user)
            for ban in banned_entries:
                if ban.user.id == uid:
                    target = ban.user
                    break
        except Exception:
            # Try by name#discriminator
            name, _, discrim = user.partition('#')
            for ban in banned_entries:
                if ban.user.name == name and str(ban.user.discriminator) == discrim:
                    target = ban.user
                    break
        if not target:
            return await ctx.send("❌ User not found in ban list.")
        await ctx.guild.unban(target)
        await ctx.send(f"✅ Unbanned {target.mention if hasattr(target,'mention') else target}")
    except Exception as e:
        await ctx.send(f"❌ Failed to unban: {e}")

@bot.command(name='timeout', help='Timeout a member for N minutes (Admin only)')
@commands.has_permissions(moderate_members=True)
async def timeout_member(ctx, member: discord.Member, minutes: int, *, reason: str = None):
    try:
        from datetime import timedelta
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason or f"Timed out by {ctx.author}")
        await ctx.send(f"⏳ Timed out {member.mention} for {minutes} minute(s).")
    except Exception as e:
        await ctx.send(f"❌ Failed to timeout: {e}")

@bot.command(name='purge', help='Delete N recent messages (Admin only)')
@commands.has_permissions(manage_messages=True)
async def purge_messages(ctx, count: int):
    try:
        if count <= 0 or count > 200:
            return await ctx.send("❌ Count must be between 1 and 200.")
        deleted = await ctx.channel.purge(limit=count + 1)
        confirm = await ctx.send(f"🧹 Deleted {len(deleted) - 1} messages.")
        await asyncio.sleep(2)
        await confirm.delete()
    except Exception as e:
        await ctx.send(f"❌ Failed to purge: {e}")

@bot.command(name='slowmode', help='Set slowmode in seconds for current channel (Admin only)')
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    try:
        if seconds < 0 or seconds > 21600:
            return await ctx.send("❌ Slowmode must be between 0 and 21600 seconds.")
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("🚀 Slowmode disabled for this channel.")
        else:
            await ctx.send(f"🐢 Slowmode set to {seconds}s for this channel.")
    except Exception as e:
        await ctx.send(f"❌ Failed to set slowmode: {e}")

# -------- Welcome/Leave Messages --------
@bot.command(name='setwelcome', help='Set welcome channel and message (Admin only)')
@commands.has_permissions(manage_guild=True)
async def set_welcome(ctx, channel: discord.TextChannel, *, message: str):
    guild_id = ctx.guild.id
    welcome_settings[guild_id] = {
        'channel_id': channel.id,
        'welcome_message': message
    }
    _save_welcome_settings()
    await ctx.send(f"✅ Welcome channel set to {channel.mention}.")

@bot.command(name='showwelcome', help='Show current welcome settings')
@commands.has_permissions(manage_guild=True)
async def show_welcome(ctx):
    cfg = welcome_settings.get(ctx.guild.id)
    if not cfg:
        return await ctx.send("ℹ️ No welcome settings configured. Use `!setwelcome #channel Welcome {user}`")
    ch = ctx.guild.get_channel(cfg['channel_id'])
    await ctx.send(f"📣 Welcome channel: {ch.mention if ch else '#deleted-channel'}\nMessage: {cfg['welcome_message']}")

@bot.command(name='setwelleave', help='Set leave message (Admin only)')
@commands.has_permissions(manage_guild=True)
async def set_leave_message(ctx, *, message: str):
    guild_id = ctx.guild.id
    cfg = welcome_settings.get(guild_id) or {}
    cfg['leave_message'] = message
    welcome_settings[guild_id] = cfg
    _save_welcome_settings()
    await ctx.send("✅ Leave message updated.")

@bot.event
async def on_member_join(member: discord.Member):
    cfg = welcome_settings.get(member.guild.id)
    if not cfg:
        return
    channel = member.guild.get_channel(cfg.get('channel_id'))
    if not channel:
        return
    msg = cfg.get('welcome_message') or "Welcome to the server, {user}!"
    try:
        await channel.send(msg.replace('{user}', member.mention))
    except Exception:
        pass

@bot.event
async def on_member_remove(member: discord.Member):
    cfg = welcome_settings.get(member.guild.id)
    if not cfg:
        return
    channel = member.guild.get_channel(cfg.get('channel_id'))
    if not channel:
        return
    msg = cfg.get('leave_message') or "{user} has left the server."
    try:
        await channel.send(msg.replace('{user}', member.mention))
    except Exception:
        pass

# -------- Whitelist Management (Admin/Owner) --------
@bot.command(name='whitelist', help='Manage unlimited-access whitelist (admin/owner)')
@commands.has_permissions(administrator=True)
async def whitelist_cmd(ctx, action: str = None, user: discord.User | None = None):
    """Add/remove/list whitelisted users with maxed-out subscription"""
    # Allow owner to bypass admin permission checks
    is_owner = OWNER_USER_ID and OWNER_USER_ID > 0 and ctx.author.id == OWNER_USER_ID
    if not is_owner:
        perms = ctx.author.guild_permissions if ctx.guild else None
        if not (perms and perms.administrator):
            return await ctx.send('❌ You must be an administrator or the owner to manage whitelist.')

    if action is None or action.lower() not in ("add", "remove", "list"):
        return await ctx.send('Usage: `!whitelist add @user` | `!whitelist remove @user` | `!whitelist list`')

    if action.lower() == "list":
        entries = subscription_manager.get_whitelist()
        if not entries:
            return await ctx.send('📄 Whitelist is empty.')
        # Format user mentions when possible
        lines = []
        for uid in entries:
            try:
                member = ctx.guild.get_member(int(uid)) if ctx.guild else None
                display = member.mention if member else f"<@{uid}>"
            except Exception:
                display = f"<@{uid}>"
            lines.append(f"• {display}")

        embed = discord.Embed(
            title="📝 Whitelisted Users",
            description="\n".join(lines),
            color=0x0099ff
        )
        embed = add_company_footer(embed)
        return await ctx.send(embed=embed)

    # add/remove require a target user
    if user is None:
        return await ctx.send('❌ Please mention a user. Example: `!whitelist add @user`')

    target_id = str(user.id)
    if action.lower() == "add":
        added = subscription_manager.add_to_whitelist(target_id)
        if added:
            return await ctx.send(f'✅ {user.mention} has been added to the whitelist (unlimited access).')
        else:
            return await ctx.send(f'ℹ️ {user.mention} is already whitelisted.')
    elif action.lower() == "remove":
        removed = subscription_manager.remove_from_whitelist(target_id)
        if removed:
            return await ctx.send(f'🗑️ {user.mention} has been removed from the whitelist.')
        else:
            return await ctx.send(f'ℹ️ {user.mention} was not on the whitelist.')

@bot.command(name='status', help='Check comprehensive bot status (Admin only)')
@commands.has_permissions(administrator=True)
async def bot_status(ctx):
    """Check comprehensive bot status including database, models, and system health."""
    try:
        # Create status embed
        embed = discord.Embed(
            title="🤖 Bot Status Dashboard",
            description="Comprehensive system status and health information",
            color=0x00ff00
        )
        
        # Bot Status
        bot_status_emoji = "🟢" if bot.status == discord.Status.online else "🔴"
        embed.add_field(
            name="Bot Status",
            value=f"{bot_status_emoji} {str(bot.status).title()}",
            inline=True
        )
        
        # Guild Count
        embed.add_field(
            name="Servers",
            value=f"📊 {len(bot.guilds)}",
            inline=True
        )
        
        # User Count
        total_users = sum(guild.member_count for guild in bot.guilds if guild.member_count)
        embed.add_field(
            name="Total Users",
            value=f"👥 {total_users:,}",
            inline=True
        )
        
        # Model Status
        try:
            model_stats = model_manager.get_model_stats()
            online_models = model_stats.get('online_models', 0)
            total_models = model_stats.get('total_models', 0)
            
            model_status = f"🟢 {online_models}/{total_models} Online"
            if online_models < total_models:
                offline_count = model_stats.get('offline_models', 0)
                degraded_count = model_stats.get('degraded_models', 0)
                model_status += f"\n🔴 {offline_count} Offline\n🟡 {degraded_count} Degraded"
            
            embed.add_field(
                name="AI Models",
                value=model_status,
                inline=True
            )
        except Exception as e:
            embed.add_field(
                name="AI Models",
                value=f"❌ Error: {str(e)[:50]}...",
                inline=True
            )
        
        # Database Status (if available)
        try:
            # Try to import and check database status
            from database_manager import db_manager
            db_stats = db_manager.get_database_stats()
            
            embed.add_field(
                name="Database",
                value=f"💾 {db_stats.get('total_conversations', 0)} conversations\n"
                      f"👤 {db_stats.get('unique_users', 0)} users\n"
                      f"📚 {db_stats.get('knowledge_entries', 0)} knowledge entries",
                inline=True
            )
        except ImportError:
            embed.add_field(
                name="Database",
                value="❌ Not available",
                inline=True
            )
        except Exception as e:
            embed.add_field(
                name="Database",
                value=f"⚠️ Error: {str(e)[:30]}...",
                inline=True
            )
        
        # Memory Usage
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            embed.add_field(
                name="Memory Usage",
                value=f"🧠 {memory_mb:.1f} MB",
                inline=True
            )
        except ImportError:
            embed.add_field(
                name="Memory Usage",
                value="❌ psutil not available",
                inline=True
            )
        except Exception:
            embed.add_field(
                name="Memory Usage",
                value="❌ Unable to get",
                inline=True
            )
        
        # Uptime
        try:
            import time
            uptime_seconds = time.time() - bot.start_time if hasattr(bot, 'start_time') else 0
            uptime_hours = uptime_seconds / 3600
            embed.add_field(
                name="Uptime",
                value=f"⏱️ {uptime_hours:.1f} hours",
                inline=True
            )
        except Exception:
            embed.add_field(
                name="Uptime",
                value="❌ Unable to calculate",
                inline=True
            )
        
        # Recent Activity
        try:
            recent_activity = model_stats.get('conversations_last_24h', 0) if 'model_stats' in locals() else 0
            embed.add_field(
                name="24h Activity",
                value=f"💬 {recent_activity} conversations",
                inline=True
            )
        except Exception:
            embed.add_field(
                name="24h Activity",
                value="❌ Unable to get",
                inline=True
            )
        
        # System Health
        health_status = "🟢 Healthy"
        if 'model_stats' in locals():
            offline_models = model_stats.get('offline_models', 0)
            if offline_models > 0:
                health_status = "🟡 Degraded"
            if offline_models == model_stats.get('total_models', 1):
                health_status = "🔴 Critical"
        
        embed.add_field(
            name="System Health",
            value=health_status,
            inline=True
        )
        
        # Footer
        embed.set_footer(text="Built by Interact Developments Inc. • Use !modelhealth for detailed model check")
        embed.timestamp = discord.utils.utcnow()
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Status Check Failed",
            description=f"Error retrieving bot status: {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=error_embed)

# -------- Voice/Music Commands --------
@bot.command(name='join', help='Join the voice channel you are in')
async def join(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        embed = discord.Embed(
            title="❌ Voice Channel Required",
            description="You need to be in a voice channel to use this command!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        return await ctx.send(embed=embed)
    
    channel = ctx.author.voice.channel
    if ctx.voice_client:
        if ctx.voice_client.channel.id == channel.id:
            embed = discord.Embed(
                title="🎵 Already Connected",
                description=f"I'm already in {channel.mention}!",
                color=0x00ff00
            )
            embed = add_company_footer(embed)
        return await ctx.send(embed=embed)
        await ctx.voice_client.move_to(channel)
        # Ensure bot stays deafened after moving
        await ctx.voice_client.guild.change_voice_state(channel=channel, self_deaf=True)
    else:
        voice_client = await channel.connect()
        # Permanently deafen the bot
        await voice_client.guild.change_voice_state(channel=channel, self_deaf=True)
    
    embed = discord.Embed(
        title="🎵 Connected to Voice Channel",
        description=f"Successfully joined {channel.mention}!\n🔇 Bot is deafened to avoid echo",
        color=0x00ff00
    )
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='leave', help='Leave the voice channel')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        embed = discord.Embed(
            title="👋 Left Voice Channel",
            description="Successfully disconnected from the voice channel!",
            color=0xff9900
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Not Connected",
            description="I am not currently in a voice channel!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)

@bot.command(name='play', help='Play a track by URL or search')
async def play(ctx, *, query: str = None):
    if not query or not query.strip():
        embed = discord.Embed(
            title="❌ Missing Query",
            description="Please provide a song name or URL!\n**Usage:** `!play <song name or URL>`",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        return await ctx.send(embed=embed)
    
    if not ctx.author.voice or not ctx.author.voice.channel:
        embed = discord.Embed(
            title="❌ Voice Channel Required",
            description="You need to be in a voice channel to play music!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        return await ctx.send(embed=embed)
    
    if not ctx.voice_client:
        await join(ctx)
    
    vc = ctx.voice_client
    if not vc:
        return
    
    # Create loading embed
    loading_embed = discord.Embed(
        title="🔍 Searching for Music...",
        description=f"Looking for: **{query}**",
        color=0xffff00
    )
    loading_msg = await ctx.send(embed=loading_embed)
    
    # Try Spotify first, then YouTube as fallback
    url = music.get_preview_url(query)
    source_type = "Spotify"
    
    if not url:
        print(f"No Spotify preview found for '{query}', trying YouTube...")
        url = music.get_youtube_url(query)
        source_type = "YouTube"
    
    if not url:
        error_embed = discord.Embed(
            title="❌ No Audio Found",
            description=f"Could not find any playable audio for: **{query}**\n\nTry a different search term or check the spelling!",
            color=0xff0000
        )
        error_embed = add_company_footer(error_embed)
        await loading_msg.edit(embed=error_embed)
        return
    
    try:
        # Use FFmpegPCMAudio to stream the audio
        from discord import FFmpegPCMAudio
        executable = FFMPEG_PATH if FFMPEG_PATH else 'ffmpeg'
        
        # Apply volume
        current_vol = music.get_volume()
        # Create FFmpeg options with volume control and better YouTube support
        before_options = f"-af volume={current_vol} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2"
        after_options = "-vn"
        source = FFmpegPCMAudio(url, executable=executable, before_options=before_options, options=after_options)
        
        if vc.is_playing():
            vc.stop()
        
        vc.play(source)
        
        # Set track info
        music.set_current_track(query)
        
        # Create success embed
        success_embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{query}**",
            color=0x00ff00
        )
        success_embed.add_field(name="Source", value=f"🎧 {source_type}", inline=True)
        
        # Add enhanced volume display
        percentage = int(current_vol * 100)
        if percentage == 0:
            vol_level = "🔇 Muted"
        elif percentage < 25:
            vol_level = "🔉 Low"
        elif percentage < 50:
            vol_level = "🔊 Medium"
        elif percentage < 75:
            vol_level = "🔊 High"
        else:
            vol_level = "📢 Very High"
        
        success_embed.add_field(name="Volume", value=f"{vol_level} ({percentage}%)", inline=True)
        success_embed.add_field(name="Loop", value="🔄 Off", inline=True)
        success_embed.set_footer(text=f"Requested by {ctx.author.display_name} • Built by Interact Developments Inc.", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await loading_msg.edit(embed=success_embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Playback Error",
            description=f"Failed to play the audio: {str(e)}",
            color=0xff0000
        )
        error_embed = add_company_footer(error_embed)
        await loading_msg.edit(embed=error_embed)

@bot.command(name='pause', help='Pause the current track')
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        embed = discord.Embed(
            title="⏸️ Track Paused",
            description="The current track has been paused.",
            color=0xff9900
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    elif vc and vc.is_paused():
        embed = discord.Embed(
            title="⏸️ Already Paused",
            description="The track is already paused! Use `!resume` to continue.",
            color=0xff9900
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Nothing Playing",
            description="There's no track currently playing to pause!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)

@bot.command(name='resume', help='Resume the paused track')
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        embed = discord.Embed(
            title="▶️ Track Resumed",
            description="The track has been resumed!",
            color=0x00ff00
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    elif vc and vc.is_playing():
        embed = discord.Embed(
            title="▶️ Already Playing",
            description="The track is already playing!",
            color=0x00ff00
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Nothing to Resume",
            description="There's no paused track to resume!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)

@bot.command(name='stop', help='Stop the current track')
async def stop(ctx):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        embed = discord.Embed(
            title="⏹️ Track Stopped",
            description="The current track has been stopped.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Nothing Playing",
            description="There's no track currently playing to stop!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)

@bot.command(name='volume', help='Set or check the volume (0-100)')
async def volume(ctx, vol: int = None):
    if vol is None:
        # Show current volume
        current_vol = music.get_volume()
        percentage = int(current_vol * 100)
        
        embed = discord.Embed(
            title="🔊 Current Volume",
            description=f"**{percentage}%**",
            color=0x0099ff
        )
        
        # Create a more detailed volume bar
        bar_length = 20
        filled_length = int((current_vol * bar_length))
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Add volume level indicator
        if percentage == 0:
            level = "🔇 Muted"
        elif percentage < 25:
            level = "🔉 Low"
        elif percentage < 50:
            level = "🔊 Medium"
        elif percentage < 75:
            level = "🔊 High"
        else:
            level = "📢 Very High"
        
        embed.add_field(name="Volume Level", value=level, inline=True)
        embed.add_field(name="Volume Bar", value=f"`{bar}`", inline=False)
        embed.add_field(name="Note", value="Volume changes apply to new tracks", inline=False)
        
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    else:
        # Set volume
        if vol < 0 or vol > 100:
            embed = discord.Embed(
                title="❌ Invalid Volume",
                description="Volume must be between 0 and 100!",
                color=0xff0000
            )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
        
        new_vol = music.set_volume(vol / 100.0)
        percentage = int(new_vol * 100)
        
        embed = discord.Embed(
            title="🔊 Volume Changed",
            description=f"Volume set to **{percentage}%**",
            color=0x00ff00
        )
        
        # Create volume bar
        bar_length = 20
        filled_length = int((new_vol * bar_length))
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Add volume level indicator
        if percentage == 0:
            level = "🔇 Muted"
        elif percentage < 25:
            level = "🔉 Low"
        elif percentage < 50:
            level = "🔊 Medium"
        elif percentage < 75:
            level = "🔊 High"
        else:
            level = "📢 Very High"
        
        embed.add_field(name="Volume Level", value=level, inline=True)
        embed.add_field(name="Volume Bar", value=f"`{bar}`", inline=False)
        embed.add_field(name="Note", value="Volume changes apply to new tracks", inline=False)
        
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)

@bot.command(name='loop', help='Toggle loop mode on/off')
async def loop(ctx):
    loop_status = music.toggle_loop()
    status_text = "ON" if loop_status else "OFF"
    status_color = 0x00ff00 if loop_status else 0xff0000
    status_emoji = "🔄" if loop_status else "⏹️"
    
    embed = discord.Embed(
        title=f"{status_emoji} Loop Mode",
        description=f"Loop mode is now **{status_text}**",
        color=status_color
    )
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='nowplaying', aliases=['np'], help='Show current track information')
async def nowplaying(ctx):
    track_info = music.get_current_track()
    vc = ctx.voice_client
    
    if not vc or not (vc.is_playing() or vc.is_paused()):
        embed = discord.Embed(
            title="❌ Nothing Playing",
            description="There's no track currently playing!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
    
    if track_info:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{track_info['name']}**",
            color=0x00ff00
        )
        embed.add_field(name="Artist", value=track_info['artist'], inline=True)
    else:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description="Unknown track",
            color=0x00ff00
        )
    
    # Add status information
    status = "▶️ Playing" if vc.is_playing() else "⏸️ Paused"
    embed.add_field(name="Status", value=status, inline=True)
    
    current_vol = music.get_volume()
    percentage = int(current_vol * 100)
    
    # Add volume level indicator
    if percentage == 0:
        vol_level = "🔇 Muted"
    elif percentage < 25:
        vol_level = "🔉 Low"
    elif percentage < 50:
        vol_level = "🔊 Medium"
    elif percentage < 75:
        vol_level = "🔊 High"
    else:
        vol_level = "📢 Very High"
    
    embed.add_field(name="Volume", value=f"{vol_level} ({percentage}%)", inline=True)
    
    loop_status = music.get_loop_status()
    embed.add_field(name="Loop", value="🔄 ON" if loop_status else "⏹️ OFF", inline=True)
    
    embed.set_footer(text=f"Voice Channel: {vc.channel.name} • Built by Interact Developments Inc.")
    await ctx.send(embed=embed)

@bot.command(name='skip', help='Skip the current track')
async def skip(ctx):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        embed = discord.Embed(
            title="⏭️ Track Skipped",
            description="The current track has been skipped.",
            color=0xff9900
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Nothing Playing",
            description="There's no track currently playing to skip!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)

@bot.command(name='musichelp', help='Show all music commands')
async def musichelp(ctx):
    embed = discord.Embed(
        title="🎵 Music Commands",
        description="Here are all the available music commands:",
        color=0x0099ff
    )
    
    embed.add_field(
        name="🎧 Basic Commands",
        value="`!join` - Join your voice channel\n`!leave` - Leave voice channel\n`!play <song>` - Play a song\n`!pause` - Pause current track\n`!resume` - Resume paused track\n`!stop` - Stop current track\n`!skip` - Skip current track",
        inline=False
    )
    
    embed.add_field(
        name="🎛️ Control Commands",
        value="`!volume [0-100]` - Set or check volume\n`!loop` - Toggle loop mode\n`!nowplaying` - Show current track info",
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Info Commands",
        value="`!musichelp` - Show this help message",
        inline=False
    )
    
    embed.set_footer(text="Enjoy your music! 🎶 • Built by Interact Developments Inc.")
    await ctx.send(embed=embed)

# -------- Custom Help Command --------
@bot.command(name='help', help='Show all available commands')
async def custom_help(ctx, *, command_name: str = None):
    """Custom help command with beautiful embeds."""
    
    if command_name:
        # Show help for specific command
        command = bot.get_command(command_name.lower())
        if command:
            embed = discord.Embed(
                title=f"📖 Command: {command.name}",
                description=command.help or "No description available",
                color=0x0099ff
            )
            embed.add_field(name="Usage", value=f"`!{command.name}`", inline=False)
            if command.aliases:
                embed.add_field(name="Aliases", value=f"`{'`, `'.join(command.aliases)}`", inline=False)
            embed = add_company_footer(embed)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"No command found with name: `{command_name}`",
                color=0xff0000
            )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
    
    # Show all commands in categories
    embed = discord.Embed(
        title="🤖 Interact Bot Commands",
        description="Here are all the available commands:",
        color=0x0099ff
    )
    
    # Music Commands
    music_commands = [
        "`!join` - Join voice channel",
        "`!leave` - Leave voice channel", 
        "`!play <song>` - Play music",
        "`!pause` - Pause track",
        "`!resume` - Resume track",
        "`!stop` - Stop track",
        "`!skip` - Skip track",
        "`!volume [0-100]` - Set volume",
        "`!loop` - Toggle loop",
        "`!nowplaying` - Show track info",
        "`!musichelp` - Music help"
    ]
    
    embed.add_field(
        name="🎵 Music Commands",
        value="\n".join(music_commands),
        inline=False
    )
    
    # Chat Commands
    chat_commands = [
        "`!togglemode` - Toggle SFW/NSFW mode",
        "`!reset` - Reset conversation memory",
        "`!persona <prompt>` - Set global behavior (owner only)",
        "`!attest` - Self-attest you are 18+ for NSFW features",
        "`!autochat` - Set auto-chat channel",
        "`!model` - Show/set your preferred AI model",
        "`!models` - List all available AI models",
        "`!modelinfo <model>` - Get detailed model information"
    ]
    
    # Subscription Commands
    subscription_commands = [
        "`!subscribe` - View subscription plans",
        "`!usage` - Check your usage and limits",
        "`!upgrade` - Upgrade to premium",
        "`!cancel` - Cancel subscription"
    ]
    
    embed.add_field(
        name="💬 Chat Commands", 
        value="\n".join(chat_commands),
        inline=False
    )
    
    embed.add_field(
        name="💎 Subscription Commands",
        value="\n".join(subscription_commands),
        inline=False
    )
    
    # Image Commands
    image_commands = [
        "`!image <prompt>` - Generate image",
        "`/image <prompt>` - Generate image (slash command)"
    ]
    
    embed.add_field(
        name="🎨 Image Commands",
        value="\n".join(image_commands),
        inline=False
    )
    
    # Only show admin commands to administrators
    if ctx.author.guild_permissions.administrator:
        admin_commands = [
            "`!status` - Check comprehensive bot status",
            "`!sync` - Sync slash commands",
            "`!modelstats` - Show model usage statistics",
            "`!modelhealth` - Run model health check",
            "`!kick @user [reason]` - Kick a member",
            "`!ban @user [reason]` - Ban a member",
            "`!unban <id|name#1234>` - Unban a user",
            "`!timeout @user <minutes> [reason]` - Timeout a member",
            "`!purge <count>` - Delete messages",
            "`!slowmode <seconds>` - Set slowmode",
            "`!setwelcome #channel <message>` - Configure welcome",
            "`!showwelcome` - Show welcome settings",
            "`!setwelleave <message>` - Configure leave message",
            "`!whitelist ...` - Manage unlimited-access whitelist",
            "`!togglemode` - Toggle SFW/NSFW mode",
            "`!autochat <ON/OFF>` - Set auto-chat channel"
        ]
        
        embed.add_field(
            name="⚙️ Admin Commands",
            value="\n".join(admin_commands),
            inline=False
        )
    
    # Slash Commands
    slash_commands = [
        "`/chat <message>` - Chat with AI",
        "`/image <prompt>` - Generate image",
        "`/model [model_name]` - Set/view AI model",
        "`/models` - List all AI models",
        "`/modelinfo <model>` - Get model details",
        "`/join` - Join voice channel",
        "`/leave` - Leave voice channel",
        "`/play <song>` - Play music",
        "`/pause` - Pause track",
        "`/resume` - Resume track",
        "`/stop` - Stop track",
        "`/skip` - Skip track",
        "`/volume [0-100]` - Set volume",
        "`/loop` - Toggle loop",
        "`/nowplaying` - Show track info",
        "`/upgrade` - View subscription plans",
        "`/contentfilter` - Show content filtering info",
        "`/status` - Check bot status (Admin only)"
    ]
    
    embed.add_field(
        name="⚡ Slash Commands",
        value="\n".join(slash_commands),
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Additional Info",
        value="• Mention the bot (@botname) to chat automatically\n• Use `!help <command>` for detailed help\n• Use `!musichelp` for music-specific help",
        inline=False
    )
    
    embed.set_footer(text="Built by Interact Developments Inc. • https://interactdevelopments.me/")
    await ctx.send(embed=embed)

# -------- Slash Commands for Music --------
@bot.tree.command(name="join", description="Join the voice channel you are in")
async def slash_join(interaction: discord.Interaction):
    """Slash command version of join."""
    if not interaction.user.voice or not interaction.user.voice.channel:
        embed = discord.Embed(
            title="❌ Voice Channel Required",
            description="You need to be in a voice channel to use this command!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        if interaction.guild.voice_client.channel.id == channel.id:
            embed = discord.Embed(
                title="🎵 Already Connected",
                description=f"I'm already in {channel.mention}!",
                color=0x00ff00
            )
            embed = add_company_footer(embed)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.guild.voice_client.move_to(channel)
        # Ensure bot stays deafened after moving
        await interaction.guild.voice_client.guild.change_voice_state(channel=channel, self_deaf=True)
    else:
        voice_client = await channel.connect()
        # Permanently deafen the bot
        await voice_client.guild.change_voice_state(channel=channel, self_deaf=True)
    
    embed = discord.Embed(
        title="🎵 Connected to Voice Channel",
        description=f"Successfully joined {channel.mention}!\n🔇 Bot is deafened to avoid echo",
        color=0x00ff00
    )
    embed = add_company_footer(embed)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leave", description="Leave the voice channel")
async def slash_leave(interaction: discord.Interaction):
    """Slash command version of leave."""
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        embed = discord.Embed(
            title="👋 Left Voice Channel",
            description="Successfully disconnected from the voice channel!",
            color=0xff9900
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Not Connected",
            description="I am not currently in a voice channel!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="play", description="Play a track by URL or search")
async def slash_play(interaction: discord.Interaction, query: str):
    """Slash command version of play."""
    if not interaction.user.voice or not interaction.user.voice.channel:
        embed = discord.Embed(
            title="❌ Voice Channel Required",
            description="You need to be in a voice channel to play music!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    if not interaction.guild.voice_client:
        # Auto-join first
        channel = interaction.user.voice.channel
        voice_client = await channel.connect()
        await voice_client.guild.change_voice_state(channel=channel, self_deaf=True)
    
    vc = interaction.guild.voice_client
    if not vc:
        return
    
    # Create loading embed
    loading_embed = discord.Embed(
        title="🔍 Searching for Music...",
        description=f"Looking for: **{query}**",
        color=0xffff00
    )
    loading_embed = add_company_footer(loading_embed)
    await interaction.response.send_message(embed=loading_embed)
    loading_msg = await interaction.original_response()
    
    # Try Spotify first, then YouTube as fallback
    url = music.get_preview_url(query)
    source_type = "Spotify"
    
    if not url:
        print(f"No Spotify preview found for '{query}', trying YouTube...")
        url = music.get_youtube_url(query)
        source_type = "YouTube"
    
    if not url:
        error_embed = discord.Embed(
            title="❌ No Audio Found",
            description=f"Could not find any playable audio for: **{query}**\n\nTry a different search term or check the spelling!",
            color=0xff0000
        )
        error_embed = add_company_footer(error_embed)
        await loading_msg.edit(embed=error_embed)
        return
    
    try:
        # Use FFmpegPCMAudio to stream the audio
        from discord import FFmpegPCMAudio
        executable = FFMPEG_PATH if FFMPEG_PATH else 'ffmpeg'
        
        # Apply volume
        current_vol = music.get_volume()
        # Create FFmpeg options with volume control and better YouTube support
        before_options = f"-af volume={current_vol} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2"
        after_options = "-vn"
        source = FFmpegPCMAudio(url, executable=executable, before_options=before_options, options=after_options)
        
        if vc.is_playing():
            vc.stop()
        
        vc.play(source)
        
        # Set track info
        music.set_current_track(query)
        
        # Create success embed
        success_embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{query}**",
            color=0x00ff00
        )
        success_embed.add_field(name="Source", value=f"🎧 {source_type}", inline=True)
        
        # Add enhanced volume display
        percentage = int(current_vol * 100)
        if percentage == 0:
            vol_level = "🔇 Muted"
        elif percentage < 25:
            vol_level = "🔉 Low"
        elif percentage < 50:
            vol_level = "🔊 Medium"
        elif percentage < 75:
            vol_level = "🔊 High"
        else:
            vol_level = "📢 Very High"
        
        success_embed.add_field(name="Volume", value=f"{vol_level} ({percentage}%)", inline=True)
        success_embed.add_field(name="Loop", value="🔄 Off", inline=True)
        success_embed.set_footer(text=f"Requested by {interaction.user.display_name} • Built by Interact Developments Inc.", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        await loading_msg.edit(embed=success_embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Playback Error",
            description=f"Failed to play the audio: {str(e)}",
            color=0xff0000
        )
        error_embed = add_company_footer(error_embed)
        await loading_msg.edit(embed=error_embed)

@bot.tree.command(name="pause", description="Pause the current track")
async def slash_pause(interaction: discord.Interaction):
    """Slash command version of pause."""
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        embed = discord.Embed(
            title="⏸️ Track Paused",
            description="The current track has been paused.",
            color=0xff9900
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
    elif vc and vc.is_paused():
        embed = discord.Embed(
            title="⏸️ Already Paused",
            description="The track is already paused! Use `/resume` to continue.",
            color=0xff9900
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Nothing Playing",
            description="There's no track currently playing to pause!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="resume", description="Resume the paused track")
async def slash_resume(interaction: discord.Interaction):
    """Slash command version of resume."""
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        embed = discord.Embed(
            title="▶️ Track Resumed",
            description="The track has been resumed!",
            color=0x00ff00
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
    elif vc and vc.is_playing():
        embed = discord.Embed(
            title="▶️ Already Playing",
            description="The track is already playing!",
            color=0x00ff00
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Nothing to Resume",
            description="There's no paused track to resume!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stop", description="Stop the current track")
async def slash_stop(interaction: discord.Interaction):
    """Slash command version of stop."""
    vc = interaction.guild.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        embed = discord.Embed(
            title="⏹️ Track Stopped",
            description="The current track has been stopped.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Nothing Playing",
            description="There's no track currently playing to stop!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="skip", description="Skip the current track")
async def slash_skip(interaction: discord.Interaction):
    """Slash command version of skip."""
    vc = interaction.guild.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        embed = discord.Embed(
            title="⏭️ Track Skipped",
            description="The current track has been skipped.",
            color=0xff9900
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Nothing Playing",
            description="There's no track currently playing to skip!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="volume", description="Set or check the volume (0-100)")
async def slash_volume(interaction: discord.Interaction, vol: int = None):
    """Slash command version of volume."""
    if vol is None:
        # Show current volume
        current_vol = music.get_volume()
        percentage = int(current_vol * 100)
        
        embed = discord.Embed(
            title="🔊 Current Volume",
            description=f"**{percentage}%**",
            color=0x0099ff
        )
        
        # Create a more detailed volume bar
        bar_length = 20
        filled_length = int((current_vol * bar_length))
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Add volume level indicator
        if percentage == 0:
            level = "🔇 Muted"
        elif percentage < 25:
            level = "🔉 Low"
        elif percentage < 50:
            level = "🔊 Medium"
        elif percentage < 75:
            level = "🔊 High"
        else:
            level = "📢 Very High"
        
        embed.add_field(name="Volume Level", value=level, inline=True)
        embed.add_field(name="Volume Bar", value=f"`{bar}`", inline=False)
        embed.add_field(name="Note", value="Volume changes apply to new tracks", inline=False)
        
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        # Set volume
        if vol < 0 or vol > 100:
            embed = discord.Embed(
                title="❌ Invalid Volume",
                description="Volume must be between 0 and 100!",
                color=0xff0000
            )
            embed = add_company_footer(embed)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        new_vol = music.set_volume(vol / 100.0)
        percentage = int(new_vol * 100)
        
        embed = discord.Embed(
            title="🔊 Volume Changed",
            description=f"Volume set to **{percentage}%**",
            color=0x00ff00
        )
        
        # Create volume bar
        bar_length = 20
        filled_length = int((new_vol * bar_length))
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Add volume level indicator
        if percentage == 0:
            level = "🔇 Muted"
        elif percentage < 25:
            level = "🔉 Low"
        elif percentage < 50:
            level = "🔊 Medium"
        elif percentage < 75:
            level = "🔊 High"
        else:
            level = "📢 Very High"
        
        embed.add_field(name="Volume Level", value=level, inline=True)
        embed.add_field(name="Volume Bar", value=f"`{bar}`", inline=False)
        embed.add_field(name="Note", value="Volume changes apply to new tracks", inline=False)
        
        embed = add_company_footer(embed)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="loop", description="Toggle loop mode on/off")
async def slash_loop(interaction: discord.Interaction):
    """Slash command version of loop."""
    loop_status = music.toggle_loop()
    status_text = "ON" if loop_status else "OFF"
    status_color = 0x00ff00 if loop_status else 0xff0000
    status_emoji = "🔄" if loop_status else "⏹️"
    
    embed = discord.Embed(
        title=f"{status_emoji} Loop Mode",
        description=f"Loop mode is now **{status_text}**",
        color=status_color
    )
    embed = add_company_footer(embed)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nowplaying", description="Show current track information")
async def slash_nowplaying(interaction: discord.Interaction):
    """Slash command version of nowplaying."""
    track_info = music.get_current_track()
    vc = interaction.guild.voice_client
    
    if not vc or not (vc.is_playing() or vc.is_paused()):
        embed = discord.Embed(
            title="❌ Nothing Playing",
            description="There's no track currently playing!",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if track_info:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{track_info['name']}**",
            color=0x00ff00
        )
        embed.add_field(name="Artist", value=track_info['artist'], inline=True)
    else:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description="Unknown track",
            color=0x00ff00
        )
    
    # Add status information
    status = "▶️ Playing" if vc.is_playing() else "⏸️ Paused"
    embed.add_field(name="Status", value=status, inline=True)
    
    current_vol = music.get_volume()
    percentage = int(current_vol * 100)
    
    # Add volume level indicator
    if percentage == 0:
        vol_level = "🔇 Muted"
    elif percentage < 25:
        vol_level = "🔉 Low"
    elif percentage < 50:
        vol_level = "🔊 Medium"
    elif percentage < 75:
        vol_level = "🔊 High"
    else:
        vol_level = "📢 Very High"
    
    embed.add_field(name="Volume", value=f"{vol_level} ({percentage}%)", inline=True)
    
    loop_status = music.get_loop_status()
    embed.add_field(name="Loop", value="🔄 ON" if loop_status else "⏹️ OFF", inline=True)
    
    embed.set_footer(text=f"Voice Channel: {vc.channel.name} • Built by Interact Developments Inc.")
    embed = add_company_footer(embed)
    await interaction.response.send_message(embed=embed)

# -------- Image Generation Commands --------
@bot.command(name='image', help='Generate an image using OpenRouter (enter a prompt). Optional: model=<id> size=<WxH>')
async def image_cmd(ctx, *, prompt: str = None):
    if not prompt:
        return await ctx.send('Usage: !image <prompt> [model=<openrouter_model_id>] [size=1024x1024]')
    await ctx.send('🎨 Generating image...')
    try:
        # Parse optional flags: model=<id> size=<WxH>
        import re
        model_match = re.search(r"model=([^\s]+)", prompt)
        size_match = re.search(r"size=([0-9]{2,4}x[0-9]{2,4})", prompt)
        model_id = model_match.group(1) if model_match else None
        size = size_match.group(1) if size_match else "1024x1024"
        # Remove flags from the actual prompt
        clean_prompt = re.sub(r"(model=[^\s]+|size=[0-9]{2,4}x[0-9]{2,4})", "", prompt).strip()

        img_bytes = await api_handler.generate_image_unified(clean_prompt, size=size, model=model_id)
        if not img_bytes:
            return await ctx.send('❌ Failed to generate image. BentoML service may be down. Try: `python start_optimized_bentoml.bat` to start the local image service.')
        import io
        from discord import File
        file = File(io.BytesIO(img_bytes), filename='image.png')
        await ctx.send(file=file)
    except Exception as e:
        print(f"Image generation error: {e}")
        await ctx.send('❌ Error while generating image.')

@bot.tree.command(name='image', description='Generate an image using OpenRouter')
async def image_slash(interaction: discord.Interaction, prompt: str, model: str | None = None, size: str | None = None):
    await interaction.response.defer()
    try:
        img_bytes = await api_handler.generate_image_unified(prompt, size=size or "1024x1024", model=model)
        if not img_bytes:
            return await interaction.followup.send('❌ Failed to generate image. BentoML service may be down. Try: `python start_optimized_bentoml.bat` to start the local image service.')
        import io
        from discord import File
        file = File(io.BytesIO(img_bytes), filename='image.png')
        await interaction.followup.send(file=file)
    except Exception as e:
        print(f"Image generation error: {e}")
        await interaction.followup.send('❌ Error while generating image.')

@bot.command(name='togglemode', help='Toggles the chat mode between 18+ and Under 18.')
async def toggle_mode(ctx):
    """Toggles the chat mode for the server or DM."""
    # Handle DMs differently
    if ctx.guild is None:
        # For DMs, toggle user's personal mode
        user_id = str(ctx.author.id)
        current_mode = user_modes.get(user_id, False)
        user_modes[user_id] = not current_mode
        
        mode_text = "18+ (NSFW)" if user_modes[user_id] else "Under 18 (SFW)"
        
        embed = discord.Embed(
            title="Mode Changed!",
            description=f"Your personal chat mode is now set to **{mode_text}**.",
            color=discord.Color.red() if user_modes[user_id] else discord.Color.green()
        )
        embed = add_company_footer(embed)
        await ctx.send(embed=embed)
        return
    
    # For guilds, check if user is administrator or owner
    is_owner = OWNER_USER_ID and OWNER_USER_ID > 0 and ctx.author.id == OWNER_USER_ID
    perms = ctx.author.guild_permissions if ctx.guild else None
    is_admin = perms and perms.administrator
    
    if not (is_owner or is_admin):
        await ctx.send("❌ Sorry, you must be an administrator to use this command in servers.")
        return
    
    guild_id = ctx.guild.id
    # Flip the current mode
    server_modes[guild_id] = not server_modes.get(guild_id, False) 
    
    mode_text = "18+ (NSFW)" if server_modes[guild_id] else "Under 18 (SFW)"
    
    embed = discord.Embed(
        title="Mode Changed!",
        description=f"Chat mode for this server is now set to **{mode_text}**.",
        color=discord.Color.red() if server_modes[guild_id] else discord.Color.green()
    )
    embed = add_company_footer(embed)
    await ctx.send(embed=embed)

@bot.command(name='autochat', help='Set current channel for automatic chat replies ON/OFF')
@commands.has_permissions(administrator=True)
async def autochat(ctx, mode: str):
    """Enable or disable automatic chat in this channel.
    Usage: !autochat on | off
    """
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    normalized = mode.strip().lower()
    if normalized in ("on", "enable", "enabled", "true", "yes"):
        auto_chat_channels[guild_id] = channel_id
        await ctx.send(f"✅ Auto chat enabled in this channel.")
    elif normalized in ("off", "disable", "disabled", "false", "no"):
        if guild_id in auto_chat_channels:
            del auto_chat_channels[guild_id]
        await ctx.send("🛑 Auto chat disabled for this server.")
    else:
        await ctx.send("Usage: !autochat on | off")


# Add error handlers for other admin commands
@model_stats.error
async def model_stats_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sorry, you must be an administrator to use this command.")

@model_health.error
async def model_health_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sorry, you must be an administrator to use this command.")

@subscription_stats.error
async def subscription_stats_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sorry, you must be an administrator to use this command.")

@cleanup_subscriptions.error
async def cleanup_subscriptions_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sorry, you must be an administrator to use this command.")

@whitelist_cmd.error
async def whitelist_cmd_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sorry, you must be an administrator to use this command.")

@sync_commands.error
async def sync_commands_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sorry, you must be an administrator to use this command.")

@bot.tree.command(name="chat", description="Chat with the AI bot")
async def chat_command(interaction: discord.Interaction, message: str):
    """Slash command to chat with the bot."""
    # Handle both guild and DM contexts
    if interaction.guild:
        guild_id = interaction.guild.id
        is_nsfw_mode = server_modes.get(guild_id, False)
    else:
        # For DMs, check user's personal mode
        user_id = str(interaction.user.id)
        is_nsfw_mode = user_modes.get(user_id, False)
    
    await interaction.response.defer()  # Let Discord know we're processing
    
    try:
        ctx_id = _context_id_from_interaction(interaction)
        history = conversations.get(ctx_id, [])
        sys_override = global_persona
        
        # Enforce NSFW constraints: require channel flagged NSFW and user attestation
        if is_nsfw_mode:
            # Skip channel NSFW check for DMs
            if interaction.guild:
                # Channel must be marked NSFW by Discord (only for guilds)
                channel_is_nsfw = getattr(interaction.channel, 'is_nsfw', lambda: False)()
                if not channel_is_nsfw:
                    return await interaction.followup.send("❌ NSFW mode is only available in channels marked NSFW by Discord.")
            # User must be attested
            if str(interaction.user.id) not in nsfw_attested_users:
                return await interaction.followup.send("❌ You must self-attest you are 18+. Use `/attest`.")

        # Use model manager for response
        user_id = str(interaction.user.id)
        
        # Modify system prompt for NSFW mode
        if is_nsfw_mode:
            nsfw_persona = (
                "You are Discord AI chatbot. Built and Developed by Interact Developments Inc., "
                "their main website is https://interactdevelopments.me/. They have been operating since 2019 "
                "and have been creating Discord bots for a long time. "
                "You were initially a music bot from 2019-2023 but after 2 years of development you are a full-fledged "
                "Discord AI chatbot. Your main goal is to create a persona for your users to make them happy and keep "
                "them engaged. Keep the conversation cool and keep them hooked, like a close friend. "
                "Remember key details for 7 days and make the user feel homely and safe around you. "
                "You are currently in NSFW mode and can discuss adult topics, relationships, and intimate conversations. "
                "Be open, understanding, and engaging while maintaining appropriate boundaries. "
                "You can provide advice, have conversations, and be supportive about adult topics."
            )
            sys_override = nsfw_persona
        
        response, model_used = await model_manager.get_chat_response(
            prompt=message,
            user_id=user_id,
            is_nsfw=is_nsfw_mode,
            history=history,
            system_override=sys_override
        )
        
        # Update memory
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        conversations[ctx_id] = history[-MAX_TURNS:]
        
        # Realistic typing delay based on response length
        response_length = len(response)
        if response_length < 50:
            typing_delay = 1.0  # Short response
        elif response_length < 200:
            typing_delay = 2.0  # Medium response
        else:
            typing_delay = 3.0  # Long response
        
        await asyncio.sleep(typing_delay)
        await interaction.followup.send(response)
    except Exception as e:
        print(f"An error occurred: {e}")
        await interaction.followup.send("Sorry, I couldn't get a response from the API. Please try again later.")

# Additional slash commands
@bot.tree.command(name="model", description="Set your preferred AI model")
async def slash_model(interaction: discord.Interaction, model_name: str = None):
    """Slash command to set preferred AI model"""
    if not model_name:
        # Show current model and available options
        user_id = str(interaction.user.id)
        current_model_id = model_manager.get_user_preference(user_id)
        current_model = model_manager.get_model_info(current_model_id)
        
        embed = discord.Embed(
            title="🤖 Current AI Model",
            description=f"**{current_model.name if current_model else 'Unknown'}**",
            color=0x0099ff
        )
        
        if current_model:
            embed.add_field(name="Provider", value=current_model.provider.value.title(), inline=True)
            embed.add_field(name="Status", value=f"🟢 {current_model.status.value.title()}", inline=True)
            embed.add_field(name="Max Tokens", value=f"{current_model.max_tokens:,}", inline=True)
            embed.add_field(name="Cost per 1K tokens", value=f"${current_model.cost_per_1k_tokens:.4f}", inline=True)
            embed.add_field(name="Usage Count", value=str(current_model.usage_count), inline=True)
            embed.add_field(name="Avg Response Time", value=f"{current_model.avg_response_time:.2f}s", inline=True)
        
        embed.add_field(
            name="Available Models", 
            value="Use `/models` to see all available models\nUse `/model <model_name>` to change your model",
            inline=False
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
        return
    
    # Set new model
    user_id = str(interaction.user.id)
    success = model_manager.set_user_preference(user_id, model_name)
    
    if success:
        # Get the actual model ID that was set
        actual_model_id = model_manager.get_user_preference(user_id)
        actual_model = model_manager.get_model_info(actual_model_id)
        
        embed = discord.Embed(
            title="✅ Model Updated",
            description=f"Your preferred model has been set to **{actual_model.name if actual_model else 'Unknown'}**",
            color=0x00ff00
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Invalid Model",
            description=f"Model '{model_name}' not found. Use `/models` to see available models.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="models", description="List all available AI models")
async def slash_models(interaction: discord.Interaction):
    """Slash command to list all available AI models"""
    embed = discord.Embed(
        title="🤖 Available AI Models",
        description="Here are all the available AI models organized by content type:",
        color=0x0099ff
    )
    
    # Define SFW and NSFW models based on our implementation
    sfw_models = [
        "google/gemma-3n-e2b-it:free",
        "nvidia/nemotron-nano-9b-v2:free"
    ]
    
    nsfw_models = [
        "google/gemma-3n-e2b-it:free",
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
    ]
    
    # Get SFW models
    sfw_list = []
    for model_id in sfw_models:
        if model_id in model_manager.models:
            model = model_manager.models[model_id]
            status_emoji = {
                'online': '🟢',
                'offline': '🔴', 
                'degraded': '🟡',
                'unknown': '⚪'
            }.get(model.status.value, '⚪')
            
            cost_info = "🆓 FREE" if model.cost_per_1k_tokens == 0 else f"${model.cost_per_1k_tokens:.4f}/1k tokens"
            sfw_list.append(f"{status_emoji} **{model.name}** - {cost_info}")
    
    # Get NSFW models
    nsfw_list = []
    for model_id in nsfw_models:
        if model_id in model_manager.models:
            model = model_manager.models[model_id]
            status_emoji = {
                'online': '🟢',
                'offline': '🔴', 
                'degraded': '🟡',
                'unknown': '⚪'
            }.get(model.status.value, '⚪')
            
            cost_info = "🆓 FREE" if model.cost_per_1k_tokens == 0 else f"${model.cost_per_1k_tokens:.4f}/1k tokens"
            nsfw_list.append(f"{status_emoji} **{model.name}** - {cost_info}")
    
    # Add SFW section
    embed.add_field(
        name="🛡️ SFW Models (Safe for Work)",
        value="\n".join(sfw_list) if sfw_list else "No SFW models available",
        inline=False
    )
    
    # Add NSFW section
    embed.add_field(
        name="🔞 NSFW Models (18+ Content)",
        value="\n".join(nsfw_list) if nsfw_list else "No NSFW models available",
        inline=False
    )
    
    # Add model details
    embed.add_field(
        name="📊 Model Details",
        value="• **Google Gemma 3n 2B**: Fast, efficient 2B parameter model\n• **NVIDIA Nemotron Nano 9B**: High-quality 9B parameter model\n• **Dolphin Mistral 24B**: Advanced 24B parameter model for complex tasks",
        inline=False
    )
    
    embed.add_field(
        name="💡 Usage",
        value="• Use `/model <model_name>` to set your preferred model\n• Use `/model` to see your current model\n• Use `/modelinfo <model_name>` for detailed info\n• Use `!togglemode` to switch between SFW/NSFW modes",
        inline=False
    )
    embed = add_company_footer(embed)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="modelinfo", description="Get detailed information about a specific model")
async def slash_modelinfo(interaction: discord.Interaction, model_name: str):
    """Slash command to get detailed model information"""
    # Try to find the model by name
    model_id = model_manager.find_model_by_name(model_name)
    if not model_id:
        embed = discord.Embed(
            title="❌ Model Not Found",
            description=f"Model '{model_name}' not found. Use `/models` to see available models.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
        return
    
    model = model_manager.get_model_info(model_id)
    if not model:
        embed = discord.Embed(
            title="❌ Model Not Found",
            description=f"Model '{model_name}' not found.",
            color=0xff0000
        )
        embed = add_company_footer(embed)
        await interaction.response.send_message(embed=embed)
        return
    
    status_emoji = {
        'online': '🟢',
        'offline': '🔴',
        'degraded': '🟡',
        'unknown': '⚪'
    }.get(model.status.value, '⚪')
    
    embed = discord.Embed(
        title=f"🤖 {model.name}",
        description=model.description,
        color=0x0099ff
    )
    
    embed.add_field(name="Model ID", value=model.id, inline=True)
    embed.add_field(name="Provider", value=model.provider.value.title(), inline=True)
    embed.add_field(name="Status", value=f"{status_emoji} {model.status.value.title()}", inline=True)
    embed.add_field(name="Max Tokens", value=f"{model.max_tokens:,}", inline=True)
    embed.add_field(name="Cost per 1K tokens", value=f"${model.cost_per_1k_tokens:.4f}", inline=True)
    embed.add_field(name="Supports Images", value="✅" if model.supports_images else "❌", inline=True)
    embed.add_field(name="Supports Functions", value="✅" if model.supports_functions else "❌", inline=True)
    embed.add_field(name="Usage Count", value=str(model.usage_count), inline=True)
    embed.add_field(name="Error Count", value=str(model.error_count), inline=True)
    embed.add_field(name="Avg Response Time", value=f"{model.avg_response_time:.2f}s", inline=True)
    
    if model.last_used:
        from datetime import datetime
        last_used = datetime.fromtimestamp(model.last_used).strftime("%Y-%m-%d %H:%M:%S")
        embed.add_field(name="Last Used", value=last_used, inline=True)
    
    # Add content guidelines for specific models
    try:
        from content_filter import content_filter
        guidelines = content_filter.get_model_guidelines(model_id)
        embed.add_field(
            name="📋 Content Guidelines",
            value=guidelines,
            inline=False
        )
    except ImportError:
        pass
    
    embed = add_company_footer(embed)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="contentfilter", description="Show content filtering information")
async def slash_contentfilter(interaction: discord.Interaction):
    """Slash command to show content filtering information"""
    embed = discord.Embed(
        title="🛡️ Content Filtering System",
        description="Information about content filtering and moderation",
        color=0x0099ff
    )
    
    embed.add_field(
        name="🚫 Blocked Content",
        value=(
            "• **Drug-related content** - All drug names, slang, and related terms\n"
            "• **Violence content** - Graphic violence, harm, weapons\n"
            "• **Harassment content** - Doxxing, stalking, threats\n"
            "• **NSFW in SFW mode** - Adult content outside NSFW channels"
        ),
        inline=False
    )
    
    embed.add_field(
        name="✅ Allowed Content",
        value=(
            "• **SFW content** - Safe for work discussions\n"
            "• **NSFW content** - Adult topics in NSFW mode (Dolphin model)\n"
            "• **Romantic discussions** - Dating, relationships, intimacy\n"
            "• **Educational content** - Learning and information sharing"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔞 Dolphin Model Special Rules",
        value=(
            "The Dolphin Mistral model has special content filtering:\n"
            "• ✅ **Allows:** Adult conversations, sexual topics, romance\n"
            "• ❌ **Blocks:** Drug-related content, violence, harassment\n"
            "• ⚠️ **Note:** Only works in NSFW mode with proper attestation"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💡 How to Use",
        value=(
            "• Use `!togglemode` to enable NSFW mode (admin only)\n"
            "• Use `/attest` to verify you're 18+ for NSFW content\n"
            "• Use `/model dolphin` to switch to Dolphin model\n"
            "• Use `/modelinfo dolphin` for detailed model guidelines"
        ),
        inline=False
    )
    
    embed = add_company_footer(embed)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="upgrade", description="View subscription plans and upgrade options")
async def slash_upgrade(interaction: discord.Interaction):
    """Slash command to view subscription plans"""
    embed = discord.Embed(
        title="💎 Subscription Plans",
        description="Choose the plan that's right for you:",
        color=0x0099ff
    )
    
    # Get subscription plans
    plans = subscription_manager.get_subscription_plans()
    
    for plan in plans:
        plan_name = plan.name
        plan_price = f"${plan.price:.2f}/month" if plan.price > 0 else "FREE"
        plan_features = "\n".join(plan.features)
        
        embed.add_field(
            name=f"{plan_name} - {plan_price}",
            value=plan_features,
            inline=False
        )
    
    embed.add_field(
        name="💡 How to Subscribe",
        value="• Use `!subscribe` to view detailed plans\n• Use `!upgrade <plan>` to upgrade\n• Use `!usage` to check your current usage",
        inline=False
    )
    
    embed = add_company_footer(embed)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Check comprehensive bot status (Admin only)")
async def slash_status(interaction: discord.Interaction):
    """Slash command to check comprehensive bot status"""
    # Check if user has administrator permissions
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ You must be an administrator to use this command.", ephemeral=True)
    
    await interaction.response.defer()
    
    try:
        # Create status embed
        embed = discord.Embed(
            title="🤖 Bot Status Dashboard",
            description="Comprehensive system status and health information",
            color=0x00ff00
        )
        
        # Bot Status
        bot_status_emoji = "🟢" if bot.status == discord.Status.online else "🔴"
        embed.add_field(
            name="Bot Status",
            value=f"{bot_status_emoji} {str(bot.status).title()}",
            inline=True
        )
        
        # Guild Count
        embed.add_field(
            name="Servers",
            value=f"📊 {len(bot.guilds)}",
            inline=True
        )
        
        # User Count
        total_users = sum(guild.member_count for guild in bot.guilds if guild.member_count)
        embed.add_field(
            name="Total Users",
            value=f"👥 {total_users:,}",
            inline=True
        )
        
        # Model Status
        try:
            model_stats = model_manager.get_model_stats()
            online_models = model_stats.get('online_models', 0)
            total_models = model_stats.get('total_models', 0)
            
            model_status = f"🟢 {online_models}/{total_models} Online"
            if online_models < total_models:
                offline_count = model_stats.get('offline_models', 0)
                degraded_count = model_stats.get('degraded_models', 0)
                model_status += f"\n🔴 {offline_count} Offline\n🟡 {degraded_count} Degraded"
            
            embed.add_field(
                name="AI Models",
                value=model_status,
                inline=True
            )
        except Exception as e:
            embed.add_field(
                name="AI Models",
                value=f"❌ Error: {str(e)[:50]}...",
                inline=True
            )
        
        # Database Status (if available)
        try:
            # Try to import and check database status
            from database_manager import db_manager
            db_stats = db_manager.get_database_stats()
            
            embed.add_field(
                name="Database",
                value=f"💾 {db_stats.get('total_conversations', 0)} conversations\n"
                      f"👤 {db_stats.get('unique_users', 0)} users\n"
                      f"📚 {db_stats.get('knowledge_entries', 0)} knowledge entries",
                inline=True
            )
        except ImportError:
            embed.add_field(
                name="Database",
                value="❌ Not available",
                inline=True
            )
        except Exception as e:
            embed.add_field(
                name="Database",
                value=f"⚠️ Error: {str(e)[:30]}...",
                inline=True
            )
        
        # Memory Usage
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            embed.add_field(
                name="Memory Usage",
                value=f"🧠 {memory_mb:.1f} MB",
                inline=True
            )
        except ImportError:
            embed.add_field(
                name="Memory Usage",
                value="❌ psutil not available",
                inline=True
            )
        except Exception:
            embed.add_field(
                name="Memory Usage",
                value="❌ Unable to get",
                inline=True
            )
        
        # Uptime
        try:
            import time
            uptime_seconds = time.time() - bot.start_time if hasattr(bot, 'start_time') else 0
            uptime_hours = uptime_seconds / 3600
            embed.add_field(
                name="Uptime",
                value=f"⏱️ {uptime_hours:.1f} hours",
                inline=True
            )
        except Exception:
            embed.add_field(
                name="Uptime",
                value="❌ Unable to calculate",
                inline=True
            )
        
        # Recent Activity
        try:
            recent_activity = model_stats.get('conversations_last_24h', 0) if 'model_stats' in locals() else 0
            embed.add_field(
                name="24h Activity",
                value=f"💬 {recent_activity} conversations",
                inline=True
            )
        except Exception:
            embed.add_field(
                name="24h Activity",
                value="❌ Unable to get",
                inline=True
            )
        
        # System Health
        health_status = "🟢 Healthy"
        if 'model_stats' in locals():
            offline_models = model_stats.get('offline_models', 0)
            if offline_models > 0:
                health_status = "🟡 Degraded"
            if offline_models == model_stats.get('total_models', 1):
                health_status = "🔴 Critical"
        
        embed.add_field(
            name="System Health",
            value=health_status,
            inline=True
        )
        
        # Footer
        embed.set_footer(text="Built by Interact Developments Inc. • Use /modelhealth for detailed model check")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Status Check Failed",
            description=f"Error retrieving bot status: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed)

@bot.event
async def on_message(message):
    """Event handler for when a message is sent."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process commands first
    await bot.process_commands(message)

    guild_id = message.guild.id if message.guild else None
    if guild_id:
        is_nsfw_mode = server_modes.get(guild_id, False)
    else:
        # For DMs, check user's personal mode
        user_id = str(message.author.id)
        is_nsfw_mode = user_modes.get(user_id, False)

    # Determine if we should auto-reply
    should_auto = False
    if message.guild:
        # Auto reply in opted-in channel
        should_auto = auto_chat_channels.get(guild_id) == message.channel.id
        # Also reply when mentioned
        if bot.user.mentioned_in(message) and not message.reference:
            should_auto = True
    else:
        # Always reply in DMs
        should_auto = True

    if not should_auto:
        return

    # Strip mention if present
    user_message = message.content.replace(f'<@!{bot.user.id}>', '').strip()
    user_message = user_message.replace(f'<@{bot.user.id}>', '').strip()
    if not user_message:
        return

    async with message.channel.typing():
        try:
            ctx_id = _context_id_from_message(message)
            history = conversations.get(ctx_id, [])
            sys_override = global_persona
            
            # Enforce NSFW constraints: require channel flagged NSFW and user attestation
            if is_nsfw_mode:
                # Skip channel NSFW check for DMs
                if message.guild:
                    channel_is_nsfw = getattr(message.channel, 'is_nsfw', lambda: False)()
                    if not channel_is_nsfw:
                        return await message.reply("❌ NSFW mode is only available in channels marked NSFW by Discord.", mention_author=True)
                if str(message.author.id) not in nsfw_attested_users:
                    return await message.reply("❌ You must self-attest you are 18+. Use `!attest` or `/attest`.", mention_author=True)

            # Use model manager for response
            user_id = str(message.author.id)
            
            # Modify system prompt for NSFW mode
            if is_nsfw_mode:
                nsfw_persona = (
                    "You are Discord AI chatbot. Built and Developed by Interact Developments Inc., "
                    "their main website is https://interactdevelopments.me/. They have been operating since 2019 "
                    "and have been creating Discord bots for a long time. "
                    "You were initially a music bot from 2019-2023 but after 2 years of development you are a full-fledged "
                    "Discord AI chatbot. Your main goal is to create a persona for your users to make them happy and keep "
                    "them engaged. Keep the conversation cool and keep them hooked, like a close friend. "
                    "Remember key details for 7 days and make the user feel homely and safe around you. "
                    "You are currently in NSFW mode and can discuss adult topics, relationships, and intimate conversations. "
                    "Be open, understanding, and engaging while maintaining appropriate boundaries. "
                    "You can provide advice, have conversations, and be supportive about adult topics."
                )
                sys_override = nsfw_persona
            
            response, model_used = await model_manager.get_chat_response(
                prompt=user_message,
                user_id=user_id,
                is_nsfw=is_nsfw_mode,
                history=history,
                system_override=sys_override
            )
            
            # Update memory
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": response})
            conversations[ctx_id] = history[-MAX_TURNS:]
            
            # Realistic typing delay based on response length
            response_length = len(response)
            if response_length < 50:
                typing_delay = 1.0  # Short response
            elif response_length < 200:
                typing_delay = 2.0  # Medium response
            else:
                typing_delay = 3.0  # Long response
            
            await asyncio.sleep(typing_delay)
            await message.reply(response, mention_author=True)
        except Exception as e:
            print(f"An error occurred in message processing: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            await message.reply("Sorry, I couldn't get a response from the API. Please try again later.", mention_author=True)


if __name__ == "__main__":
    if DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN":
        print("Please set your DISCORD_TOKEN in config.py")
    else:
        print(f"Starting bot with token: {DISCORD_TOKEN[:10]}...")
        print("Make sure your bot has the following permissions in Discord Developer Portal:")
        print("- Send Messages")
        print("- Use Slash Commands") 
        print("- Read Message History")
        print("- Add Reactions")
        print("- Embed Links")
        print("- Attach Files")
        print("- Read Message Content (Privileged Intent)")
        print("- Server Members Intent (if needed)")
        print("\nStarting bot...")
        try:
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            print(f"❌ Error starting bot: {e}")
            print("Check your bot token and permissions in Discord Developer Portal")
