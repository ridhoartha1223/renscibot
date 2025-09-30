import json
import os
from telethon import TelegramClient, events
from telethon.tl.functions.stickers import CreateStickerSetRequest, AddStickerToSetRequest
from telethon.tl.types import InputStickerSetShortName, InputDocument

# ------------------- CONFIG -------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # atau langsung string "xxx:yyy"
SERVICE_ACCOUNT_FILE = "service_account.json"  # file .json di project
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")  # ID folder Google Drive

# Telethon client requires api_id and api_hash
api_id = int(os.environ.get("API_ID", "28235685"))
api_hash = os.environ.get("API_HASH", "03c741f65092cb2ccdd9341b9b055f13")

client = TelegramClient('bot', api_id, api_hash).start(bot_token=BOT_TOKEN)

# ------------------- EVENTS -------------------
@client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond("Bot aktif! Kirim sticker untuk ditambahkan ke set.")
    raise events.StopPropagation

@client.on(events.NewMessage)
async def sticker_handler(event):
    if event.sticker:
        sticker_set_name = "my_awesome_sticker_set_by_bot"  # nama short_name
        sticker_set_title = "My Sticker Set"  # judul set

        # Cek apakah sticker set sudah ada
        try:
            await client(GetStickerSetRequest(
                stickerset=InputStickerSetShortName(sticker_set_name),
                hash=0
            ))
            sticker_set_exists = True
        except:
            sticker_set_exists = False

        # Tambah sticker ke set
        if not sticker_set_exists:
            await client(CreateStickerSetRequest(
                user_id=await event.client.get_me(),
                title=sticker_set_title,
                short_name=sticker_set_name,
                stickers=[InputDocument(id=event.sticker.document.id,
                                        access_hash=event.sticker.document.access_hash,
                                        file_reference=event.sticker.document.file_reference)],
                animated=False
            ))
            await event.respond(f"Sticker set baru dibuat: {sticker_set_title}")
        else:
            await client(AddStickerToSetRequest(
                stickerset=InputStickerSetShortName(sticker_set_name),
                sticker=InputDocument(id=event.sticker.document.id,
                                      access_hash=event.sticker.document.access_hash,
                                      file_reference=event.sticker.document.file_reference)
            ))
            await event.respond(f"Sticker ditambahkan ke set: {sticker_set_title}")

# ------------------- RUN BOT -------------------
print("Bot berjalan...")
client.run_until_disconnected()
