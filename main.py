import os
import time
import sqlite3
import random
import requests
import datetime
import threading
from telebot import TeleBot, types

# ==================== CONFIGURATION ====================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_ID = 123456789  # Replace with your Telegram User ID
DEFAULT_GROUP_ID = -100123456789  # Hardcoded default group ID

# Static channel links (Must edit these)
STATIC_CHANNELS = [
    {"username": "@Channel1Username", "link": "https://t.me/Channel1Link"},
    {"username": "@Channel2Username", "link": "https://t.me/Channel2Link"}
]

API_BASE_URL = "https://samiullike-production.up.railway.app/like" 
# Note: Adjust the endpoint path if your API uses different parameters (e.g., /api?uid=...&region=...)
# =======================================================

bot = TeleBot(BOT_TOKEN)

# Randomized Emojis for Premium UI look
EMOJIS_PROCESSING = ["⚡", "🔄", "⏳", "🚀", "🛸"]
EMOJIS_SUCCESS = ["🔥", "✨", "👑", "🎯", "💎", "👾"]

# Initialize Database
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    # Allowed groups
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_groups (
            group_id INTEGER PRIMARY KEY
        )
    """)
    # Dynamic channels for verification
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            button_name TEXT,
            link TEXT
        )
    """)
    # Daily limits (resets at 4:00 AM)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_limits (
            user_id INTEGER,
            last_date TEXT,
            PRIMARY KEY (user_id, last_date)
        )
    """)
    # Auto-like list for 7:00 AM auto runs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auto_likes (
            uid TEXT PRIMARY KEY,
            region TEXT
        )
    """)
    
    # Insert default group if not exists
    cursor.execute("INSERT OR IGNORE INTO allowed_groups (group_id) VALUES (?)", (DEFAULT_GROUP_ID,))
    conn.commit()
    conn.close()

init_db()

# ==================== HELPER FUNCTIONS ====================

def get_db_connection():
    return sqlite3.connect("bot_database.db")

