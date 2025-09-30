import os
import tempfile
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from lottie import parsers, exporters
from removebg import RemoveBg
import ntplib

# --- Environment Variables Railway ---
API_HASH = os.getenv("API_HASH")
API_ID = int(os.getenv("API_ID"))
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMOVE_BG_API = os.getenv("REMOVE_BG_API")

# --- Initialize Bot ---
bot = Client("emoji_bot",
             api_id=API_ID,
             api_hash=API_HASH,
             bot_token=BOT_TOKEN)

# --- User state for interactive import ---
user_state = {}

# --- Helper Functions ---
def json_to_tgs(json_file_path, optimize=False):
    animation = parsers.tgs.parse_tgs(json_file_path)
    # Optimasi sederhana, compatible dengan lottie 0.7.x
    tgs_path = json_file_path.replace(".json", "_converted.tgs")
    exporters.tgs.export_tgs(animation, tgs_path)
    return tgs_path

def check_size_limit(file_path):
    return os.path.getsize(file_path) > 64 * 1024

# --- Time sync to prevent BadMsgNotification ---
def sync_time():
    try:
        c = ntplib.NTPClient()
        response = c.request('pool.ntp.org')
        offset = response.offset
        print(f"NTP offset: {offset} seconds")
    except Exception as e:
        print("Gagal sinkronisasi waktu:", e)

# --- Start command ---
@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text(
        "👋 Selamat datang di Emoji Bot!\n\n"
        "Fitur:\n"
        "/json2tgs - Convert .json → .tgs\n"
        "/json2tgs_optimize - Convert .json → .tgs (optimized)\n"
        "/import_tgs - Import .tgs ke New Premium Emoji Pack\n"
        "/removebg - Remove background gambar"
    )

# --- Upload JSON untuk auto convert ---
@bot.on_message(filters.document & filters.regex(r".*\.json$"))
async def handle_json(client, message: Message):
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, message.document.file_name)
        await message.download(file_path=json_path)
        tgs_path = json_to_tgs(json_path)
        size_warning = check_size_limit(tgs_path)
        caption = "✅ Konversi selesai."
        if size_warning:
            caption += "\n⚠️ File .tgs lebih dari 64KB, mungkin tidak bisa dijadikan emoji premium."

        # Kirim hasil TGS sent =
