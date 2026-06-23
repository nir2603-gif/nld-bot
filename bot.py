import os
import asyncio
import logging
from datetime import datetime, timedelta
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUMMARY_CHAT_ID = os.environ.get("SUMMARY_CHAT_ID", "")

SOURCE_GROUPS = {
    "NLD CVD SALES GROUP": os.environ.get("SALES_CHAT_ID", ""),
    "Sent to Goldsmith": os.environ.get("GOLDSMITH_CHAT_ID", ""),
    "NLD EXP": os.environ.get("EXP_CHAT_ID", ""),
    "REFUNDS NLD": os.environ.get("REFUNDS_CHAT_ID", ""),
}

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set!")

TIMEZONE = pytz.timezone("Asia/Phnom_Penh")
SUMMARY_HOUR = 8
SUMMARY_MINUTE = 0

# --- TELEGRAM ---
async def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30, "limit": 100}
    if offset:
        params["offset"] = offset
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.get(url, params=params)
        return r.json()

async def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    max_length = 4000
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    async with httpx.AsyncClient(timeout=30) as client:
        for chunk in chunks:
            await client.post(url, json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown"
            })

# --- MESSAGE STORAGE ---
messages_store = {}

# --- GEMINI ---
async def summarize_with_gemini(group_name, messages):
    if not messages:
        return f"No messages yesterday."

    messages_text = "\n".join([
        f"[{m['from']}]: {m['text']}" for m in messages
    ])

    prompt = f"""You are a business assistant. Below are messages from the Telegram group "{group_name}".
Many messages may be in Khmer (Cambodian language). 

Please:
1. Translate all Khmer text to English
2. Summarize what happened in this group yesterday
3. List any important actions, payments, orders, or tasks mentioned
4. Highlight anything that needs follow-up

Messages:
{messages_text}

Respond in clear English with bullet points. Be concise and business-focused."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}]
        })
        result = r.json()
        logger.info(f"Gemini response for {group_name}: {result}")
        if "candidates" not in result:
            error_msg = result.get("error", {}).get("message", str(result))
            return f"Gemini API error: {error_msg}"
        return result["candidates"][0]["content"]["parts"][0]["text"]

# --- DAILY SUMMARY ---
async def send_daily_summary():
    logger.info("Sending daily summary...")
    now = datetime.now(TIMEZONE)
    yesterday = now - timedelta(days=1)
    yesterday_date = yesterday.date()

    summary_parts = []
    summary_parts.append(f"📊 *DAILY BUSINESS SUMMARY*")
    summary_parts.append(f"📅 {yesterday_date.strftime('%A, %B %d, %Y')}\n")

    for group_name in SOURCE_GROUPS.keys():
        all_msgs = messages_store.get(group_name, [])
        yesterday_msgs = [
            m for m in all_msgs
            if m["date"].date() == yesterday_date
        ]

        try:
            summary = await summarize_with_gemini(group_name, yesterday_msgs)
        except Exception as e:
            summary = f"Error generating summary: {e}"

        summary_parts.append(f"━━━━━━━━━━━━━━━━━━━━")
        summary_parts.append(f"📁 *{group_name}*")
        summary_parts.append(summary)

    summary_parts.append(f"\n━━━━━━━━━━━━━━━━━━━━")
    summary_parts.append(f"✅ End of daily summary")

    full_summary = "\n".join(summary_parts)
    await send_message(SUMMARY_CHAT_ID, full_summary)
    logger.info("Daily summary sent!")

    for group_name in SOURCE_GROUPS.keys():
        if group_name in messages_store:
            messages_store[group_name] = [
                m for m in messages_store[group_name]
                if m["date"].date() != yesterday_date
            ]

# --- POLL MESSAGES ---
async def poll_messages():
    offset = None
    while True:
        try:
            data = await get_updates(offset)
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message") or update.get("channel_post")
                    if msg and msg.get("text"):
                        chat_id = str(msg["chat"]["id"])
                        text = msg.get("text", "")

                        # Handle /summary command
                        if text.strip() == "/summary" and chat_id == SUMMARY_CHAT_ID:
                            await send_message(chat_id, "⏳ Generating summary now, please wait...")
                            await send_daily_summary()
                            continue

                        # Store messages from source groups
                        for group_name, gid in SOURCE_GROUPS.items():
                            if chat_id == gid:
                                if group_name not in messages_store:
                                    messages_store[group_name] = []
                                sender = msg.get("from", {}).get("first_name", "Unknown")
                                messages_store[group_name].append({
                                    "date": datetime.fromtimestamp(msg["date"], tz=TIMEZONE),
                                    "from": sender,
                                    "text": text
                                })
                                break
        except Exception as e:
            logger.error(f"Polling error: {e}")
        await asyncio.sleep(2)

# --- MAIN ---
async def main():
    logger.info("NLD Bot starting...")

    await send_message(SUMMARY_CHAT_ID, "✅ *NLD Bot is online!*\nI will send daily summaries every morning at 8:00 AM.\nSend /summary anytime to get yesterday's report.")

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        send_daily_summary,
        "cron",
        hour=SUMMARY_HOUR,
        minute=SUMMARY_MINUTE
    )
    scheduler.start()

    await poll_messages()

if __name__ == "__main__":
    asyncio.run(main())
