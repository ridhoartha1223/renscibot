import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telethon import TelegramClient, events

# ==========================
# Ambil environment variables
# ==========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON").replace("\\n", "\n")

# ==========================
# Load Service Account
# ==========================
service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
credentials = service_account.Credentials.from_service_account_info(service_account_info)
drive_service = build('drive', 'v3', credentials=credentials)

# ==========================
# Telegram Client
# ==========================
api_id = int(os.environ.get("API_ID", 123456))  # isi default api_id, bisa diganti jika ada
api_hash = os.environ.get("API_HASH", "your_api_hash")  # isi default api_hash, bisa diganti
client = TelegramClient('bot', api_id, api_hash).start(bot_token=BOT_TOKEN)

# ==========================
# Event Example
# ==========================
@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply(f"Bot aktif! Folder Drive: {DRIVE_FOLDER_ID}")

# ==========================
# Jalankan Bot
# ==========================
print("Bot berjalan...")
client.run_until_disconnected()
