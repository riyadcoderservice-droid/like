#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           FREXY AUTO LIKE - Telegram Bot                         ║
║           Free Fire Auto Like Bot                                ║
║           POWERED BY FREXY                                       ║
╚══════════════════════════════════════════════════════════════════╝

RENDER DEPLOY READY - Token & ID hardcoded below
No environment variables needed!
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

# ═══════════════════════════════════════════════════════════════════
# 🔴 EDIT THESE 2 VALUES ONLY - THEN DEPLOY TO RENDER
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN = "8535184265:AAF-Tav70c7KDvTGyuaqX6hEDfeH_TDRA4o"   # ← Tomar BotFather token ekhane boshao
ADMIN_ID = 6417430059                                  # ← Tomar Telegram ID ekhane boshao

# ═══════════════════════════════════════════════════════════════════
# API CONFIG (Already set - change only if needed)
# ═══════════════════════════════════════════════════════════════════

API_KEY = "JMLB"
API_BASE = "https://samiullike-production.up.railway.app"

# Required channels users MUST join (edit your 2 channel links here)
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
# EMOJI POOL
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
# DATA MANAGER
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
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def get_user_emoji(user_id):
    users = load_data("users")
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"emoji": random.choice(EMOJI_POOL)}
        save_data("users", users)
    return users[uid].get("emoji", "🔥")


def get_footer():
    return "\n\n> ⚡ *POWERED BY FREXY* ⚡"


def q(text):
    lines = text.split("\n")
    quoted_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            quoted_lines.append(f"> *{stripped}*")
        else:
            quoted_lines.append(">")
    return "\n".join(quoted_lines)


def format_msg(text):
    return q(text) + get_footer()


def is_admin(user_id):
    return user_id == ADMIN_ID


def get_today():
    return datetime.now().strftime("%Y-%m-%d")


def can_use_like(user_id):
    if is_admin(user_id):
        return True
    usage = load_data("daily_usage")
    uid = str(user_id)
    today = get_today()
    if uid not in usage:
        return True
    return usage[uid].get("date") != today


def mark_like_used(user_id):
    if is_admin(user_id):
        return
    usage = load_data("daily_usage")
    uid = str(user_id)
    usage[uid] = {"date": get_today(), "count": 1}
    save_data("daily_usage", usage)


def reset_daily_usage():
    save_data("daily_usage", {})
    logger.info("Daily usage reset at 4:00 AM")


def is_group_allowed(chat_id):
    groups = load_data("groups")
    return str(chat_id) in groups


def allow_group(chat_id):
    groups = load_data("groups")
    groups[str(chat_id)] = {"allowed": True, "added_at": datetime.now().isoformat()}
    save_data("groups", groups)


def remove_group(chat_id):
    groups = load_data("groups")
    if str(chat_id) in groups:
        del groups[str(chat_id)]
        save_data("groups", groups)


def add_channel(name, link):
    channels = load_data("channels")
    channels[name] = {"link": link, "added_at": datetime.now().isoformat()}
    save_data("channels", channels)


def remove_channel(name):
    channels = load_data("channels")
    if name in channels:
        del channels[name]
        save_data("channels", channels)


def get_channels():
    return load_data("channels")


def add_auto_like(uid, region):
    auto = load_data("auto_like")
    auto[uid] = {"region": region.upper(), "added_at": datetime.now().isoformat()}
    save_data("auto_like", auto)


def remove_auto_like(uid):
    auto = load_data("auto_like")
    if uid in auto:
        del auto[uid]
        save_data("auto_like", auto)


def get_auto_like_list():
    return load_data("auto_like")


def add_unlimited(uid, region):
    unlimited = load_data("unlimited")
    unlimited[uid] = {"region": region.upper(), "added_at": datetime.now().isoformat()}
    save_data("unlimited", unlimited)


def remove_unlimited(uid):
    unlimited = load_data("unlimited")
    if uid in unlimited:
        del unlimited[uid]
        save_data("unlimited", unlimited)


def is_unlimited(uid):
    unlimited = load_data("unlimited")
    return uid in unlimited


def add_broadcast_user(user_id):
    users = load_data("broadcast_users")
    users[str(user_id)] = True
    save_data("broadcast_users", users)


def get_broadcast_users():
    users = load_data("broadcast_users")
    return [int(uid) for uid in users.keys()]


# ═══════════════════════════════════════════════════════════════════
# API CLIENT - ASYNC
# ═══════════════════════════════════════════════════════════════════

