"""
Enhanced AI Discord Bot with Database and RAG Integration
Main bot file with database-backed contexts and RAG capabilities
"""

import discord
import asyncio
from discord.ext import commands
import api_handler
import music
from enhanced_model_manager import enhanced_model_manager
from context_manager import context_manager
from subscription_manager import subscription_manager, SubscriptionTier
from config import DISCORD_TOKEN
from config import GLOBAL_PERSONA
from config import OWNER_USER_ID
from config import FFMPEG_PATH

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
# Per-server auto chat channel mapping: guild_id -> channel_id
auto_chat_channels = {}
# Welcome settings per server: guild_id -> { 'channel_id': int, 'welcome_message': str }
welcome_settings = {}
# Global persona/system prompt applied across all channels and DMs
global_persona = GLOBAL_PERSONA if (GLOBAL_PERSONA and GLOBAL_PERSONA.strip()) else None

# -- Welcome Settings Persistence --
WELCOME_SETTINGS_FILE = "welcome_config.json"

def _load_welcome_settings():
    global welcome_settings
    try:
        import json, os
        if os.path.exists(WELCOME_SETTINGS_FILE):
            with open(WELCOME_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                welcome_settings = data
    except Exception as e:
        print(f"Error loading welcome settings: {e}")

def _save_welcome_settings():
    try:
        import json
        with open(WELCOME_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(welcome_settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving welcome settings: {e}")

# Load welcome settings on startup
_load_welcome_settings()

# -- NSFW Attestation System --
nsfw_attested_users = set()

def _load_nsfw_attestations():
    global nsfw_attested_users
    try:
        import json, os
        if os.path.exists("nsfw_attestations.json"):
            with open("nsfw_attestations.json", 'r') as f:
                data = json.load(f)
                nsfw_attested_users = set(data.get('attested_users', []))
    except Exception as e:
        print(f"Error loading NSFW attestations: {e}")

def _save_nsfw_attestations():
    try:
        import json
        data = {'attested_users': list(nsfw_attested_users)}
        with open("nsfw_attestations.json", 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving NSFW attestations: {e}")

# Load NSFW attestations on startup
_load_nsfw_attestations()

# -- Context ID Helpers --
def _context_id_from_interaction(interaction):
    """Generate context ID from Discord interaction"""
    if interaction.guild:
        return f"guild_{interaction.guild.id}_channel_{interaction.channel.id}"
    else:
        return f"dm_{interaction.user.id}"

def _context_id_from_message(message):
    """Generate context ID from Discord message"""
    if message.guild:
        return f"guild_{message.guild.id}_channel_{message.channel.id}"
    else:
        return f"dm_{message.author.id}"

# -- Bot Events --
@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    print(f"🤖 {bot.user} is online and ready!")
    print(f"📊 Database stats: {enhanced_model_manager.get_user_stats('system')}")
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

@bot.event
async def on_guild_join(guild):
    """Event handler for when the bot joins a new guild."""
    print(f"🎉 Joined new guild: {guild.name} (ID: {guild.id})")
    
    # Set default welcome settings
    welcome_settings[guild.id] = {
        'channel_id': None,
        'welcome_message': f"Thanks for adding me to {guild.name}! Use `/help` to see what I can do."
    }
    _save_welcome_settings()

@bot.event
async def on_member_join(member):
    """Event handler for when a member joins a guild."""
    if member.guild.id in welcome_settings:
        settings = welcome_settings[member.guild.id]
        if settings['channel_id']:
            channel = member.guild.get_channel(settings['channel_id'])
            if channel:
                try:
                    welcome_msg = settings['welcome_message'].format(
                        user=member.mention,
                        guild=member.guild.name
                    )
                    await channel.send(welcome_msg)
                except Exception as e:
                    print(f"Error sending welcome message: {e}")

# -- Slash Commands --
@bot.tree.command(name="chat", description="Chat with the AI bot")
async def chat_command(interaction: discord.Interaction, message: str):
    """Slash command to chat with the bot."""
    # Handle both guild and DM contexts
    if interaction.guild:
        guild_id = interaction.guild.id
        is_nsfw_mode = server_modes.get(guild_id, False)
    else:
        # For DMs, default to SFW mode
        is_nsfw_mode = False
    
    await interaction.response.defer()  # Let Discord know we're processing
    
    try:
        ctx_id = _context_id_from_interaction(interaction)
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id) if interaction.guild else None
        channel_id = str(interaction.channel.id)
        
        # Enforce NSFW constraints
        if is_nsfw_mode:
            channel_is_nsfw = getattr(interaction.channel, 'is_nsfw', lambda: False)()
            if not channel_is_nsfw:
                return await interaction.followup.send("❌ NSFW mode is only available in channels marked NSFW by Discord.")
            if user_id not in nsfw_attested_users:
                return await interaction.followup.send("❌ You must self-attest you are 18+. Use `/attest`.")

        # Get RAG-enhanced response
        response, model_used, rag_context = await enhanced_model_manager.get_chat_response_with_rag(
            prompt=message,
            user_id=user_id,
            context_id=ctx_id,
            is_nsfw=is_nsfw_mode,
            guild_id=guild_id,
            channel_id=channel_id,
            system_override=global_persona
        )
        
        # Realistic typing delay based on response length
        response_length = len(response)
        if response_length < 50:
            typing_delay = 1.0
        elif response_length < 200:
            typing_delay = 2.0
        else:
            typing_delay = 3.0
        
        await asyncio.sleep(typing_delay)
        await interaction.followup.send(response)
        
        # Create context summary if conversation is getting long
        if len(rag_context.conversation_history) > 10:
            await enhanced_model_manager.create_context_summary(ctx_id, user_id)
        
    except Exception as e:
        print(f"Error in chat command: {e}")
        await interaction.followup.send("❌ Sorry, I encountered an error. Please try again.")

@bot.tree.command(name="model", description="Set your preferred AI model")
async def model_command(interaction: discord.Interaction, model_name: str = None):
    """Slash command to set or view preferred model."""
    user_id = str(interaction.user.id)
    
    if model_name:
        # Find model by name
        actual_model_id = enhanced_model_manager.find_model_by_name(model_name)
        if not actual_model_id:
            available_models = [model.name for model in enhanced_model_manager.get_available_models()]
            return await interaction.response.send_message(
                f"❌ Model '{model_name}' not found.\n\nAvailable models:\n" + 
                "\n".join([f"• {name}" for name in available_models[:10]])
            )
        
        # Update user preference
        success = enhanced_model_manager.set_user_preference(user_id, actual_model_id)
        if success:
            model_info = enhanced_model_manager.get_model_info(actual_model_id)
            await interaction.response.send_message(
                f"✅ Your preferred model is now set to: **{model_info.name}**"
            )
        else:
            await interaction.response.send_message("❌ Failed to set model preference.")
    else:
        # Show current model
        current_model = enhanced_model_manager.get_user_preference(user_id)
        model_info = enhanced_model_manager.get_model_info(current_model)
        if model_info:
            await interaction.response.send_message(
                f"🤖 Your current model: **{model_info.name}**\n"
                f"📝 Description: {model_info.description}"
            )
        else:
            await interaction.response.send_message("❌ No model preference set.")

@bot.tree.command(name="models", description="List all available AI models")
async def models_command(interaction: discord.Interaction):
    """Slash command to list all available models."""
    models = enhanced_model_manager.get_available_models()
    
    if not models:
        return await interaction.response.send_message("❌ No models available.")
    
    embed = discord.Embed(
        title="🤖 Available AI Models",
        description="Here are all the AI models you can use:",
        color=0x00ff00
    )
    
    for model in models[:10]:  # Limit to first 10 models
        status_emoji = "🟢" if model.status.value == "online" else "🔴"
        cost_text = "Free" if model.cost_per_1k_tokens == 0 else f"${model.cost_per_1k_tokens}/1k tokens"
        
        embed.add_field(
            name=f"{status_emoji} {model.name}",
            value=f"**Provider:** {model.provider.value.title()}\n"
                  f"**Cost:** {cost_text}\n"
                  f"**Max Tokens:** {model.max_tokens:,}\n"
                  f"**Description:** {model.description[:100]}...",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="persona", description="Set your conversation style")
async def persona_command(interaction: discord.Interaction, style: str = None):
    """Slash command to set conversation style."""
    user_id = str(interaction.user.id)
    
    if style:
        valid_styles = ["friendly", "professional", "casual", "technical", "creative"]
        if style.lower() not in valid_styles:
            return await interaction.response.send_message(
                f"❌ Invalid style. Choose from: {', '.join(valid_styles)}"
            )
        
        await enhanced_model_manager.update_user_preferences(
            user_id=user_id,
            conversation_style=style.lower()
        )
        
        await interaction.response.send_message(
            f"✅ Your conversation style is now set to: **{style.title()}**"
        )
    else:
        # Show current style
        user_context = context_manager.db.get_user_context(user_id)
        current_style = user_context.conversation_style if user_context else "friendly"
        await interaction.response.send_message(
            f"🎭 Your current conversation style: **{current_style.title()}**\n\n"
            f"Available styles: {', '.join(valid_styles)}"
        )

@bot.tree.command(name="attest", description="Self-attest you are 18+ for NSFW content")
async def attest_command(interaction: discord.Interaction):
    """Slash command for NSFW self-attestation."""
    user_id = str(interaction.user.id)
    
    if user_id in nsfw_attested_users:
        await interaction.response.send_message("✅ You are already attested for NSFW content.")
    else:
        nsfw_attested_users.add(user_id)
        _save_nsfw_attestations()
        await interaction.response.send_message(
            "✅ You have self-attested that you are 18+. You can now access NSFW content in appropriate channels."
        )

@bot.tree.command(name="rag", description="Add knowledge to the bot's memory")
async def rag_command(interaction: discord.Interaction, title: str, content: str, category: str = "general"):
    """Slash command to add knowledge to RAG system."""
    user_id = str(interaction.user.id)
    
    try:
        entry_id = await enhanced_model_manager.add_knowledge_entry(
            title=title,
            content=content,
            category=category,
            user_id=user_id,
            source="user_input"
        )
        
        await interaction.response.send_message(
            f"✅ Added knowledge entry: **{title}**\n"
            f"📝 Content: {content[:100]}{'...' if len(content) > 100 else ''}\n"
            f"🏷️ Category: {category}"
        )
    except Exception as e:
        print(f"Error adding knowledge entry: {e}")
        await interaction.response.send_message("❌ Failed to add knowledge entry.")

@bot.tree.command(name="stats", description="View your conversation statistics")
async def stats_command(interaction: discord.Interaction):
    """Slash command to view user statistics."""
    user_id = str(interaction.user.id)
    
    try:
        stats = enhanced_model_manager.get_user_stats(user_id)
        user_stats = stats['user_stats']
        
        embed = discord.Embed(
            title="📊 Your Statistics",
            color=0x00ff00
        )
        
        embed.add_field(
            name="💬 Messages",
            value=f"Total: {user_stats['total_messages']}\n"
                  f"User: {user_stats['user_messages']}\n"
                  f"Assistant: {user_stats['assistant_messages']}",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Contexts",
            value=f"Unique: {user_stats['unique_contexts']}\n"
                  f"NSFW: {user_stats['nsfw_messages']}",
            inline=True
        )
        
        embed.add_field(
            name="🤖 Models Used",
            value=", ".join(user_stats['models_used'][:5]) or "None",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        await interaction.response.send_message("❌ Failed to get statistics.")

# -- Regular Commands (for backward compatibility) --
@bot.command(name="chat")
async def chat_legacy(ctx, *, message: str):
    """Legacy chat command for backward compatibility."""
    # Convert to slash command format
    class MockInteraction:
        def __init__(self, ctx, message):
            self.guild = ctx.guild
            self.user = ctx.author
            self.channel = ctx.channel
            self.response = MockResponse()
            self.followup = MockFollowup()
            self._message = message
        
        async def defer(self):
            pass
    
    class MockResponse:
        async def send_message(self, content):
            await ctx.send(content)
    
    class MockFollowup:
        async def send(self, content):
            await ctx.send(content)
    
    mock_interaction = MockInteraction(ctx, message)
    await chat_command(mock_interaction, message)

# -- Music Commands (unchanged) --
# Include all music commands from the original main.py
# ... (music commands would be included here)

# -- Admin Commands --
@bot.tree.command(name="sync_commands", description="Sync slash commands (Admin only)")
async def sync_commands(interaction: discord.Interaction):
    """Sync slash commands (admin only)"""
    if interaction.user.id != OWNER_USER_ID:
        return await interaction.response.send_message("❌ You must be the bot owner to use this command.")
    
    try:
        synced = await bot.tree.sync()
        await interaction.response.send_message(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to sync commands: {e}")

@bot.tree.command(name="cleanup", description="Clean up old data (Admin only)")
async def cleanup_command(interaction: discord.Interaction, days: int = 30):
    """Clean up old data (admin only)"""
    if interaction.user.id != OWNER_USER_ID:
        return await interaction.response.send_message("❌ You must be the bot owner to use this command.")
    
    try:
        await enhanced_model_manager.cleanup_old_data(days)
        await interaction.response.send_message(f"✅ Cleaned up data older than {days} days.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to cleanup: {e}")

# -- Message Event Handler --
@bot.event
async def on_message(message):
    """Event handler for when a message is sent."""
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Process commands
    await bot.process_commands(message)
    
    # Auto-chat functionality (if enabled for the channel)
    if message.guild and message.guild.id in auto_chat_channels:
        if message.channel.id == auto_chat_channels[message.guild.id]:
            # Process as auto-chat
            user_message = message.content.strip()
            if not user_message:
                return
            
            # Determine NSFW mode
            is_nsfw_mode = server_modes.get(message.guild.id, False)
            
            async with message.channel.typing():
                try:
                    ctx_id = _context_id_from_message(message)
                    user_id = str(message.author.id)
                    guild_id = str(message.guild.id)
                    channel_id = str(message.channel.id)
                    
                    # Enforce NSFW constraints
                    if is_nsfw_mode:
                        channel_is_nsfw = getattr(message.channel, 'is_nsfw', lambda: False)()
                        if not channel_is_nsfw:
                            return await message.reply("❌ NSFW mode is only available in channels marked NSFW by Discord.", mention_author=True)
                        if user_id not in nsfw_attested_users:
                            return await message.reply("❌ You must self-attest you are 18+. Use `!attest` or `/attest`.", mention_author=True)

                    # Get RAG-enhanced response
                    response, model_used, rag_context = await enhanced_model_manager.get_chat_response_with_rag(
                        prompt=user_message,
                        user_id=user_id,
                        context_id=ctx_id,
                        is_nsfw=is_nsfw_mode,
                        guild_id=guild_id,
                        channel_id=channel_id,
                        system_override=global_persona
                    )
                    
                    # Realistic typing delay
                    response_length = len(response)
                    if response_length < 50:
                        typing_delay = 1.0
                    elif response_length < 200:
                        typing_delay = 2.0
                    else:
                        typing_delay = 3.0
                    
                    await asyncio.sleep(typing_delay)
                    await message.reply(response, mention_author=True)
                    
                    # Create context summary if needed
                    if len(rag_context.conversation_history) > 10:
                        await enhanced_model_manager.create_context_summary(ctx_id, user_id)
                        
                except Exception as e:
                    print(f"Error in auto-chat: {e}")

# -- Bot Startup --
if __name__ == "__main__":
    print("🚀 Starting Enhanced AI Discord Bot with Database and RAG...")
    bot.run(DISCORD_TOKEN)
