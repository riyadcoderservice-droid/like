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
from aiohttp import web

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION - EDIT THESE VALUES
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN = "8535184265:AAEsBNmUY1I6GBuQd33yAGjCW-Cmk1WPWJ4"          # Get from @BotFather
ADMIN_ID = 6417430059                        # Your Telegram numeric ID

# Single API Config (Used for all regions like BD, IND, etc.)
API_BASE = "https://frexy-x-like.onrender.com"
API_KEY = "FREXY"                            # Keep blank "" if there is no key

# Pre-Authorized Groups/Channels list (These don't need manual /allow command)
PRE_AUTHORIZED_GROUPS = [
    -1003765179070,                          # Replace with your actual Channel/Group Chat ID
]

# Required channels users MUST join
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
    "👑", "🎓", "🎖️", "🏅", "🥇", "🥈", "🥉", "🎁",
    "🎀", "🎊", "🎉", "🎈", "🎄", "🎃", "🎅", "🤖",
    "👾", "👽", "🛸", "🌍", "🌎", "🌏", "🌕", "☀️",
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
    "target_like": os.path.join(DATA_DIR, "target_like.json"),
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
        except Exception:
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
    """Check if group is allowed (Pre-authorized lists always return True)"""
    if chat_id in PRE_AUTHORIZED_GROUPS:
        return True
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


def add_auto_like(uid, region, days):
    """Add UID to auto-like list with duration in days"""
    auto = load_data("auto_like")
    auto[str(uid)] = {
        "region": region.upper(),
        "days_left": int(days),
        "added_at": datetime.now().isoformat()
    }
    save_data("auto_like", auto)


def remove_auto_like(uid):
    """Remove UID from auto-like list"""
    auto = load_data("auto_like")
    if str(uid) in auto:
        del auto[str(uid)]
        save_data("auto_like", auto)


def get_auto_like_list():
    """Get all auto-like UIDs"""
    return load_data("auto_like")


def add_target_like(uid, region, target_limit):
    """Add UID with target likes limit"""
    targets = load_data("target_like")
    targets[str(uid)] = {
        "region": region.upper(),
        "target_limit": int(target_limit),
        "likes_sent": 0,
        "added_at": datetime.now().isoformat()
    }
    save_data("target_like", targets)