def is_group_allowed(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM allowed_groups WHERE group_id = ?", (chat_id,))
    allowed = cursor.fetchone() is not None
    conn.close()
    return allowed

def check_channel_membership(user_id):
    # Check static channels
    for chan in STATIC_CHANNELS:
        try:
            member = bot.get_chat_member(chan["username"], user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            # If bot is not admin or channel username is invalid
            return False

    # Check dynamically added channels
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    dynamic_channels = cursor.fetchall()
    conn.close()

    for (chan_id,) in dynamic_channels:
        try:
            member = bot.get_chat_member(chan_id, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
            
    return True

def can_user_request(user_id):
    if user_id == ADMIN_ID:
        return True

    # Check 4:00 AM reset rule
    now = datetime.datetime.now()
    # If it is before 4 AM, the "current day" for limit is yesterday
    if now.hour < 4:
        limit_date = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        limit_date = now.strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_limits WHERE user_id = ? AND last_date = ?", (user_id, limit_date))
    record = cursor.fetchone()
    conn.close()

    return record is None

def register_user_request(user_id):
    if user_id == ADMIN_ID:
        return
    now = datetime.datetime.now()
    if now.hour < 4:
        limit_date = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        limit_date = now.strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_limits (user_id, last_date) VALUES (?, ?)", (user_id, limit_date))
    conn.commit()
    conn.close()

def send_footer(text):
    return f"{text}\n\n<b>━━━━━━━━━━━━━━━━━━━━\n⚡ POWERED BY FREXY ⚡\n━━━━━━━━━━━━━━━━━━━━</b>"

# ==================== USER COMMANDS ====================

@bot.message_handler(commands=['start', 'help'])
def help_command(message):
    help_text = (
        "<b>✨ FREXY AUTO LIKE HELP MENU ✨</b>\n\n"
        "<b>How to use the bot:</b>\n"
        "<b>Use the /like command followed by your region and your UID.</b>\n\n"
        "<b>Format:</b>\n"
        "<code>/like [region] [uid]</code>\n\n"
        "<b>Example:</b>\n"
        "<code>/like BD 123456789</code>\n"
        "<code>/like IND 987654321</code>\n\n"
        "<b>Available Regions:</b> <b>BD (Bangladesh), IND (India)</b>\n"
        "<i>Note: Users are limited to 1 request per day, which resets daily at 4:00 AM.</i>"
    )
    bot.reply_to(message, send_footer(help_text), parse_mode="HTML")


@bot.message_handler(commands=['like'])
def handle_like(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if the group is authorized
    if message.chat.type in ['group', 'supergroup'] and not is_group_allowed(chat_id):
        # Silent ignore or minimal response to prevent spam in unauthorized groups
        return

    # Check subscription status
    if not check_channel_membership(user_id):
        # Build joining links
        markup = types.InlineKeyboardMarkup()
        for idx, chan in enumerate(STATIC_CHANNELS, start=1):
            markup.add(types.InlineKeyboardButton(f"Join Channel {idx}", url=chan["link"]))
        
        # Get dynamic channels
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT button_name, link FROM channels")
        dyn_chans = cursor.fetchall()
        conn.close()

        for btn_name, link in dyn_chans:
            markup.add(types.InlineKeyboardButton(btn_name, url=link))

        markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify_join"))
        
        verify_msg = (
            "<b>🚫 ACCESS DENIED 🚫</b>\n\n"
            "<b>You must join our official channels before using this bot. Please join and click Verify below!</b>"
        )
        bot.reply_to(message, send_footer(verify_msg), reply_markup=markup, parse_mode="HTML")
        return

    # Check daily limit
    if not can_user_request(user_id):
        limit_msg = (
            "<b>⚠️ DAILY LIMIT REACHED ⚠️</b>\n\n"
            "<b>You can only request likes once a day. Your limit will reset at 4:00 AM.</b>"
        )
        bot.reply_to(message, send_footer(limit_msg), parse_mode="HTML")
        return

    # Parse parameters
    args = message.text.split()
    if len(args) != 3:
        error_msg = (
            "<b>❌ INVALID FORMAT ❌</b>\n\n"
            "<b>Please use the command correctly:</b>\n"
            "<code>/like [region] [uid]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/like BD 123456789</code>"
        )
        bot.reply_to(message, send_footer(error_msg), parse_mode="HTML")
        return

    region = args[1].upper()
    uid = args[2]

    if region not in ["BD", "IND"]:
        region_error = (
            "<b>❌ UNSUPPORTED REGION ❌</b>\n\n"
            "<b>Please specify a valid region (BD or IND).</b>"
        )
        bot.reply_to(message, send_footer(region_error), parse_mode="HTML")
        return

    # Processing state
    p_emoji = random.choice(EMOJIS_PROCESSING)
    processing_msg = bot.reply_to(
        message, 
        send_footer(f"<b>{p_emoji} Processing your like request for UID {uid}... Please wait.</b>"), 
        parse_mode="HTML"
    )

    # API Request Call
    try:
        # Assuming parameters: ?uid=...&region=...
        response = requests.get(f"{API_BASE_URL}?uid={uid}&region={region}", timeout=25)
        
        if response.status_code == 200:
            data = response.json()
            # Adjust parsed values according to your API response JSON layout
            player_name = data.get("player_name", "N/A")
            before_like = data.get("before_likes", "N/A")
            after_like = data.get("after_likes", "N/A")
            api_uid = data.get("uid", uid)
            api_region = data.get("region", region)

            # Record successfully completed request to apply limit
            register_user_request(user_id)

            s_emoji = random.choice(EMOJIS_SUCCESS)
            success_msg = (
                f"<b>{s_emoji} LIKE DELIVERED SUCCESSFULLY {s_emoji}</b>\n\n"
                f"<b>👤 Player Name:</b> <code>{player_name}</code>\n"
                f"<b>🆔 Player UID:</b> <code>{api_uid}</code>\n"
                f"<b>🌐 Region:</b> <code>{api_region}</code>\n"
                f"<b>📉 Before Likes:</b> <code>{before_like}</code>\n"
                f"<b>📈 After Likes:</b> <code>{after_like}</code>"
            )
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text=send_footer(success_msg),
                parse_mode="HTML"
            )
        else:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text=send_footer("<b>❌ API Error: Unable to complete your like request at this time.</b>"),
                parse_mode="HTML"
            )
    except Exception as e:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=processing_msg.message_id,
            text=send_footer(f"<b>❌ Connection Error: Unable to reach the service server.</b>"),
            parse_mode="HTML"
        )


@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_join_callback(call):
    user_id = call.from_user.id
    if check_channel_membership(user_id):
        bot.answer_callback_query(call.id, "✅ Verification Successful!")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=send_footer("<b>✅ VERIFICATION SUCCESSFUL!</b>\n\n<b>You can now use the /like command.</b>"),
            parse_mode="HTML"
        )
    else:
        bot.answer_callback_query(call.id, "❌ You have not joined all channels yet!", show_alert=True)

# ==================== ADMIN COMMANDS ====================

@bot.message_handler(commands=['allow'])
def allow_group(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "<b>Usage:</b> <code>/allow [group_id]</code>", parse_mode="HTML")
        return
    try:
        g_id = int(args[1])
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO allowed_groups (group_id) VALUES (?)", (g_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"<b>Success:</b> Group ID <code>{g_id}</code> is now allowed to use the bot.", parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, "<b>Error:</b> Group ID must be an integer.", parse_mode="HTML")


