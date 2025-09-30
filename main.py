import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Ambil ENV VAR
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")

# Load service account JSON
credentials = service_account.Credentials.from_service_account_info(json.loads(SERVICE_ACCOUNT_JSON))
drive_service = build('drive', 'v3', credentials=credentials)

# Telegram bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
bot = Bot(BOT_TOKEN)

# Command /start
async def start(update: Update, context):
    await update.message.reply_text("Halo! Kirim .tgs file kamu, nanti aku simpan ke Google Drive dan ubah jadi emoji pack!")

# Handler file .tgs
async def handle_tgs(update: Update, context):
    file = await update.message.effective_attachment.get_file()
    file_path = file.file_path
    await update.message.reply_text(f"File diterima: {file_path}\nProses simpan ke Drive...")

    # Upload ke Drive
    file_name = update.message.effective_attachment.file_name
    media = drive_service.files().create(
        body={"name": file_name, "parents":[DRIVE_FOLDER_ID]},
        media_body=file_path
    ).execute()
    await update.message.reply_text(f"Berhasil diupload ke Drive! ID: {media['id']}")

# Registrasi handler
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.FileExtension("tgs"), handle_tgs))

if name == "__main__":
    print("Bot siap jalan...")
    app.run_polling()
