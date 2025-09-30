import os
import json
import aiohttp
from telethon import TelegramClient, events
from telethon.tl.types import InputDocument

# ===== CONFIG =====
API_ID = int(os.getenv("API_ID"))  # isi dari my.telegram.org
API_HASH = os.getenv("API_HASH")   # isi dari my.telegram.org
BOT_TOKEN = os.getenv("BOT_TOKEN") # token bot
REMOVE_BG_API = os.getenv("REMOVE_BG_API")  # API key remove.bg

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ===== HELP TEXT =====
HELP_TEXT = """
🤖 Selamat datang di Rensci Emoji Bot!

Command yang tersedia:
/help - Menampilkan daftar command
/json2tgs - Convert file .json ke .tgs otomatis
/tgs2pack - Buat pack emoji dari file .tgs
/removebg - Hapus background gambar (png/jpg)

File yang dikirim akan otomatis diproses dan disimpan.
"""

# ===== UTILITY =====
async def convert_json_to_tgs(json_file, output_file):
    """
    Contoh simple convert json ke tgs.
    Bisa diganti dengan library lottie atau compress json.
    """
    import lottie
    anim = lottie.parsers.tgs.parse_tgs(json_file)
    lottie.parsers.tgs.save_tgs(anim, output_file)

async def remove_bg_image(file_path, output_path):
    """
    Remove background menggunakan remove.bg API
    """
    url = "https://api.remove.bg/v1.0/removebg"
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = {"size":"auto"}
            files = {"image_file": f}
            headers = {"X-Api-Key": REMOVE_BG_API}
            async with session.post(url, data=data, headers=headers, files=files) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as out:
                        out.write(await resp.read())
                else:
                    text = await resp.text()
                    raise Exception(f"Remove.bg error: {text}")

# ===== EVENTS =====
@client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.reply("👋 Halo! Bot siap digunakan.\n" + HELP_TEXT)

@client.on(events.NewMessage(pattern="/help"))
async def help_handler(event):
    await event.reply(HELP_TEXT)

@client.on(events.NewMessage)
async def message_handler(event):
    # Simpan file yang dikirim user
    if event.file:
        file_path = os.path.join(DOWNLOAD_FOLDER, event.file.name or "file")
        await event.download_media(file_path)
        await event.reply(f"📥 File diterima: {file_path}")

        # Otomatis convert json -> tgs jika json
        if file_path.endswith(".json"):
            tgs_file = file_path.replace(".json", ".tgs")
            try:
                await convert_json_to_tgs(file_path, tgs_file)
                await event.reply(f"✅ File berhasil dikonversi ke: {tgs_file}")
            except Exception as e:
                await event.reply(f"❌ Gagal convert json -> tgs: {e}")

        # Remove background otomatis jika gambar
        elif file_path.lower().endswith((".png", ".jpg", ".jpeg")):
            out_file = file_path.replace(".", "_nobg.")
            try:
                await remove_bg_image(file_path, out_file)
                await event.reply(f"✅ Background dihapus: {out_file}")
            except Exception as e:
                await event.reply(f"❌ Gagal remove.bg: {e}")

# ===== RUN BOT =====
print("Bot berjalan...")
client.run_until_disconnected()