def remove_target_like(uid):
    """Remove UID from target like list"""
    targets = load_data("target_like")
    if str(uid) in targets:
        del targets[str(uid)]
        save_data("target_like", targets)


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
    """Call the Free Fire Like API - Safe error handling without leaking URLs"""
    try:
        url = f"{API_BASE.rstrip('/')}/like"
        params = {
            "uid": str(uid),
            "server_name": region.upper(),
        }
        
        # Include API Key parameter only if it is set and not empty
        if API_KEY and API_KEY.strip():
            params["key"] = API_KEY
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                if resp.status != 200:
                    logger.error(f"API HTTP Error: Status code {resp.status}")
                    return {"error": "API is currently not working or returned invalid status.", "status": 0}
                
                data = await resp.json()
                return data
    except Exception as e:
        # Save actual error details to the internal logs (hidden from Telegram users)
        logger.error(f"Internal API Connection Error: {e}")
        # Return a generic safe message
        return {"error": "API is currently not working or under maintenance.", "status": 0}


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
    """Handle /help command with distinct admin and user views"""
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)

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
            f"{emoji} FREXY AUTO LIKE - ADMIN PANEL {emoji}\n\n"
            f"🔐 Admin Commands:\n"
            f"/allow <group_id> - Allow bot in group\n"
            f"/removegroup <group_id> - Remove group\n"
            f"/add <name> <link> - Add verify channel\n"
            f"/removechannel <name> - Remove channel\n"
            f"/broadcast <message> - Message all users\n"
            f"/unlimit <uid> <region> - Unlimited likes\n"
            f"/removeunlimit <uid> - Remove unlimited\n"
            f"/autolike <region> <uid> <days> - Auto daily like\n"
            f"/removeauto <uid> - Remove auto like\n"
            f"/autolist - List auto-like UIDs\n"
            f"/tlike <region> <uid> <target_limit> - Daily like until target\n"
            f"/removetlike <uid> - Remove target like\n"
            f"/tlist - List target likes\n"
            f"/stats - Bot statistics\n"
            f"/grouplist - Allowed groups\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
    else:
        text = (
            f"{emoji} FREXY AUTO LIKE - USER MENU {emoji}\n\n"
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
    """Handle /like command - Works in Allowed or Pre-Authorized Groups"""
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)
    emoji = get_user_emoji(user.id)

    if chat.type == "private" and not is_admin(user.id):
        text = (
            "❌ ACCESS DENIED!\n\n"
            "This bot is only allowed inside authorized groups.\n"
            "Private usage is restricted to administrators."
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

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

    if len(context.args) < 2:
        text = (
            f"{emoji} WRONG COMMAND! {emoji}\n\n"
            f"✅ Correct Format:\n"
            f"/like <region> <uid>\n\n"
            f"📌 Examples:\n"
            f"/like BD 123456789\n"
            f"/like IND 987654321\n\n"
            f"🌍 Valid Regions: BD, IND, BR, US, SAC, NA, RU\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    region = context.args[0].upper()
    uid = context.args[1]

    if region not in VALID_REGIONS:
        text = (
            f"{emoji} INVALID REGION! {emoji}\n\n"
            f"🌍 Valid Regions:\n"
            f"BD, IND, BR, US, SAC, NA, RU\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    if not uid.isdigit():
        text = (
            f"{emoji} INVALID UID! {emoji}\n\n"
            f"UID must be numbers only.\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    # Check if the UID is already in Auto-Like or Target-Like lists
    auto_list = get_auto_like_list()
    targets = load_data("target_like")

    if uid in auto_list:
        days_left = auto_list[uid].get("days_left", 0)
        text = (
            f"❌ REQUEST REJECTED!\n\n"
            f"This UID already has an active Auto-Like setup.\n"
            f"📅 Remaining Duration: {days_left} Days\n"
            f"Likes are delivered automatically daily."
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    if uid in targets:
        likes_sent = targets[uid].get("likes_sent", 0)
        target_limit = targets[uid].get("target_limit", 0)
        text = (
            f"❌ REQUEST REJECTED!\n\n"
            f"This UID already has an active Target-Like setup.\n"
            f"📈 Current Progress: {likes_sent}/{target_limit} Likes\n"
            f"Likes are delivered automatically daily."
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    # Channel check
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

    if not is_unlimited(uid) and not can_use_like(user.id):
        text = (
            f"{emoji} DAILY LIMIT REACHED! {emoji}\n\n"
            f"⏳ You already used your daily like!\n"
            f"🔄 Resets at 4:00 AM\n\n"
            f"⚡ POWERED BY FREXY ⚡"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    processing_text = (
        f"{emoji} PROCESSING YOUR REQUEST... {emoji}\n\n"
        f"🎮 Player UID: {uid}\n"
        f"🌍 Region: {region}\n\n"
        f"⏳ Please wait..."
    )
    msg = await update.message.reply_text(
        format_bold(processing_text), parse_mode=ParseMode.MARKDOWN
    )

    result = await send_like_api(uid, region)

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

        if not is_unlimited(uid):
            mark_like_used(user.id)

        await msg.edit_text(format_bold(success_text), parse_mode=ParseMode.MARKDOWN)
    else:
        error_text = (
            f"{emoji} FAILED! {emoji}\n\n"
            f"❌ Could not send likes. API is currently down.\n"
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
    """Handle /autolike command with format: /autolike <region> <uid> <days>"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if len(context.args) < 3:
        text = (
            "❌ WRONG FORMAT!\n\n"
            "Correct: /autolike <region> <uid> <days>\n"
            "Example: /autolike BD 123456789 30"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    region = context.args[0].upper()
    uid = context.args[1]
    days = context.args[2]

    if region not in VALID_REGIONS:
        await update.message.reply_text(
            format_bold(f"❌ Invalid Region. Available: {', '.join(VALID_REGIONS)}"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not uid.isdigit() or not days.isdigit():
        await update.message.reply_text(
            format_bold("❌ UID and Days must be numbers!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    add_auto_like(uid, region, days)
    text = (
        f"✅ AUTO LIKE ADDED!\n\n"
        f"UID: {uid}\n"
        f"Region: {region}\n"
        f"Duration: {days} Days\n"
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
            lines.append(f"🆔 {uid} | 🌍 {info.get('region', 'N/A')} | 📅 Remaining: {info.get('days_left', 0)} Days")
        text = "\n".join(lines)
        text += "\n\n⚡ POWERED BY FREXY ⚡"

    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def tlike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tlike command (Target Likes)"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if len(context.args) < 3:
        text = (
            "❌ WRONG FORMAT!\n\n"
            "Correct: /tlike <region> <uid> <target_limit>\n"
            "Example: /tlike BD 123456789 200"
        )
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    region = context.args[0].upper()
    uid = context.args[1]
    target_limit = context.args[2]

    if region not in VALID_REGIONS:
        await update.message.reply_text(
            format_bold(f"❌ Invalid Region. Available: {', '.join(VALID_REGIONS)}"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not uid.isdigit() or not target_limit.isdigit():
        await update.message.reply_text(
            format_bold("❌ UID and Target Limit must be numbers!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    add_target_like(uid, region, target_limit)
    text = (
        f"✅ TARGET LIKE ADDED!\n\n"
        f"UID: {uid}\n"
        f"Region: {region}\n"
        f"Target Limit: {target_limit} Likes\n"
        f"Will process daily at 7:00 AM until limit is reached!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def removetlike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removetlike command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        text = "❌ Correct: /removetlike <uid>"
        await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    remove_target_like(uid)
    text = (
        f"✅ UID {uid} removed from target-like list!\n\n"
        f"⚡ POWERED BY FREXY ⚡"
    )
    await update.message.reply_text(format_bold(text), parse_mode=ParseMode.MARKDOWN)


async def tlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tlist command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    targets = load_data("target_like")
    if not targets:
        text = "📋 Target-like list is empty!"
    else:
        lines = ["📋 TARGET LIKE LIST:\n"]
        for uid, info in targets.items():
            lines.append(f"🆔 {uid} | 🌍 {info.get('region', 'N/A')} | 📈 Progress: {info.get('likes_sent', 0)}/{info.get('target_limit', 0)}")
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
    targets = load_data("target_like")
    unlimited = load_data("unlimited")
    usage = load_data("daily_usage")

    text = (
        f"📊 BOT STATISTICS 📊\n\n"
        f"Total Users: {len(users)}\n"
        f"Today's Active: {len(usage)}\n"
        f"Allowed Groups: {len(groups)}\n"
        f"Channels: {len(channels)}\n"
        f"Auto-Like UIDs: {len(auto_list)}\n"
        f"Target-Like UIDs: {len(targets)}\n"
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
    lines = ["📋 ALLOWED GROUPS:\n"]
    
    if PRE_AUTHORIZED_GROUPS:
        lines.append("⚙️ Pre-Authorized (From Code):")
        for gid in PRE_AUTHORIZED_GROUPS:
            lines.append(f"🆔 {gid}")
        lines.append("")

    if groups:
        lines.append("📝 Manually Allowed:")
        for gid, info in groups.items():
            lines.append(f"🆔 {gid}")
    
    if len(lines) == 1:
        text = "📋 No groups allowed yet!"
    else:
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
        logger.info(f"Next daily reset scheduled in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)
        reset_daily_usage()


async def run_auto_like(application):
    """Send auto likes and target likes daily at 7:00 AM with log delivery to Admin Chat"""
    while True:
        now = datetime.now()
        target = now.replace(hour=AUTO_LIKE_HOUR, minute=AUTO_LIKE_MINUTE, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info(f"Next scheduled auto-like run in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)

        # Admin Log summary buffer
        admin_report = ["📢 DAILY AUTO-LIKE REPORT 📢\n"]
        has_auto = False
        has_target = False

        # ----------------------------------------------------
        # Part 1: Auto Likes (Duration / Days based)
        # ----------------------------------------------------
        auto_list = get_auto_like_list()
        updated_auto_list = {}
        
        if auto_list:
            admin_report.append("📅 ACTIVE AUTO LIKES STATUS:")
            has_auto = True
            
        for uid, info in list(auto_list.items()):
            days_left = info.get("days_left", 0)
            if days_left <= 0:
                continue

            region = info.get("region", "BD")
            status_text = ""
            try:
                result = await send_like_api(uid, region)
                if result.get("status") in [1, 2]:
                    logger.info(f"Auto-like successfully sent to {uid} ({region})")
                    status_text = "✅ SUCCESS"
                else:
                    err_msg = result.get("error", "API Failed")
                    logger.error(f"Auto-like failed for {uid}: {err_msg}")
                    status_text = f"❌ FAILED"
            except Exception as e:
                logger.error(f"Auto-like run-error for {uid}: {e}")
                status_text = f"❌ ERROR"

            # Decrement days left
            new_days = days_left - 1
            if new_days > 0:
                info["days_left"] = new_days
                updated_auto_list[uid] = info
                admin_report.append(f"• UID: {uid} | {region} | Status: {status_text} | Days Left: {new_days}")
            else:
                logger.info(f"Auto-like duration expired for UID: {uid}")
                admin_report.append(f"• UID: {uid} | {region} | Status: {status_text} | Status: EXPIRED/REMOVED")
            
            await asyncio.sleep(1.5)  # API request interval delay
        
        save_data("auto_like", updated_auto_list)

        # Formatting space between logs
        admin_report.append("")

        # ----------------------------------------------------
        # Part 2: Target Likes (Target count limit based)
        # ----------------------------------------------------
        targets = load_data("target_like")
        updated_targets = {}
        
        if targets:
            admin_report.append("📈 ACTIVE TARGET LIKES STATUS:")
            has_target = True
            
        for uid, info in list(targets.items()):
            target_limit = info.get("target_limit", 0)
            likes_sent = info.get("likes_sent", 0)

            if likes_sent >= target_limit:
                continue

            region = info.get("region", "BD")
            status_text = ""
            try:
                result = await send_like_api(uid, region)
                if result.get("status") in [1, 2]:
                    logger.info(f"Target-like successfully sent to {uid} ({region})")
                    likes_sent += 1
                    status_text = "✅ SUCCESS"
                else:
                    err_msg = result.get("error", "API Failed")
                    logger.error(f"Target-like failed for {uid}: {err_msg}")
                    status_text = f"❌ FAILED"
            except Exception as e:
                logger.error(f"Target-like run-error for {uid}: {e}")
                status_text = f"❌ ERROR"

            # Save status or discard if target limit reached
            if likes_sent < target_limit:
                info["likes_sent"] = likes_sent
                updated_targets[uid] = info
                admin_report.append(f"• UID: {uid} | {region} | Status: {status_text} | Progress: {likes_sent}/{target_limit}")
            else:
                logger.info(f"Target limit ({target_limit}) reached successfully for UID: {uid}")
                admin_report.append(f"• UID: {uid} | {region} | Status: {status_text} | Status: TARGET REACHED/REMOVED")
            
            await asyncio.sleep(1.5)

        save_data("target_like", updated_targets)

        # Send report to Admin via private chat if any job is registered
        if has_auto or has_target:
            admin_report.append("⚡ POWERED BY FREXY ⚡")
            report_text = "\n".join(admin_report)
            try:
                await application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=format_bold(report_text),
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info("Daily admin report sent successfully.")
            except Exception as e:
                logger.error(f"Failed to send Admin private report: {e}")


# ═══════════════════════════════════════════════════════════════════
# MAIN (Async Server Startup)
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
    application.add_handler(CommandHandler("tlike", tlike_cmd))
    application.add_handler(CommandHandler("removetlike", removetlike_cmd))
    application.add_handler(CommandHandler("tlist", tlist_cmd))
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

    # Render Port Binding Setup
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running successfully!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Port binding web server started on port {port}")

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
