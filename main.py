import json
import gzip
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeFilename

# ================== CONFIG ==================
API_ID = 28235685        # ganti dengan api_id mu
API_HASH = "03c741f65092cb2ccdd9341b9b055f13"  # ganti dengan api_hash mu
BOT_TOKEN = "8319183574:AAHIi3SX218DNqS-owUcQ9Xyvc_D4Mk14Rw"
# ===========================================

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Fungsi convert JSON → TGS
def json_to_tgs(json_bytes, output_name="emoji.tgs"):
    data = json.loads(json_bytes)
    json_min = json.dumps(data, separators=(',', ':'))
    tgs_bytes = gzip.compress(json_min.encode("utf-8"))
    return tgs_bytes

# /start
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "Halo! Kirim file .json Lottie kamu, aku akan ubah jadi .tgs siap untuk @Stickers!"
    )

# Terima file JSON
@client.on(events.NewMessage)
async def handle_file(event):
    if event.file and event.file.name.endswith(".json"):
        await event.reply("Menerima file, sedang proses convert ke TGS...")
        file_path = await event.download_media()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_bytes = f.read()
            tgs_bytes = json_to_tgs(json_bytes)
            # Kirim balik sebagai .tgs
            await client.send_file(
                event.chat_id,
                tgs_bytes,
                force_document=True,
                attributes=[DocumentAttributeFilename("emoji.tgs")]
            )
        except Exception as e:
            await event.reply(f"Gagal convert: {e}")
    else:
        if event.message.message.startswith("/"):
            return
        await event.reply("Kirim file .json Lottie saja ya!")

print("Bot berjalan...")
client.run_until_disconnected()
