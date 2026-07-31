#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           FREXY AUTO LIKE - Telegram Bot                         ║
║           Free Fire Auto Like Bot                                ║
║           POWERED BY FREXY                                       ║
╚══════════════════════════════════════════════════════════════════╝

Setup:
1. pip install python-telegram-bot aiohttp
2. Fill in BOT_TOKEN and ADMIN_ID below
3. Add your channel links in REQUIRED_CHANNELS
4. python main.py
"""

import os
import json
import random
import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from aiohttp import web  # Render port binding-এর জন্য প্রয়োজনীয়

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION - EDIT THESE VALUES
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN = "8535184265:AAEsBNmUY1I6GBuQd33yAGjCW-Cmk1WPWJ4"          # Get from @BotFather
ADMIN_ID = 6417430059                        # Your Telegram numeric ID
API_KEY = "FREXY"                            # API Key (already set)
API_BASE = "https://frexy-x-admin-like-server.vercel.app"

# Required channels users MUST join (add your 2 channel links here)
REQUIRED_CHANNELS = [
    {"name": "Channel 1", "link": "https://t.me/FREXY_OFC"},
    {"name": "Channel 2", "link": "https://t.me/FREXY_CHATS"},
]

# Daily reset time (4:00 AM)
RESET_HOUR = 4
RESET_MINUTE = 0

# Auto-like time (7:00 AM)
AUTO_LIKE_HOUR = 7
AUTO_LIKE_MINUTE = 0

# Valid Free Fire regions
VALID_REGIONS = ["BD", "IND", "BR", "US", "SAC", "NA", "RU"]

# ═══════════════════════════════════════════════════════════════════
# EMOJI POOL - Random emojis for each user
# ═══════════════════════════════════════════════════════════════════

EMOJI_POOL = [
    "🔥", "⚡", "🎯", "🏆", "💎", "🚀", "⭐", "💥",
    "🎮", "🎲", "🎪", "🎭", "🎨", "🎰", "🎱", "🎳",
    "🎸", "🎺", "🎻", "🎹", "🎷", "🎤", "🎧", "🎬",
    "🌟", "✨", "💫", "🌠", "🌈", "☄️", "🔮", "💀",
    "👑", "🎓", "🎖️", "🏅", "🥇", "🥈", "🥉", "🏆",
    "🎁", "🎀", "🎊", "🎉", "🎈", "🎄", "🎃", "🎅",
    "🤖", "👾", "👽", "🛸", "🚀", "🛰️", "🌍", "🌎",
    "🌏", "🌕", "🌙", "☀️", "⭐", "🌟", "💫", "✨",
]

# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# DATA MANAGER - JSON File Storage
# ═══════════════════════════════════════════════════════════════════

DATA_DIR = "bot_data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "users": os.path.join(DATA_DIR, "users.json"),
    "groups": os.path.join(DATA_DIR, "groups.json"),
    "channels": os.path.join(DATA_DIR, "channels.json"),
    "auto_like": os.path.join(DATA_DIR, "auto_like.json"),
    "daily_usage": os.path.join(DATA_DIR, "daily_usage.json"),
    "unlimited": os.path.join(DATA_DIR, "unlimited.json"),
    "broadcast_users": os.path.join(DATA_DIR, "broadcast_users.json"),
}


def load_data(key):
    path = FILES.get(key)
    if not path:
        return {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_data(key, data):
    path = FILES.get(key)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════
# FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════════════

def format_bold(text):
    """Format text so that every non-empty line is styled in bold (*bold*) with absolutely NO blockquotes (>)"""
    lines = text.split("\n")
    formatted_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            # Remove existing formatting and quote symbols to ensure clean rendering
            clean = stripped.replace("*", "").replace("_", "").replace(">", "").strip()
            if clean:
                formatted_lines.append(f"*{clean}*")
            else:
                formatted_lines.append("")
        else:
            formatted_lines.append("")
    return "\n".join(formatted_lines)


def is_admin(user_id):
    return user_id == ADMIN_ID


def get_today():
    return datetime.now().strftime("%Y-%m-%d")


def can_use_like(user_id):
    """Check if user can use /like today - ADMIN ALWAYS BYPASSED"""
    if is_admin(user_id):
        return True
    usage = load_data("daily_usage")
    uid = str(user_id)
    today = get_today()
    if uid not in usage:
        return True
    return usage[uid].get("date") != today


def mark_like_used(user_id):
    """Mark that user has used /like today - SKIP ADMIN"""
    if is_admin(user_id):
        return
    usage = load_data("daily_usage")
    uid = str(user_id)
    usage[uid] = {"date": get_today(), "count": 1}
    save_data("daily_usage", usage)


def reset_daily_usage():
    """Reset daily usage at 4 AM"""
    save_data("daily_usage", {})
    logger.info("Daily usage reset at 4:00 AM")


def is_group_allowed(chat_id):
    """Check if group is allowed"""
    groups = load_data("groups")
    return str(chat_id) in groups


def allow_group(chat_id):
    """Allow bot to work in a group"""
    groups = load_data("groups")
    groups[str(chat_id)] = {"allowed": True, "added_at": datetime.now().isoformat()}
    save_data("groups", groups)


def remove_group(chat_id):
    """Remove group from allowed list"""
    groups = load_data("groups")
    if str(chat_id) in groups:
        del groups[str(chat_id)]
        save_data("groups", groups)


def add_channel(name, link):
    """Add verification channel"""
    channels = load_data("channels")
    channels[name] = {"link": link, "added_at": datetime.now().isoformat()}
    save_data("channels", channels)


def remove_channel(name):
    """Remove verification channel"""
    channels = load_data("channels")
    if name in channels:
        del channels[name]
        save_data("channels", channels)


def get_channels():
    """Get all verification channels"""
    return load_data("channels")


def add_auto_like(uid, region):
    """Add UID to auto-like list"""
    auto = load_data("auto_like")
    auto[uid] = {"region": region.upper(), "added_at": datetime.now().isoformat()}
    save_data("auto_like", auto)


def remove_auto_like(uid):
    """Remove UID from auto-like list"""
    auto = load_data("auto_like")
    if uid in auto:
        del auto[uid]
        save_data("auto_like", auto)


def get_auto_like_list():
    """Get all auto-like UIDs"""
    return load_data("auto_like")


def add_unlimited(uid, region):
    """Add UID to unlimited likes list"""
    unlimited = load_data("unlimited")
    unlimited[uid] = {"region": region.upper(), "added_at": datetime.now().isoformat()}
    save_data("unlimited", unlimited)


def remove_unlimited(uid):
    """Remove UID from unlimited list"""
    unlimited = load_data("unlimited")
    if uid in unlimited:
        del unlimited[uid]
        save_data("unlimited", unlimited)


def is_unlimited(uid):
    """Check if UID has unlimited likes"""
    unlimited = load_data("unlimited")
    return uid in unlimited


def add_broadcast_user(user_id):
    """Add user to broadcast list"""
    users = load_data("broadcast_users")
    users[str(user_id)] = True
    save_data("broadcast_users", users)


def get_broadcast_users():
    """Get all broadcast user IDs"""
    users = load_data("broadcast_users")
    return [int(uid) for uid in users.keys()]


def get_user_emoji(user_id):
    """Get a consistent random emoji for each user"""
    users = load_data("users")
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"emoji": random.choice(EMOJI_POOL)}
        save_data("users", users)
    return users[uid].get("emoji", "🔥")


# ═══════════════════════════════════════════════════════════════════
# FREE FIRE API CLIENT - ASYNC (FAST)
# ═══════════════════════════════════════════════════════════════════

async def send_like_api(uid, region):
    """Call the Free Fire Like API - ASYNC for speed"""
    try:
        url = f"{API_BASE}/like"
        params = {
            "key": API_KEY,
            "uid": str(uid),
            "server_name": region.upper(),
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                data = await resp.json()
                return data
    except Exception as e:
        logger.error(f"API Error: {e}")
        return {"error": str(e), "status": 0}


# ═══════════════════════════════════════════════════════════════════
# CHANNEL VERIFICATION
# ═══════════════════════════════════════════════════════════════════

async def check_channel_membership(user_id, context):
    """Check if user has joined all required channels"""
    channels = get_channels()
    if not channels:
        channels = {ch["name"]: {"link": ch["link"]} for ch in REQUIRED_CHANNELS}

    not_joined = []
    for name, info in channels.items():
        try:
            link = info.get("link", "")
            if "/" in link:
                parts = link.rstrip("/").split("/")
                username = parts[-1]
                if username.startswith("+"):
                    continue
                member = await context.bot.get_chat_member(f"@{username}", user_id)
                if member.status in ["left", "kicked"]:
                    not_joined.append({"name": name, "link": link})
            else:
                not_joined.append({"name": name, "link": link})
        except Exception as e:
            logger.error(f"Channel check error for {name}: {e}")
            not_joined.append({"name": name, "link": info.get("link", "")})

    return not_joined


def build_verify_keyboard():
    """Build verification keyboard with channel buttons"""
    channels = get_channels()
    if not channels:
        channels = {ch["name"]: {"link": ch["link"]} for ch in REQUIRED_CHANNELS}

    buttons = []
    for name, info in channels.items():
        buttons.append([InlineKeyboardButton(f"📢 Join {name}", url=info["link"])])
    buttons.append([InlineKeyboardButton("✅ Verify", callback_data="verify_channels")])
    return InlineKeyboardMarkup(buttons)


# ═══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)

    # Restriction: Admin can use private; Regular users are restricted
    if chat.type == "private" and not is_admin(user.id):
        text = (
            "❌ ACCESS DENIED!\n\n"
            "This bot is only allowed inside authorized groups.\n"
            "Private usage is restricted to administrators."
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    emoji = get_user_emoji(user.id)
    text = (
        f"{emoji} WELCOME TO FREXY AUTO LIKE {emoji}\n\n"
        f"👤 Name: {user.first_name}\n"
        f"🆔 ID: {user.id}\n\n"
        f"🎮 How to get likes?\n"
        f"Use: /like <region> <uid>\n"
        f"Example: /like BD 123456789\n\n"
        f"📋 Use /help for all commands\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)

    # Restriction: Admin can use private; Regular users are restricted
    if chat.type == "private" and not is_admin(user.id):
        text = (
            "❌ ACCESS DENIED!\n\n"
            "This bot is only allowed inside authorized groups.\n"
            "Private usage is restricted to administrators."
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    emoji = get_user_emoji(user.id)

    if is_admin(user.id):
        text = (
            f"{emoji} FREXY AUTO LIKE - ADMIN COMMANDS {emoji}\n\n"
            f"👤 User Commands:\n"
            f"/start - Start the bot\n"
            f"/help - Show this help\n"
            f"/like <region> <uid> - Send likes\n"
            f"Example: /like BD 123456789\n\n"
            f"🔐 Admin Commands:\n"
            f"/allow <group_id> - Allow bot in group\n"
            f"/removegroup <group_id> - Remove group\n"
            f"/add <name> <link> - Add verify channel\n"
            f"/removechannel <name> - Remove channel\n"
            f"/broadcast <message> - Message all users\n"
            f"/unlimit <uid> <region> - Unlimited likes\n"
            f"/removeunlimit <uid> - Remove unlimited\n"
            f"/autolike <uid> <region> - Auto daily like\n"
            f"/removeauto <uid> - Remove auto like\n"
            f"/autolist - List auto-like UIDs\n"
            f"/stats - Bot statistics\n"
            f"/grouplist - Allowed groups\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
    else:
        text = (
            f"{emoji} FREXY AUTO LIKE - USER COMMANDS {emoji}\n\n"
            f"🎮 How to use:\n"
            f"/like <region> <uid>\n"
            f"Example: /like BD 123456789\n\n"
            f"🌍 Valid Regions:\n"
            f"BD, IND, BR, US, SAC, NA, RU\n\n"
            f"⚠️ Rules:\n"
            f"• 1 like per day per user\n"
            f"• Reset at 4:00 AM daily\n"
            f"• Must join channels to use\n"
            f"• Bot works in allowed groups\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
    
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def like_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /like command - Only Works in Allowed Groups for users"""
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)
    emoji = get_user_emoji(user.id)

    # Restriction: Admin can use private; Regular users are restricted
    if chat.type == "private" and not is_admin(user.id):
        text = (
            "❌ ACCESS DENIED!\n\n"
            "This bot is only allowed inside authorized groups.\n"
            "Private usage is restricted to administrators."
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    # Check if in group and group is allowed
    if chat.type in ["group", "supergroup"]:
        if not is_group_allowed(chat.id):
            text = (
                f"{emoji} FREXY AUTO LIKE {emoji}\n\n"
                f"❌ This group is not authorized!\n"
                f"Contact admin to allow this group.\n\n"
                f"⚡ POWERED BY FREXY ⚡"
            )
            await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
            return

    # Check args
    if len(context.args) < 2:
        text = (
            f"{emoji} WRONG COMMAND! {emoji}\n\n"
            f"✅ Correct Format:\n"
            f"/like <region> <uid>\n\n"
            f"📌 Examples:\n"
            f"/like BD 123456789\n"
            f"/like IND 987654321\n"
            f"/like BR 555666777\n\n"
            f"🌍 Valid Regions: BD, IND, BR, US, SAC, NA, RU\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    region = context.args[0].upper()
    uid = context.args[1]

    # Validate region
    if region not in VALID_REGIONS:
        text = (
            f"{emoji} INVALID REGION! {emoji}\n\n"
            f"🌍 Valid Regions:\n"
            f"BD, IND, BR, US, SAC, NA, RU\n\n"
            f"✅ Try again with correct region\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    # Validate UID
    if not uid.isdigit():
        text = (
            f"{emoji} INVALID UID! {emoji}\n\n"
            f"UID must be numbers only.\n"
            f"Example: 123456789\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    # Check channel membership
    not_joined = await check_channel_membership(user.id, context)
    if not_joined:
        text = (
            f"{emoji} VERIFICATION REQUIRED! {emoji}\n\n"
            f"❌ You must join all channels first!\n\n"
            f"📢 Join the channels below, then click Verify:"
        )
        await update.message.reply_text(
            format_bold(text),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_verify_keyboard(),
        )
        return

    # Check daily limit (ADMIN BYPASSED + unlimited UIDs bypassed)
    if not is_unlimited(uid) and not can_use_like(user.id):
        text = (
            f"{emoji} DAILY LIMIT REACHED! {emoji}\n\n"
            f"⏳ You already used your daily like!\n"
            f"🔄 Resets at 4:00 AM\n"
            f"🕐 Come back tomorrow!\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    # Send processing message
    processing_text = (
        f"{emoji} PROCESSING YOUR REQUEST... {emoji}\n\n"
        f"🎮 Player UID: {uid}\n"
        f"🌍 Region: {region}\n\n"
        f"⏳ Please wait..."
    )
    msg = await update.message.reply_text(
        format_bold(processing_text), parse_mode=ParseMode.MARKDOWN
    )

    # Call API - ASYNC (FAST)
    result = await send_like_api(uid, region)

    # Handle API response
    if result.get("error"):
        error_text = (
            f"{emoji} ERROR! {emoji}\n\n"
            f"❌ {result['error']}\n\n"
            f"🎮 UID: {uid}\n"
            f"🌍 Region: {region}\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await msg.edit_text(format_bold(error_text), parse_mode=ParseMode.MARKDOWN)
        return

    if result.get("status") in [1, 2]:
        # Success Layout Matching User Format
        player_name = result.get("PlayerNickname", "Unknown")
        likes_before = result.get("LikesbeforeCommand", "N/A")
        likes_after = result.get("LikesafterCommand", "N/A")
        likes_given = result.get("LikesGivenByAPI", 0)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        success_text = (
            f"✅ Like Sent Successfully!\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Name: {player_name}\n"
            f"🌍 Server: {region}\n"
            f"📉 Before: {likes_before}\n"
            f"📈 After: {likes_after}\n"
            f"➕ Given: {likes_given}\n"
            f"🆔 UID: {uid}\n"
            f"⏰ {current_time}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ POWERED BY FREXY ⚡"
        )

        # Mark as used (only for non-unlimited + non-admin)
        if not is_unlimited(uid):
            mark_like_used(user.id)

        await msg.edit_text(format_bold(success_text), parse_mode=ParseMode.MARKDOWN)
    else:
        error_text = (
            f"{emoji} FAILED! {emoji}\n\n"
            f"❌ Could not send likes\n"
            f"🎮 UID: {uid}\n"
            f"🌍 Region: {region}\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await msg.edit_text(format_bold(error_text), parse_mode=ParseMode.MARKDOWN)


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verify button click"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    emoji = get_user_emoji(user.id)

    not_joined = await check_channel_membership(user.id, context)
    if not_joined:
        text = (
            f"❌ NOT VERIFIED!\n\n"
            f"You haven't joined all channels yet!\n"
            f"Join all channels first, then click Verify again."
        )
        await query.edit_message_text(
            format_bold(text),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_verify_keyboard(),
        )
    else:
        text = (
            f"✅ VERIFIED SUCCESSFULLY!\n\n"
            f"You can now use the bot!\n\n"
            f"Use /like <region> <uid> to get likes"
        )
        await query.edit_message_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════
# ADMIN COMMANDS
# ═══════════════════════════════════════════════════════════════════

async def allow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /allow command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        text = (
            "❌ WRONG FORMAT!\n\n"
            "Correct: /allow <group_id>\n"
            "Example: /allow -1001234567890"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    group_id = context.args[0]
    allow_group(group_id)
    text = (
        f"✅ GROUP ALLOWED!\n\n"
        f"Group ID: {group_id}\n"
        f"Bot will now work in this group!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def removegroup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removegroup command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        text = "❌ Correct: /removegroup <group_id>"
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    group_id = context.args[0]
    remove_group(group_id)
    text = (
        f"✅ Group {group_id} removed!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def addchannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if len(context.args) < 2:
        text = (
            "❌ WRONG FORMAT!\n\n"
            "Correct: /add <button_name> <channel_link>\n"
            "Example: /add MyChannel https://t.me/mychannel"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    name = context.args[0]
    link = context.args[1]
    add_channel(name, link)
    text = (
        f"✅ CHANNEL ADDED!\n\n"
        f"Name: {name}\n"
        f"Link: {link}\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def removechannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removechannel command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        text = "❌ Correct: /removechannel <name>"
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    name = context.args[0]
    remove_channel(name)
    text = (
        f"✅ Channel {name} removed!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        text = "❌ Correct: /broadcast <message>"
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    message = " ".join(context.args)
    users = get_broadcast_users()
    sent = 0
    failed = 0

    status_msg = await update.message.reply_text(
        format_bold("📢 Broadcasting..."),
        parse_mode=ParseMode.MARKDOWN,
    )

    for uid in users:
        try:
            text = (
                f"📢 MESSAGE FROM ADMIN 📢\n\n"
                f"{message}\n\n"
                f"⚡ POWERED BY FREXY ⚡"
            )
            await context.bot.send_message(
                uid, format_bold(text), parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed for {uid}: {e}")

    text = (
        f"✅ BROADCAST COMPLETE!\n\n"
        f"Sent: {sent}\n"
        f"Failed: {failed}\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await status_msg.edit_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def unlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unlimit command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if len(context.args) < 2:
        text = (
            "❌ WRONG FORMAT!\n\n"
            "Correct: /unlimit <uid> <region>\n"
            "Example: /unlimit 123456789 BD"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    region = context.args[1].upper()
    add_unlimited(uid, region)
    text = (
        f"✅ UNLIMITED LIKE ADDED!\n\n"
        f"UID: {uid}\n"
        f"Region: {region}\n"
        f"No daily limit for this UID!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def removeunlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeunlimit command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        text = "❌ Correct: /removeunlimit <uid>"
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    remove_unlimited(uid)
    text = (
        f"✅ UID {uid} removed from unlimited list!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def autolike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /autolike command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if len(context.args) < 2:
        text = (
            "❌ WRONG FORMAT!\n\n"
            "Correct: /autolike <uid> <region>\n"
            "Example: /autolike 123456789 BD"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    region = context.args[1].upper()
    add_auto_like(uid, region)
    text = (
        f"✅ AUTO LIKE ADDED!\n\n"
        f"UID: {uid}\n"
        f"Region: {region}\n"
        f"Daily like at 7:00 AM!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def removeauto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeauto command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        text = "❌ Correct: /removeauto <uid>"
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    remove_auto_like(uid)
    text = (
        f"✅ UID {uid} removed from auto-like list!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def autolist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /autolist command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    auto_list = get_auto_like_list()
    if not auto_list:
        text = "📋 Auto-like list is empty!"
    else:
        lines = ["📋 AUTO LIKE LIST:\n"]
        for uid, info in auto_list.items():
            lines.append(f"🆔 {uid} | 🌍 {info.get('region', 'N/A')}")
        text = "\n".join(lines)
        text += "\n\n⚡ POWERED BY FREXY ⚡"

    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    users = load_data("broadcast_users")
    groups = load_data("groups")
    channels = get_channels()
    auto_list = get_auto_like_list()
    unlimited = load_data("unlimited")
    usage = load_data("daily_usage")

    text = (
        f"📊 BOT STATISTICS 📊\n\n"
        f"Total Users: {len(users)}\n"
        f"Today's Active: {len(usage)}\n"
        f"Allowed Groups: {len(groups)}\n"
        f"Channels: {len(channels)}\n"
        f"Auto-Like UIDs: {len(auto_list)}\n"
        f"Unlimited UIDs: {len(unlimited)}\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def grouplist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /grouplist command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    groups = load_data("groups")
    if not groups:
        text = "📋 No groups allowed yet!"
    else:
        lines = ["📋 ALLOWED GROUPS:\n"]
        for gid, info in groups.items():
            lines.append(f"🆔 {gid}")
        text = "\n".join(lines)
        text += "\n\n⚡ POWERED BY FREXY ⚡"

    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════
# SCHEDULER - Daily Reset & Auto Like
# ═══════════════════════════════════════════════════════════════════

async def run_daily_reset(application):
    """Reset daily usage at 4:00 AM"""
    while True:
        now = datetime.now()
        target = now.replace(hour=RESET_HOUR, minute=RESET_MINUTE, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info(f"Next daily reset in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)
        reset_daily_usage()


async def run_auto_like(application):
    """Send auto likes at 7:00 AM daily"""
    while True:
        now = datetime.now()
        target = now.replace(hour=AUTO_LIKE_HOUR, minute=AUTO_LIKE_MINUTE, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info(f"Next auto-like in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)

        # Send auto likes
        auto_list = get_auto_like_list()
        for uid, info in auto_list.items():
            region = info.get("region", "BD")
            try:
                result = await send_like_api(uid, region)
                if result.get("status") in [1, 2]:
                    logger.info(f"Auto-like sent to {uid} ({region})")
                else:
                    logger.error(f"Auto-like failed for {uid}: {result.get('error')}")
            except Exception as e:
                logger.error(f"Auto-like error for {uid}: {e}")
            await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════════════
# MAIN (Render-এ রান করার জন্য Async-এ রূপান্তরিত করা হয়েছে)
# ═══════════════════════════════════════════════════════════════════

async def main_async():
    # Build application
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("like", like_cmd))

    # Admin commands
    application.add_handler(CommandHandler("allow", allow_cmd))
    application.add_handler(CommandHandler("removegroup", removegroup_cmd))
    application.add_handler(CommandHandler("add", addchannel_cmd))
    application.add_handler(CommandHandler("removechannel", removechannel_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CommandHandler("unlimit", unlimit_cmd))
    application.add_handler(CommandHandler("removeunlimit", removeunlimit_cmd))
    application.add_handler(CommandHandler("autolike", autolike_cmd))
    application.add_handler(CommandHandler("removeauto", removeauto_cmd))
    application.add_handler(CommandHandler("autolist", autolist_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("grouplist", grouplist_cmd))

    # Callback handler
    application.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_channels$"))

    # Start scheduler tasks
    asyncio.create_task(run_daily_reset(application))
    asyncio.create_task(run_auto_like(application))

    # Initialize and start Telegram Bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Telegram Bot polling started.")

    # dummy web server चालू করা (Render port binding এর জন্য)
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running successfully!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Port binding web server started on port {port}")

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║           FREXY AUTO LIKE - Starting...                          ║
    ║           Free Fire Auto Like Bot                                ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
