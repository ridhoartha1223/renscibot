import os
import json
import aiohttp
from telethon import TelegramClient, events
from telethon.tl.types import InputDocument

# ===== CONFIG =====
API_ID = int(os.getenv("API_ID"))       # dari my.telegram.org
API_HASH = os.getenv("API_HASH")        # dari my.telegram.org
BOT_TOKEN = os.getenv("BOT_TOKEN")      # token bot
REMOVE_BG_API = os.getenv("REMOVE_BG_API")  # key remove.bg

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ===== HELP TEXT =====
HELP_TEXT = """
🤖 Selamat datang di Rensci Emoji Bot!

Command tersedia:
/help - Tampilkan daftar command
/json2tgs - Convert file .json ke .tgs
/tgs2pack - Buat pack emoji dari file .tgs
/removebg - Hapus background gambar (png/jpg)
"""

# ===== UTILITY FUNCTIONS =====
async def convert_json_to_tgs(json_file, output_file):
    import lottie.parsers.tgs
    try:
        anim = lottie.parsers.tgs.parse_tgs(json_file)
        lottie.parsers.tgs.save_tgs(anim, output_file)
    except Exception as e:
        raise Exception(f"Gagal convert json->tgs: {e}")

async def remove_bg(file_path, output_path):
    url = "https://api.remove.bg/v1.0/removebg"
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = {"size": "auto"}
            files = {"image_file": f}
            headers = {"X-Api-Key": REMOVE_BG_API}
            async with session.post(url, data=data, headers=headers, files=files) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as out:
                        out.write(await resp.read())
                else:
                    raise Exception(await resp.text())

# ===== EVENTS =====
@client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.reply("👋 Halo! Bot siap digunakan.\n" + HELP_TEXT)

@client.on(events.NewMessage(pattern="/help"))
async def help_handler(event):
    await event.reply(HELP_TEXT)

@client.on(events.NewMessage)
async def message_handler(event):
    if not event.file:
        return

    file_name = event.file.name or "file"
    file_path = os.path.join(DOWNLOAD_FOLDER, file_name)
    await event.download_media(file_path)
    await event.reply(f"📥 File diterima: {file_path}")

    # Convert JSON -> TGS
    if file_path.endswith(".json"):
        tgs_file = file_path.replace(".json", ".tgs")
        try:
            await convert_json_to_tgs(file_path, tgs_file)
            await event.reply(f"✅ File berhasil dikonversi ke: {tgs_file}")
        except Exception as e:
            await event.reply(str(e))

    # Remove background otomatis
    elif file_path.lower().endswith((".png", ".jpg", ".jpeg")):
        out_file = file_path.replace(".", "_nobg.")
        try:
            await remove_bg(file_path, out_file)
            await event.reply(f"✅ Background dihapus: {out_file}")
        except Exception as e:
            await event.reply(f"❌ Remove.bg gagal: {e}")

    # TGS -> buat pack emoji
    elif file_path.endswith(".tgs"):
        # NOTE: Untuk membuat pack emoji via bot, Telegram memerlukan user account premium.
        # Kita hanya bisa mengirim file .tgs dan link pack nanti harus dibuat manual atau via userbot
        await event.reply("✅ File TGS siap untuk dijadikan emoji pack.\nSilahkan gunakan Telegram UserBot untuk membuat pack otomatis.")

# ===== RUN BOT =====
print("Bot berjalan...")
client.run_until_disconnected()
