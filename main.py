import os
import json
from telethon import TelegramClient, events
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ===== Ambil ENV vars =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON")

if not all([BOT_TOKEN, DRIVE_FOLDER_ID, SERVICE_ACCOUNT_JSON]):
    raise ValueError("Pastikan BOT_TOKEN, DRIVE_FOLDER_ID, dan SERVICE_ACCOUNT_JSON sudah di-set di ENV vars.")

# ===== Setup Google Drive API =====
service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
credentials = service_account.Credentials.from_service_account_info(service_account_info)
drive_service = build('drive', 'v3', credentials=credentials)

# ===== Setup Telegram Bot =====
bot = TelegramClient('bot_session', api_id=123456, api_hash='dummyhash').start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/list'))
async def list_files(event):
    """List file names di folder Google Drive"""
    results = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
        pageSize=10,
        fields="files(id, name)"
    ).execute()
    items = results.get('files', [])
    if not items:
        await event.reply("Folder kosong.")
    else:
        msg = "\n".join([f"{item['name']} (ID: {item['id']})" for item in items])
        await event.reply(msg)

@bot.on(events.NewMessage(pattern='/upload'))
async def upload_file(event):
    """Upload file dari reply ke Google Drive"""
    if not event.message.reply_to_msg_id:
        await event.reply("Reply ke file yang mau di-upload.")
        return
    reply = await event.get_reply_message()
    if not reply.document:
        await event.reply("Reply ke file yang valid.")
        return

    path = await reply.download_media()
    file_metadata = {'name': os.path.basename(path), 'parents': [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(path, resumable=True)
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    await event.reply(f"File {os.path.basename(path)} berhasil di-upload!")

print("Bot sudah siap...")
bot.run_until_disconnected()