@bot.message_handler(commands=['add'])
def add_channel(message):
    """
    Format: /add [channel_id_or_username] [button_name] [channel_link]
    Example: /add @mychannel Join Here https://t.me/mychannel
    """
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        bot.reply_to(message, "<b>Usage:</b> <code>/add [channel_username/id] [button_name] [link]</code>", parse_mode="HTML")
        return
    
    channel_id = args[1]
    button_name = args[2]
    link = args[3]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO channels (channel_id, button_name, link) VALUES (?, ?, ?)", (channel_id, button_name, link))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"<b>Success:</b> Channel <code>{channel_id}</code> added to mandatory verification list.", parse_mode="HTML")


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast"))
    markup.add(types.InlineKeyboardButton("➕ Add Auto-Like UID", callback_data="admin_add_auto"))
    markup.add(types.InlineKeyboardButton("📋 View Auto-Like List", callback_data="admin_view_auto"))
    
    bot.reply_to(message, "<b>🛠️ FREXY ADMIN CONTROL PANEL 🛠️</b>", reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback_handler(call):
    if call.from_user.id != ADMIN_ID:
        return

    action = call.data

    if action == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "<b>Please enter the message you want to broadcast to all authorized groups:</b>", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_broadcast)
        bot.answer_callback_query(call.id)

    elif action == "admin_add_auto":
        msg = bot.send_message(call.message.chat.id, "<b>Enter UID and Region to add to the auto-like list (Format: UID REGION):</b>\nExample: <code>123456789 BD</code>", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_add_auto)
        bot.answer_callback_query(call.id)

    elif action == "admin_view_auto":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT uid, region FROM auto_likes")
        records = cursor.fetchall()
        conn.close()

        if not records:
            bot.send_message(call.message.chat.id, "<b>No UIDs configured in the auto-like database.</b>", parse_mode="HTML")
        else:
            list_text = "<b>📋 AUTO-LIKE SCHEDULED LIST:</b>\n\n"
            for r in records:
                list_text += f"• UID: <code>{r[0]}</code> | Region: <code>{r[1]}</code>\n"
            bot.send_message(call.message.chat.id, list_text, parse_mode="HTML")
        bot.answer_callback_query(call.id)

def process_broadcast(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT group_id FROM allowed_groups")
    groups = cursor.fetchall()
    conn.close()

    success_count = 0
    for (g_id,) in groups:
        try:
            bot.send_message(g_id, send_footer(f"<b>📢 ADMIN BROADCAST</b>\n\n{message.text}"), parse_mode="HTML")
            success_count += 1
            time.sleep(0.1) # Small delay to respect rate limit
        except Exception:
            continue

    bot.reply_to(message, f"<b>Broadcast sent to {success_count} group(s).</b>", parse_mode="HTML")

def process_add_auto(message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "<b>Invalid format. Process aborted.</b>", parse_mode="HTML")
            return
        uid = parts[0]
        region = parts[1].upper()

        if region not in ["BD", "IND"]:
            bot.reply_to(message, "<b>Invalid region. Must be BD or IND.</b>", parse_mode="HTML")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO auto_likes (uid, region) VALUES (?, ?)", (uid, region))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"<b>Success:</b> UID <code>{uid}</code> ({region}) added to 7:00 AM auto-like system.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "<b>Error parsing request. Process aborted.</b>", parse_mode="HTML")

# ==================== CRON JOB / SCHEDULER SYSTEM ====================

def run_auto_likes():
    """Trigger likes automatically for listed profiles"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uid, region FROM auto_likes")
    records = cursor.fetchall()
    conn.close()

    for uid, region in records:
        try:
            # Dispatch background API call
            requests.get(f"{API_BASE_URL}?uid={uid}&region={region}", timeout=25)
            time.sleep(2) # Prevent overwhelming the target server
        except Exception:
            pass

def scheduler_thread():
    """Checks the time and executes scheduled tasks"""
    already_run_today = False
    while True:
        now = datetime.datetime.now()
        # Check if current time is exactly 7:00 AM
        if now.hour == 7 and now.minute == 0:
            if not already_run_today:
                run_auto_likes()
                already_run_today = True
        else:
            already_run_today = False
        
        time.sleep(30) # Check every 30 seconds

# Start Scheduler Thread
threading.Thread(target=scheduler_thread, daemon=True).start()

# ==================== BOT RUNNING ====================
if __name__ == "__main__":
    print("FREXY AUTO LIKE Bot is running...")
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            time.sleep(5)