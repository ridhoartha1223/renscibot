import os
import json
import subprocess
from telethon import TelegramClient, events
from telethon.tl.types import InputDocument

# ================= CONFIG =================
BOT_TOKEN = "8319183574:AAHIi3SX218DNqS-owUcQ9Xyvc_D4Mk14Rw"
API_ID = 28235685  # isi dengan api_id Telegram
API_HASH = "03c741f65092cb2ccdd9341b9b055f13"

DOWNLOAD_DIR = "downloads"
PACK_NAME = "rensci_emoji_r3nsian"
PACK_TITLE = "Rensci Emoji @r3nsian"

# ================= CLIENT =================
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

COMMANDS = {
    "/new": "Kirim file .tgs untuk membuat emoji pack otomatis",
    "/json2tgs": "Kirim file .json untuk dikonversi menjadi .tgs",
    "/help": "Menampilkan semua command aktif"
}

# ================= HELP =================
@client.on(events.NewMessage(pattern="/start|/help"))
async def start(event):
    text = "Selamat datang di Rensci Emoji Bot!\n\nCommand aktif:\n"
    for cmd, desc in COMMANDS.items():
        text += f"{cmd} → {desc}\n"
    await event.reply(text)

# ================= UTILS =================
def json_to_tgs(json_path, tgs_path):
    """
    Konversi JSON Lottie menjadi .tgs menggunakan lottie_convert.py
    Pastikan sudah ada lottie_convert.py di project atau install lottie2tgs
    """
    try:
        subprocess.run(["lottie_convert.py", json_path, tgs_path], check=True)
        return True
    except Exception as e:
        print("Error convert:", e)
        return False

# ================= HANDLER .TGS =================
@client.on(events.NewMessage(pattern="/new"))
async def new_tgs_cmd(event):
    await event.reply("Silakan kirim file .tgs untuk membuat emoji pack otomatis...")

@client.on(events.NewMessage)
async def tgs_handler(event):
    if event.file and event.file.name.endswith(".tgs"):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        path = f"{DOWNLOAD_DIR}/{event.file.name}"
        await event.download_media(path)
        await event.reply(f"File diterima: {path}\nEmoji pack siap dibuat!")
        # TODO: implement auto pack + replace + link generation

# ================= HANDLER JSON =================
@client.on(events.NewMessage(pattern="/json2tgs"))
async def json2tgs_cmd(event):
    await event.reply("Silakan kirim file .json untuk dikonversi menjadi .tgs...")

@client.on(events.NewMessage)
async def json_handler(event):
    if event.file and event.file.name.endswith(".json"):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        json_path = f"{DOWNLOAD_DIR}/{event.file.name}"
        tgs_path = f"{DOWNLOAD_DIR}/{os.path.splitext(event.file.name)[0]}.tgs"
        await event.download_media(json_path)
        await event.reply(f"File JSON diterima: {json_path}\nMengonversi ke .tgs ...")
        if json_to_tgs(json_path, tgs_path):
            await event.reply(f"Selesai! File TGS siap: {tgs_path}")
        else:
            await event.reply("Gagal mengonversi JSON menjadi TGS.")

# ================= RUN =================
print("Bot berjalan...")
client.run_until_disconnected()
