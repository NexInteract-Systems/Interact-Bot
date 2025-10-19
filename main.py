import discord
import asyncio
from discord.ext import commands
import api_handler
import music
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
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # Disable default help

# -- Bot State --
# This dictionary will store the mode for each server (guild)
# True for 18+, False for Under 18
server_modes = {}
# Per-server auto chat channel mapping: guild_id -> channel_id
auto_chat_channels = {}
# Conversation memory per channel/DM: channel_id -> list of turns [{role, content}]
conversations = {}
# Global persona/system prompt applied across all channels and DMs
global_persona = GLOBAL_PERSONA if (GLOBAL_PERSONA and GLOBAL_PERSONA.strip()) else None

MAX_TURNS = 20  # cap memory per channel to avoid unbounded growth

def add_company_footer(embed: discord.Embed) -> discord.Embed:
    """Add the company footer to any embed."""
    embed.set_footer(text="Built by Interact Developments Inc. • https://interactdevelopments.me/")
    return embed

def _context_id_from_interaction(interaction: discord.Interaction):
    return interaction.channel.id if interaction.channel else None

def _context_id_from_message(message: discord.Message):
    return message.channel.id

@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
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
        activity = discord.Activity(type=discord.ActivityType.listening, name="/chat")
        await bot.change_presence(activity=activity, status=discord.Status.online)
        print(f"✅ Bot status set to: {discord.Status.online}")
        
        # Wait and try again to ensure status is set
        await asyncio.sleep(2)
        await bot.change_presence(activity=activity, status=discord.Status.online)
        print("✅ Bot status confirmed as online")
        
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

@bot.command(name='status', help='Check and set bot status (Admin only)')
@commands.has_permissions(administrator=True)
async def bot_status(ctx):
    """Check and manually set bot status."""
    try:
        # Get current status
        current_status = bot.status
        await ctx.send(f'Current bot status: {current_status}')
        
        # Try to set online status
        activity = discord.Activity(type=discord.ActivityType.listening, name="/chat")
        await bot.change_presence(activity=activity, status=discord.Status.online)
        await ctx.send('✅ Bot status set to online')
        
    except Exception as e:
        await ctx.send(f'❌ Error setting status: {e}')

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
        source = FFmpegPCMAudio(url, executable=executable, before_options=before_options, after_options=after_options)
        
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
        "`!autochat` - Set auto-chat channel"
    ]
    
    embed.add_field(
        name="💬 Chat Commands", 
        value="\n".join(chat_commands),
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
    
    # Admin Commands
    admin_commands = [
        "`!status` - Check bot status (admin only)",
        "`!sync` - Sync slash commands (admin only)"
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
        "`/join` - Join voice channel",
        "`/leave` - Leave voice channel",
        "`/play <song>` - Play music",
        "`/pause` - Pause track",
        "`/resume` - Resume track",
        "`/stop` - Stop track",
        "`/skip` - Skip track",
        "`/volume [0-100]` - Set volume",
        "`/loop` - Toggle loop",
        "`/nowplaying` - Show track info"
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
        source = FFmpegPCMAudio(url, executable=executable, before_options=before_options, after_options=after_options)
        
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
@bot.command(name='image', help='Generate an image using OpenRouter (enter a prompt)')
async def image_cmd(ctx, *, prompt: str = None):
    if not prompt:
        return await ctx.send('Usage: !image <prompt>')
    await ctx.send('🎨 Generating image...')
    try:
        img_bytes = await api_handler.generate_image_with_openrouter(prompt)
        if not img_bytes:
            return await ctx.send('❌ Failed to generate image. Check API key or try a different prompt.')
        import io
        from discord import File
        file = File(io.BytesIO(img_bytes), filename='image.png')
        await ctx.send(file=file)
    except Exception as e:
        print(f"Image generation error: {e}")
        await ctx.send('❌ Error while generating image.')

@bot.tree.command(name='image', description='Generate an image using OpenRouter')
async def image_slash(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    try:
        img_bytes = await api_handler.generate_image_with_openrouter(prompt)
        if not img_bytes:
            return await interaction.followup.send('❌ Failed to generate image. Check API key or try a different prompt.')
        import io
        from discord import File
        file = File(io.BytesIO(img_bytes), filename='image.png')
        await interaction.followup.send(file=file)
    except Exception as e:
        print(f"Image generation error: {e}")
        await interaction.followup.send('❌ Error while generating image.')

@bot.command(name='togglemode', help='Toggles the chat mode between 18+ and Under 18.')
@commands.has_permissions(administrator=True) # Only administrators can change the mode
async def toggle_mode(ctx):
    """Toggles the chat mode for the server."""
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

@toggle_mode.error
async def toggle_mode_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Sorry, you must be an administrator to use this command.")

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
        history = conversations.get(ctx_id, [])
        sys_override = global_persona
        response = await api_handler.get_chat_response(message, is_nsfw_mode, history=history, system_override=sys_override)
        # Update memory
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        conversations[ctx_id] = history[-MAX_TURNS:]
        await asyncio.sleep(1)  # Simulate thinking time
        await interaction.followup.send(response)
    except Exception as e:
        print(f"An error occurred: {e}")
        await interaction.followup.send("Sorry, I couldn't get a response from the API. Please try again later.")

@bot.event
async def on_message(message):
    """Event handler for when a message is sent."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process commands first
    await bot.process_commands(message)

    guild_id = message.guild.id if message.guild else None
    is_nsfw_mode = server_modes.get(guild_id, False) if guild_id else False

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
            response = await api_handler.get_chat_response(user_message, is_nsfw_mode, history=history, system_override=sys_override)
            # Update memory
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": response})
            conversations[ctx_id] = history[-MAX_TURNS:]
            await asyncio.sleep(0.3)
            await message.reply(response, mention_author=True)
        except Exception as e:
            print(f"An error occurred: {e}")
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
