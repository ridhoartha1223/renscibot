import os
import asyncio
from telethon import TelegramClient, events

# Ambil data dari environment variables di Railway
API_ID = int(os.getenv("API_ID"))            # contoh: 28235685
API_HASH = os.getenv("API_HASH")             # isi API_HASH dari my.telegram.org
BOT_TOKEN = os.getenv("BOT_TOKEN")           # token bot Telegram

# Buat client bot
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Event handler untuk /start
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("Halo! Bot siap menerima file .tgs atau .json untuk emoji.\nKetik /help untuk melihat command yang tersedia.")

# Event handler untuk /help
@client.on(events.NewMessage(pattern='/help'))
async def help(event):
    help_text = (
        "/start - Mulai bot\n"
        "/help - Lihat command\n"
        "/json2tgs - Konversi file .json menjadi .tgs\n"
        "/tgslink - Dapatkan link emoji pack dari file .tgs\n"
    )
    await event.respond(help_text)

# Event handler untuk menerima file
@client.on(events.NewMessage)
async def file_handler(event):
    if event.file:
        file_path = await event.download_media(file="downloads/")
        await event.respond(f"File diterima: {file_path}\nKamu bisa lanjut membuat emoji pack.")

# Jalankan client
print("Bot berjalan...")
client.run_until_disconnected()
