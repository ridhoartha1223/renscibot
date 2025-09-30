import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ================= CONFIG ===================
BOT_TOKEN = "8319183574:AAHIi3SX218DNqS-owUcQ9Xyvc_D4Mk14Rw"
DRIVE_FOLDER_ID = "1Z5q0Td8zWD4cFPO0upmWhBHAXW3eSacm"

SERVICE_ACCOUNT_JSON = {
  "type": "service_account",
  "project_id": "rensci-bot",
  "private_key_id": "2c25071c5e8cb9f4ae43323ce7503012dd0af815",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANB ... \n-----END PRIVATE KEY-----\n",
  "client_email": "rensci@rensci-bot.iam.gserviceaccount.com",
  "client_id": "104566396256112841524",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/rensci%40rensci-bot.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
# ============================================

# Setup Google Drive
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_JSON)
service = build('drive', 'v3', credentials=credentials)

# Bot Handlers
async def start(update: Update, context):
    await update.message.reply_text("Halo! Kirimkan file .tgs, nanti akan otomatis di-upload ke Drive.")

async def handle_file(update: Update, context):
    file = await update.message.document.get_file()
    path = f"{update.message.document.file_name}"
    await file.download_to_drive(path)

    # Upload ke Google Drive
    media = MediaFileUpload(path, mimetype='application/octet-stream')
    file_drive = service.files().create(
        body={'name': path, 'parents':[DRIVE_FOLDER_ID]},
        media_body=media,
        fields='id'
    ).execute()
    
    await update.message.reply_text(f"File berhasil di-upload! File ID: {file_drive.get('id')}")

# Setup Telegram Bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

print("Bot sudah berjalan...")
app.run_polling()