async def send_like_api(uid, region):
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
    user = update.effective_user
    add_broadcast_user(user.id)
    emoji = get_user_emoji(user.id)

    text = (
        f"{emoji} WELCOME TO FREXY AUTO LIKE {emoji}\n\n"
        f"👤 Name: {user.first_name}\n"
        f"🆔 ID: `{user.id}`\n\n"
        f"🎮 How to get likes?\n"
        f"Use: `/like <region> <uid>`\n"
        f"Example: `/like BD 123456789`\n\n"
        f"📋 Use /help for all commands"
    )
    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_broadcast_user(user.id)
    emoji = get_user_emoji(user.id)

    if is_admin(user.id):
        text = (
            f"{emoji} FREXY AUTO LIKE - ADMIN COMMANDS {emoji}\n\n"
            f"👤 User Commands:\n"
            f"`/start` - Start the bot\n"
            f"`/help` - Show this help\n"
            f"`/like <region> <uid>` - Send likes\n"
            f"   Example: `/like BD 123456789`\n\n"
            f"🔐 Admin Commands:\n"
            f"`/allow <group_id>` - Allow bot in group\n"
            f"`/removegroup <group_id>` - Remove group\n"
            f"`/add <name> <link>` - Add verify channel\n"
            f"`/removechannel <name>` - Remove channel\n"
            f"`/broadcast <message>` - Message all users\n"
            f"`/unlimit <uid> <region>` - Unlimited likes\n"
            f"`/removeunlimit <uid>` - Remove unlimited\n"
            f"`/autolike <uid> <region>` - Auto daily like\n"
            f"`/removeauto <uid>` - Remove auto like\n"
            f"`/autolist` - List auto-like UIDs\n"
            f"`/stats` - Bot statistics\n"
            f"`/grouplist` - Allowed groups"
        )
    else:
        text = (
            f"{emoji} FREXY AUTO LIKE - USER COMMANDS {emoji}\n\n"
            f"🎮 How to use:\n"
            f"`/like <region> <uid>`\n"
            f"Example: `/like BD 123456789`\n\n"
            f"🌍 Valid Regions:\n"
            f"`BD, IND, BR, US, SAC, NA, RU`\n\n"
            f"⚠️ Rules:\n"
            f"• 1 like per day per user\n"
            f"• Reset at 4:00 AM daily\n"
            f"• Must join channels to use\n"
            f"• Bot works in private chat & allowed groups"
        )

    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def like_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)
    emoji = get_user_emoji(user.id)

    if chat.type in ["group", "supergroup"]:
        if not is_group_allowed(chat.id):
            text = (
                f"{emoji} FREXY AUTO LIKE {emoji}\n\n"
                f"❌ This group is not authorized!\n"
                f"Contact admin to allow this group."
            )
            await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
            return

    if len(context.args) < 2:
        text = (
            f"{emoji} WRONG COMMAND! {emoji}\n\n"
            f"✅ Correct Format:\n"
            f"`/like <region> <uid>`\n\n"
            f"📌 Examples:\n"
            f"`/like BD 123456789`\n"
            f"`/like IND 987654321`\n"
            f"`/like BR 555666777`\n\n"
            f"🌍 Valid Regions: `BD, IND, BR, US, SAC, NA, RU`"
        )
        await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
        return

    region = context.args[0].upper()
    uid = context.args[1]

    if region not in VALID_REGIONS:
        text = (
            f"{emoji} INVALID REGION! {emoji}\n\n"
            f"🌍 Valid Regions:\n"
            f"`BD, IND, BR, US, SAC, NA, RU`\n\n"
            f"✅ Try again with correct region"
        )
        await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
        return

    if not uid.isdigit():
        text = (
            f"{emoji} INVALID UID! {emoji}\n\n"
            f"UID must be numbers only.\n"
            f"Example: `123456789`"
        )
        await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
        return

    not_joined = await check_channel_membership(user.id, context)
    if not_joined:
        text = (
            f"{emoji} VERIFICATION REQUIRED! {emoji}\n\n"
            f"❌ You must join all channels first!\n\n"
            f"📢 Join the channels below, then click Verify:"
        )
        await update.message.reply_text(
            format_msg(text),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_verify_keyboard(),
        )
        return

    if not is_unlimited(uid) and not can_use_like(user.id):
        text = (
            f"{emoji} DAILY LIMIT REACHED! {emoji}\n\n"
            f"⏳ You already used your daily like!\n"
            f"🔄 Resets at 4:00 AM\n"
            f"🕐 Come back tomorrow!"
        )
        await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
        return

    processing_text = (
        f"{emoji} PROCESSING YOUR REQUEST... {emoji}\n\n"
        f"🎮 Player UID: `{uid}`\n"
        f"🌍 Region: `{region}`\n\n"
        f"⏳ Please wait..."
    )
    msg = await update.message.reply_text(
        format_msg(processing_text), parse_mode=ParseMode.MARKDOWN
    )

    result = await send_like_api(uid, region)

    if result.get("error"):
        error_text = (
            f"{emoji} ERROR! {emoji}\n\n"
            f"❌ {result['error']}\n\n"
            f"🎮 UID: `{uid}`\n"
            f"🌍 Region: `{region}`"
        )
        await msg.edit_text(format_msg(error_text), parse_mode=ParseMode.MARKDOWN)
        return

    if result.get("status") in [1, 2]:
        player_name = result.get("PlayerNickname", "Unknown")
        likes_before = result.get("LikesbeforeCommand", "N/A")
        likes_after = result.get("LikesafterCommand", "N/A")
        likes_given = result.get("LikesGivenByAPI", 0)
        remains = result.get("remains", "N/A")
        success_count = result.get("success_count", 0)

        text = (
            f"{emoji} LIKE SENT SUCCESSFULLY! {emoji}\n\n"
            f"👤 Player Name: `{player_name}`\n"
            f"🆔 UID: `{uid}`\n"
            f"🌍 Region: `{region}`\n\n"
            f"📊 Like Results:\n"
            f"❤️ Before: `{likes_before}`\n"
            f"❤️ After: `{likes_after}`\n"
            f"🔥 Likes Given: `{likes_given}`\n"
            f"✅ Success: `{success_count}` accounts\n"
            f"📦 Remains: `{remains}`"
        )

        if not is_unlimited(uid):
            mark_like_used(user.id)

        await msg.edit_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
    else:
        error_text = (
            f"{emoji} FAILED! {emoji}\n\n"
            f"❌ Could not send likes\n"
            f"🎮 UID: `{uid}`\n"
            f"🌍 Region: `{region}`"
        )
        await msg.edit_text(format_msg(error_text), parse_mode=ParseMode.MARKDOWN)


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    emoji = get_user_emoji(user.id)

    not_joined = await check_channel_membership(user.id, context)
    if not_joined:
        text = (
            f"{emoji} NOT VERIFIED! {emoji}\n\n"
            f"❌ You haven't joined all channels yet!\n"
            f"📢 Join all channels first, then click Verify again."
        )
        await query.edit_message_text(
            format_msg(text),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_verify_keyboard(),
        )
    else:
        text = (
            f"{emoji} VERIFIED SUCCESSFULLY! {emoji}\n\n"
            f"✅ You can now use the bot!\n\n"
            f"🎮 Use `/like <region> <uid>` to get likes"
        )
        await query.edit_message_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════
