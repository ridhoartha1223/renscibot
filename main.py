import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import InputDocument

# --- Konfigurasi ---
API_ID = int(os.environ.get("API_ID", "28235685"))
API_HASH = os.environ.get("API_HASH", "03c741f65092cb2ccdd9341b9b055f13")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")

# --- Inisialisasi client ---
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- Command menu ---
COMMANDS = {
    "/new": "Buat pack emoji baru (kirim file .tgs)",
    "/json2tgs": "Convert file .json ke .tgs",
    "/removebg": "Hapus background gambar",
    "/link": "Dapatkan link emoji pack",
    "/help": "Lihat daftar perintah"
}

# --- Event /start ---
@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    menu_text = "\n".join([f"{cmd} → {desc}" for cmd, desc in COMMANDS.items()])
    await event.respond(
        "Halo! Aku Rensci Emoji Bot 🤖\n"
        "Aku bisa bantu kamu membuat emoji Telegram premium dengan cepat.\n\n"
        "Berikut daftar perintah yang tersedia:\n\n"
        f"{menu_text}"
    )

# --- Event /help ---
@client.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    menu_text = "\n".join([f"{cmd} → {desc}" for cmd, desc in COMMANDS.items()])
    await event.respond(f"Daftar perintah:\n\n{menu_text}")

# --- Event /new ---
@client.on(events.NewMessage(pattern='/new'))
async def new_handler(event):
    await event.respond("Kirim file .tgs kamu sekarang untuk membuat emoji pack!")

# --- Event /json2tgs ---
@client.on(events.NewMessage(pattern='/json2tgs'))
async def json2tgs_handler(event):
    await event.respond("Kirim file .json kamu, nanti aku akan convert ke .tgs!")

# --- Event /removebg ---
@client.on(events.NewMessage(pattern='/removebg'))
async def removebg_handler(event):
    await event.respond("Kirim file gambar kamu, aku akan hapus background-nya!")

# --- Event /link ---
@client.on(events.NewMessage(pattern='/link'))
async def link_handler(event):
    await event.respond("Aku akan buatkan link emoji pack kamu setelah selesai.")

# --- Menjalankan client ---
print("Bot sedang berjalan...")
client.run_until_disconnected()
