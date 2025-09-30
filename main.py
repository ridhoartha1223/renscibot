import os
from pyrogram import Client, filters
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import json

# ===== Config =====
BOT_TOKEN = "8319183574:AAHIi3SX218DNqS-owUcQ9Xyvc_D4Mk14Rw"
DRIVE_FOLDER_ID = "1Z5q0Td8zWD4cFPO0upmWhBHAXW3eSacm"
SERVICE_ACCOUNT_JSON = '{"{"type":"service_account","project_id":"rensci-bot","private_key_id":"2c25071c5e8cb9f4ae43323ce7503012dd0af815","private_key":"-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDdk5lZSC7BeCmS\nAlHEtN+MqVF3RtNIfSNxbym0e6ErhILb4QXA+AQXtuDBT/hgIaMirNhhXeyFkXBr\nW9X3SkjgaWGGEdowI8oC6n8kDMG0BjZ5jVMSC2eNxq+HZ2LPdPTxggYinZ67whDa\nAMZhdjjPU5bpSTyWIWug3clG3IOVqyqIjUSxReUWwW1+HFKHD2JkCAQnwzzDD6zj\n8+vzwq1IjnWtAI6zoggKFrAQTyaFTqGtPuFxPFP9FzPofaYkDwGwPZkPhRZ7c9/e\nhvQG+/3xjxaQUvRCUPkwDKb4D0wRl0hoX543VI08D3YfTBXjSVi8niwVOoD5dhMQ\nUl5NFmhPAgMBAAECggEATEdvP9K/MeBtozPENY009mYlwwOxYd+er4Le3yC+c85L\nBGobgnp/YjCVgEdJEMMTt7C8Twy4C6Vth7AWYWsD2qm8ppyHuhHgDg/vVBhGKPUI\nlODnq6sca6zuKZWYaSXw2yFxfkI37phZF8uzf8LkvM8ggVAymNaJiFhB3fC1JfUi\nMdePzGonhJBGOUM+IiRVcwdj1j43jP5y7/EA7jWHXyNUp30kMMfQXmQCYLfl3pvT\n7ptDbNQtwfxAQuuzzAsazMZQ7Em1zL3Y1iL3t5l3G/5vi8ORoIRpmoj1jMK6aZui\nqKYdQLvxSTu/nXNUYO68Hx4K63qY4pcQzL31meXhZQKBgQD/B+7tlupvuP0FewJN\nvErYXd4O5Cb0unea6gnDGavHrqhShZ3W16VITJKrGW2QORA38u5VKN8jJD2MzSY2\nZLMw76u9jD0jxsl4+dvXVt8/ktihUdf/aoHICkrjzJGNefo6PpMfnGqFXvXHCC7m\n0C2SocrF06M7fuHx9yIGlJN9vQKBgQDeax/1WdH7WiCUFpQoDa4ST8WtSM6CmmlJ\nzbVXg1gJqMcoR2oHdqNRWdpQbGb0ubtuYXYq9d8zd2AwQ7grvlmTg95yJUWHvBLK\nkDpfTdSJQCTfdXclKBNuF2/CI/iGntopCOyUIbSx7U2Y3Ba5Tbl+RSW4Q8N8UMtz\noZo0PbSg+wKBgQCkUoVFeu71K5mEFX0nf0IuZVT1/VWIbDkyjMfbeMfxMn1sJoHL\n80ig7A24xvqMaegkVJfyMRKNPwWVmn2boIjA6DydNiYSzjv0gfF/r47LFKAWWXi2\nLvcOYGtemenS4Zw0OStsu8j6xHPSWVh3Cf3DNBJGIxZS+G83C8hVuxfJdQKBgD9d\nh6JPr5oLaEKoWBc9Jn2DCo8+sc7VjO+A0owXGErQMcUQ620q6IZxsde9ums4SuS8\nkXzVxXwVI2s8r8iOl1iGdiZQ5gkwlK3u/yJNuyJLCvY6sfH9A+QWezl1JAW+Verg\n5v2gyKj0MWo+MZ8jPJhzvLZNX/EX146e2J7PgZlnAoGBAJQdWWoCFlJmzMFGkkfk\nXyBhUtA43sncIPgWdCjplRlfz/3AfEfzA8h34u1Hg9yty4ilQI0k03Md8z+CmBeb\nbkgf0/byXl9KYTOiDknQO/+TI3yajr5EaDm8Yqg9V/rIFmvQls2rd6/Fi3gv7MME\n6OMREOrx+Kj8hqtFeLjot9mf\n-----END PRIVATE KEY-----\n","client_email":"rensci@rensci-bot.iam.gserviceaccount.com","client_id":"104566396256112841524","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/rensci%40rensci-bot.iam.gserviceaccount.com","universe_domain":"googleapis.com"}"]}}'

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

