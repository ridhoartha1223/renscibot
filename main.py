import os
import json
from telethon import TelegramClient, events
from telethon.tl.types import InputDocument
from telethon.tl.functions.stickers import CreateStickerSetRequest, AddStickerToSetRequest
from telethon.tl.functions.messages import GetStickerSetRequest

# ===== CONFIG =====
BOT_TOKEN = "8319183574:AAHIi3SX218DNqS-owUcQ9Xyvc_D4Mk14Rw"
API_ID = 28235685  # ganti dengan api_id Telegram kamu
API_HASH = "03c741f65092cb2ccdd9341b9b055f13"  # ganti dengan api_hash Telegram kamu
OWNER_USERNAME = "@r3nsian"  # nama yang akan muncul di pack

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ===== HANDLER =====
@client.on(events.NewMessage(pattern='/new'))
async def new_pack_handler(event):
    await event.respond("Silakan kirim file .tgs untuk dibuatkan emoji pack otomatis.")

@client.on(events.NewMessage(func=lambda e: e.file and e.file.name.endswith('.tgs')))
async def tgs_handler(event):
    try:
        # Simpan file yang dikirim
        file_path = await event.download_media()
        
        # Siapkan input document untuk Telegram
        doc = InputDocument(id=event.file.id, access_hash=event.file.access_hash, file_reference=event.file.file_reference)
        
        # Nama pack otomatis
        pack_name = f"rensci_emoji_by_{OWNER_USERNAME}"
        pack_title = f"Rensci Emoji @{OWNER_USERNAME}"
        
        # Buat pack baru
        await client(CreateStickerSetRequest(
            user_id=event.sender_id,
            title=pack_title,
            short_name=pack_name,
            stickers=[doc],
            stickers_format='tgs',
            stickers_type='regular'
        ))
        
        await event.respond(f"Emoji pack dibuat! Nama pack: {pack_title}\nSiap digunakan di Telegram.")
    
    except Exception as e:
        await event.respond(f"Terjadi error: {str(e)}")

print("Bot aktif...")
client.run_until_disconnected()
