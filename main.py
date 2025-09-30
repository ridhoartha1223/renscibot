import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telethon import TelegramClient, events

# Ambil dari environment variable
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")

# Load service account dari file
SERVICE_ACCOUNT_FILE = "service_account.json"
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

# Build Google Drive service
drive_service = build('drive', 'v3', credentials=credentials)

# Setup TelegramClient
api_id = 123456  # Bisa dummy, BOT_TOKEN sudah cukup
api_hash = "dummyhash"
client = TelegramClient('bot', api_id, api_hash).start(bot_token=BOT_TOKEN)

# Event listener sederhana
@client.on(events.NewMessage)
async def handler(event):
    msg = event.message.message.lower()
    if msg == "/start":
        await event.respond("Bot aktif! 🚀")
    elif msg == "/listfiles":
        results = drive_service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents",
            pageSize=10,
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])
        if not files:
            await event.respond("Folder kosong 😔")
        else:
            file_list = "\n".join([f"{f['name']} ({f['id']})" for f in files])
            await event.respond(f"File di folder:\n{file_list}")

print("Bot siap dijalankan!")
client.run_until_disconnected()
