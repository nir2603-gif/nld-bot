# NLD Daily Summary Bot

Telegram bot that reads messages from business groups, translates Khmer to English using Gemini AI, and sends a daily summary every morning at 8:00 AM (Phnom Penh time).

## Groups monitored:
- NLD CVD SALES GROUP
- Sent to Goldsmith
- NLD EXP
- REFUNDS NLD

## Environment Variables (set in Railway):
| Variable | Description |
|----------|-------------|
| TELEGRAM_TOKEN | Your bot token from BotFather |
| GEMINI_API_KEY | Your Gemini API key from aistudio.google.com |
| SUMMARY_CHAT_ID | Chat ID of NLD Daily Summary group (-5395440702) |
| SALES_CHAT_ID | Chat ID of NLD CVD SALES GROUP (-1001991985756) |
| GOLDSMITH_CHAT_ID | Chat ID of Sent to Goldsmith (-1003124128984) |
| EXP_CHAT_ID | Chat ID of NLD EXP (-1002219185766) |
| REFUNDS_CHAT_ID | Chat ID of REFUNDS NLD (-1002228397271) |

## Deploy to Railway:
1. Push this code to GitHub
2. Connect GitHub repo to Railway
3. Add all environment variables
4. Deploy!
