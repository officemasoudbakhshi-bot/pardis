import os
import asyncio
from telegram import Bot

async def main():
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    WEBHOOK_URL = "https://your-app-name.onrender.com/webhook"
    
    bot = Bot(token=BOT_TOKEN)
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook set successfully!")

if __name__ == '__main__':
    asyncio.run(main())