import os
import json
import aiohttp
from telethon import TelegramClient, events
from telethon.tl.types import InputDocument
from telethon.tl.functions.stickers import CreateStickerSetRequest, AddStickerToSetRequest
from telethon.errors import StickerSetInvalidError

# ===== CONFIG =====
BOT_TOKEN = os.getenv("8319183574:AAHIi3SX218DNqS-owUcQ9Xyvc_D4Mk14Rw")
API_ID = int(os.getenv("28235685"))
API_HASH = os.getenv("03c741f65092cb2ccdd9341b9b055f13")
REMOVE_BG_KEY = os.getenv("ikoTRQesM3BffWcCc5rRygRP")
USERNAME = "r3nsian"

DOWNLOADS = "downloads"
os.makedirs(DOWNLOADS, exist_ok=True)

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

HELP_TEXT = """
🤖 Selamat datang!
Perintah:
/start - Menampilkan pesan ini
/json2tgs - Convert file .json ke .tgs
/removebg - Hapus background gambar
Kirim file .tgs langsung untuk dijadikan emoji pack otomatis!
"""

# ===== START =====
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(HELP_TEXT)

# ===== JSON -> TGS =====
@client.on(events.NewMessage(pattern='/json2tgs'))
async def json2tgs(event):
    if event.message.file and event.message.file.name.endswith(".json"):
        file_path = await event.download_media(DOWNLOADS)
        tgs_path = file_path.replace(".json", ".tgs")
        try:
            # Minify JSON
            with open(file_path, 'r') as f:
                data = json.load(f)
            with open(tgs_path, 'w') as f:
                json.dump(data, f, separators=(',', ':'))
            await event.reply(f"File berhasil di-convert: {tgs_path}")
        except Exception as e:
            await event.reply(f"Gagal convert JSON ke TGS: {str(e)}")
    else:
        await event.reply("Kirim file .json Lottie!")

# ===== REMOVE BG =====
@client.on(events.NewMessage(pattern='/removebg'))
async def removebg(event):
    if event.message.file and event.message.file.name.endswith((".png",".jpg",".jpeg")):
        file_path = await event.download_media(DOWNLOADS)
        output_path = file_path.replace(".", "_nobg.")
        try:
            async with aiohttp.ClientSession() as session:
                with open(file_path, "rb") as f:
                    files = {"image_file": f}
                    headers = {"X-Api-Key": REMOVE_BG_KEY}
                    async with session.post("https://api.remove.bg/v1.0/removebg", data=files, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            with open(output_path, "wb") as out:
                                out.write(data)
                            await event.reply(f"Background dihapus! File: {output_path}")
                        else:
                            text = await resp.text()
                            await event.reply(f"Gagal remove.bg: {text}")
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
    else:
        await event.reply("Kirim gambar .png/.jpg/.jpeg untuk dihapus backgroundnya!")

# ===== TGS -> EMOJI PACK =====
@client.on(events.NewMessage)
async def tgs_handler(event):
    if event.message.file and event.message.file.name.endswith(".tgs"):
        file_path = await event.download_media(DOWNLOADS)
        await event.reply(f"File diterima: {file_path}\nMembuat emoji pack...")

        pack_name = f"rensci_emoji_{USERNAME}"
        pack_title = f"Rensci Emoji @{USERNAME}"

        input_doc = InputDocument(
            id=event.message.file.id,
            access_hash=event.message.file.access_hash,
            file_reference=event.message.file.file_reference
        )

        try:
            # Buat pack baru
            await client(CreateStickerSetRequest(
                user_id=await client.get_me(),
                title=pack_title,
                short_name=pack_name,
                stickers=[input_doc],
                animated=True
            ))
            await event.reply(f"Emoji pack dibuat!\nLink: t.me/addemoji/{pack_name}")
        except StickerSetInvalidError:
            # Pack sudah ada -> tambahkan sticker
            await client(AddStickerToSetRequest(
                stickers=[input_doc],
                stickerset=pack_name
            ))
            await event.reply(f"Sticker ditambahkan ke pack!\nLink: t.me/addemoji/{pack_name}")

client.start()
client.run_until_disconnected()