# ADMIN COMMANDS
# ═══════════════════════════════════════════════════════════════════

async def allow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if not context.args:
        text = "❌ WRONG FORMAT!\n\n✅ Correct: `/allow <group_id>`\nExample: `/allow -1001234567890`"
        await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
        return

    group_id = context.args[0]
    allow_group(group_id)
    text = f"✅ GROUP ALLOWED!\n\n🆔 Group ID: `{group_id}`\n🤖 Bot will now work in this group!"
    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def removegroup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if not context.args:
        await update.message.reply_text(format_msg("❌ Correct: `/removegroup <group_id>`"), parse_mode=ParseMode.MARKDOWN)
        return

    group_id = context.args[0]
    remove_group(group_id)
    await update.message.reply_text(format_msg(f"✅ Group `{group_id}` removed!"), parse_mode=ParseMode.MARKDOWN)


async def addchannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if len(context.args) < 2:
        text = "❌ WRONG FORMAT!\n\n✅ Correct: `/add <button_name> <channel_link>`\nExample: `/add MyChannel https://t.me/mychannel`"
        await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
        return

    name = context.args[0]
    link = context.args[1]
    add_channel(name, link)
    text = f"✅ CHANNEL ADDED!\n\n📢 Name: `{name}`\n🔗 Link: {link}"
    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def removechannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if not context.args:
        await update.message.reply_text(format_msg("❌ Correct: `/removechannel <name>`"), parse_mode=ParseMode.MARKDOWN)
        return

    name = context.args[0]
    remove_channel(name)
    await update.message.reply_text(format_msg(f"✅ Channel `{name}` removed!"), parse_mode=ParseMode.MARKDOWN)


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if not context.args:
        await update.message.reply_text(format_msg("❌ Correct: `/broadcast <message>`"), parse_mode=ParseMode.MARKDOWN)
        return

    message = " ".join(context.args)
    users = get_broadcast_users()
    sent = 0
    failed = 0

    status_msg = await update.message.reply_text(format_msg("📢 Broadcasting..."), parse_mode=ParseMode.MARKDOWN)

    for uid in users:
        try:
            text = f"📢 MESSAGE FROM ADMIN 📢\n\n{message}"
            await context.bot.send_message(uid, format_msg(text), parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed for {uid}: {e}")

    text = f"✅ BROADCAST COMPLETE!\n\n📤 Sent: `{sent}`\n❌ Failed: `{failed}`"
    await status_msg.edit_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def unlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if len(context.args) < 2:
        text = "❌ WRONG FORMAT!\n\n✅ Correct: `/unlimit <uid> <region>`\nExample: `/unlimit 123456789 BD`"
        await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    region = context.args[1].upper()
    add_unlimited(uid, region)
    text = f"✅ UNLIMITED LIKE ADDED!\n\n🆔 UID: `{uid}`\n🌍 Region: `{region}`\n♾️ No daily limit for this UID!"
    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def removeunlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if not context.args:
        await update.message.reply_text(format_msg("❌ Correct: `/removeunlimit <uid>`"), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    remove_unlimited(uid)
    await update.message.reply_text(format_msg(f"✅ UID `{uid}` removed from unlimited list!"), parse_mode=ParseMode.MARKDOWN)


async def autolike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if len(context.args) < 2:
        text = "❌ WRONG FORMAT!\n\n✅ Correct: `/autolike <uid> <region>`\nExample: `/autolike 123456789 BD`"
        await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    region = context.args[1].upper()
    add_auto_like(uid, region)
    text = f"✅ AUTO LIKE ADDED!\n\n🆔 UID: `{uid}`\n🌍 Region: `{region}`\n⏰ Daily like at 7:00 AM!"
    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def removeauto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    if not context.args:
        await update.message.reply_text(format_msg("❌ Correct: `/removeauto <uid>`"), parse_mode=ParseMode.MARKDOWN)
        return

    uid = context.args[0]
    remove_auto_like(uid)
    await update.message.reply_text(format_msg(f"✅ UID `{uid}` removed from auto-like list!"), parse_mode=ParseMode.MARKDOWN)


async def autolist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    auto_list = get_auto_like_list()
    if not auto_list:
        text = "📋 Auto-like list is empty!"
    else:
        lines = ["📋 AUTO LIKE LIST:\n"]
        for uid, info in auto_list.items():
            lines.append(f"🆔 `{uid}` | 🌍 `{info.get('region', 'N/A')}`")
        text = "\n".join(lines)

    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    users = load_data("broadcast_users")
    groups = load_data("groups")
    channels = get_channels()
    auto_list = get_auto_like_list()
    unlimited = load_data("unlimited")
    usage = load_data("daily_usage")

    text = (
        f"📊 BOT STATISTICS 📊\n\n"
        f"👥 Total Users: `{len(users)}`\n"
        f"👥 Today's Active: `{len(usage)}`\n"
        f"🏢 Allowed Groups: `{len(groups)}`\n"
        f"📢 Channels: `{len(channels)}`\n"
        f"🔄 Auto-Like UIDs: `{len(auto_list)}`\n"
        f"♾️ Unlimited UIDs: `{len(unlimited)}`"
    )
    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


async def grouplist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(format_msg("❌ You are not authorized!"), parse_mode=ParseMode.MARKDOWN)
        return

    groups = load_data("groups")
    if not groups:
        text = "📋 No groups allowed yet!"
    else:
        lines = ["📋 ALLOWED GROUPS:\n"]
        for gid, info in groups.items():
            lines.append(f"🆔 `{gid}`")
        text = "\n".join(lines)

    await update.message.reply_text(format_msg(text), parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════
# SCHEDULER
# ═══════════════════════════════════════════════════════════════════

async def run_daily_reset(application):
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
    while True:
        now = datetime.now()
        target = now.replace(hour=AUTO_LIKE_HOUR, minute=AUTO_LIKE_MINUTE, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info(f"Next auto-like in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)

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
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║           FREXY AUTO LIKE - Starting on Render...                ║
    ║           Token: Hardcoded in file                               ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("like", like_cmd))
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
    application.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_channels$"))

    asyncio.get_event_loop().create_task(run_daily_reset(application))
    asyncio.get_event_loop().create_task(run_auto_like(application))

    print("✅ Bot is running on Render! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
