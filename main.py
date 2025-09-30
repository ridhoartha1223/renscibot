import os
from pyrogram import Client, filters
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import json

# ===== Config =====
BOT_TOKEN = "8319183574:AAHIi3SX218DNqS-owUcQ9Xyvc_D4Mk14Rw"
DRIVE_FOLDER_ID = "1Z5q0Td8zWD4cFPO0upmWhBHAXW3eSacm"
SERVICE_ACCOUNT_JSON = '{"installed":{"client_id":"1011650448521-sg3j5i3ec09htmdpdeg6lfphune6bgg9.apps.googleusercontent.com","project_id":"rensci-bot","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"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","redirect_uris":["http://localhost"]}}'

# ===== Google Drive Setup =====
SCOPES = ['https://www.googleapis.com/auth/drive.file']
with open("service_account.json", "w") as f:
    f.write(SERVICE_ACCOUNT_JSON)

credentials = service_account.Credentials.from_service_account_file(
    "service_account.json", scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

def upload_file_to_drive(local_path, folder_id):
    filename = os.path.basename(local_path)
    file_metadata = {'name': filename, 'parents': [folder_id]}
    media = MediaFileUpload(local_path, mimetype='application/octet-stream')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

# ===== Pyrogram Bot =====
user_states = {}
app = Client("bot_session", bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
def start(client, message):
    message.reply("👋 Hai! Kirim file .tgs atau .json.\nBot akan otomatis upload ke Google Drive dengan nama asli file.")

@app.on_message(filters.document & filters.private)
def receive_file(client, message):
    user_id = str(message.from_user.id)
    doc = message.document
    if not doc.file_name.lower().endswith((".tgs", ".json")):
        message.reply("❌ Tolong kirim .tgs atau .json saja.")
        return

    temp_folder = f"{user_id}_temp"
    os.makedirs(temp_folder, exist_ok=True)
    file_path = os.path.join(temp_folder, doc.file_name)
    message.download(file_path)
    user_states.setdefault(user_id, {})["temp_files"] = user_states.get(user_id, {}).get("temp_files", []) + [file_path]
    message.reply(f"✅ File '{doc.file_name}' diterima. Sekarang kirim nama pack untuk prefix (misal: MyPack).")

@app.on_message(filters.text & filters.private)
def set_pack_name(client, message):
    user_id = str(message.from_user.id)
    if user_id not in user_states or "temp_files" not in user_states[user_id]:
        message.reply("⚠️ Kirim file dulu ya.")
        return

    pack_name = message.text.strip()
    temp_files = user_states[user_id]["temp_files"]
    for f in temp_files:
        original_name = os.path.basename(f)
        new_name = f"{pack_name}_{original_name}"
        upload_file_to_drive(f, DRIVE_FOLDER_ID)
        os.remove(f)  # hapus file lokal
    user_states[user_id]["temp_files"] = []
    message.reply(f"✅ Semua file diupload ke Google Drive dengan prefix pack '{pack_name}'.")

print("Bot starting... (Railway / Local, bot-only, Google Drive upload)")
app.run()
