import asyncio
import json
from telethon import TelegramClient, events
from telethon.tl.types import InputStickerSetShortName
from telethon.tl.functions.messages import ImportStickerSetRequest, GetStickerSetRequest
from telethon.tl.functions.stickers import AddStickerToSetRequest
from telethon.tl.functions.messages import SendMediaRequest
from telethon.tl.types import InputDocument, InputStickerSetItem

# -------------------- CONFIG --------------------
BOT_TOKEN = "8319183574:AAHIi3SX218DNqS-owUcQ9Xyvc_D4Mk14Rw"
API_ID = 28235685  # Masukkan api_id dari https://my.telegram.org
API_HASH = "03c741f65092cb2ccdd9341b9b055f13"  # Masukkan api_hash

# Path ke file service account JSON
SERVICE_ACCOUNT_FILE = "service_account.json"

# Folder ID Google Drive (kalau mau pakai integrasi Drive)
DRIVE_FOLDER_ID = "1Z5q0Td8zWD4cFPO0upmWhBHAXW3eSacm"
# ------------------------------------------------

# Load Service Account JSON (opsional, kalau pakai Google Drive)
with open(SERVICE_ACCOUNT_FILE, "r") as f:
    service_account_info = json.load(f)

client = TelegramClient('sticker_bot', API_ID, API_HASH)

# -------------------- EVENT HANDLERS --------------------

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply("Halo! Bot Stiker aktif. Gunakan /help untuk melihat command.")

@client.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    text = (
        "Daftar command:\n"
        "/start - Mulai bot\n"
        "/help - Bantuan\n"
        "/addsticker - Tambah stiker ke pack\n"
        "/liststickers - List stiker di pack\n"
        "/createstickerpack - Buat stiker pack baru\n"
    )
    await event.reply(text)

# Event buat nambah stiker ke pack
@client.on(events.NewMessage(pattern='/addsticker'))
async def add_sticker(event):
    # Cek apakah ada reply ke gambar
    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg.media:
            await event.reply("Stiker berhasil ditambahkan (dummy).")
            # Di sini nanti logic konversi gambar -> .WEBP -> add ke sticker pack
        else:
            await event.reply("Reply ke gambar/gif yang mau dijadikan stiker!")
    else:
        await event.reply("Gunakan command ini dengan reply ke gambar.")

# Event buat list sticker
@client.on(events.NewMessage(pattern='/liststickers'))
async def list_stickers(event):
    await event.reply("Daftar stiker pack (dummy): 🟢 Stiker 1, 🔵 Stiker 2")

# Event buat create sticker pack baru
@client.on(events.NewMessage(pattern='/createstickerpack'))
async def create_pack(event):
    await event.reply("Sticker pack baru berhasil dibuat! (dummy)")

# -------------------- RUN BOT --------------------
async def main():
    print("Bot Stiker Telegram siap!")
    await client.start(bot_token=BOT_TOKEN)
    await client.run_until_disconnected()  # <- terus listen semua command

asyncio.run(main())
