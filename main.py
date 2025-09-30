# main.py
import os
import time
import asyncio
import logging
from pathlib import Path

from telethon import TelegramClient, events
from telethon.tl.types import InputDocument, InputStickerSetShortName
from telethon.tl.functions.stickers import CreateStickerSetRequest, AddStickerToSetRequest, GetStickerSetRequest
from telethon.errors import StickersetInvalidError, StickersTooManyError, RPCError

# ---------------- CONFIG ----------------
# Set these as environment variables or edit here for local testing (not recommended for production)
API_ID = int(os.environ.get("API_ID", "28235685"))
API_HASH = os.environ.get("API_HASH", "03c741f65092cb2ccdd9341b9b055f13")
BOT_TOKEN = os.environ.get("BOT_TOKEN", None)  # from @BotFather
# folder to store temporary downloads
TMP_DIR = Path(os.environ.get("TMP_DIR", "/tmp"))
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Sticker pack title fixed (contains @r3nsian as requested)
PACK_TITLE_TEMPLATE = "@r3nsian"

# Default emoji to assign automatically to every emoji (.tgs)
DEFAULT_EMOJI = "🙂"

# limit checks
MAX_STICKERS_PER_SET = 120  # Telegram limit for animated stickers as of writing may vary

# In-memory state per chat when expecting .tgs after /new
EXPECTING_TGS = {}  # chat_id -> True/False

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Client ----------------
# NOTE: This client uses a user account session (not bot). We'll also use bot token to receive incoming files,
# but to create sticker sets we must act as the user. Approach: run a TelegramClient for the USER session,
# and also a bot to receive messages OR run the same client and use its bot_token start method.
# We'll start the user client and then start it with bot_token to accept bot updates.
client = TelegramClient("user_session", API_ID, API_HASH)

# ---------------- Helpers ----------------
def make_short_name(user_id: int) -> str:
    """Create a unique short_name for the sticker/emoji pack (no '@', url-safe)."""
    t = int(time.time())
    return f"rensci_emoji_{user_id}_{t}"

async def create_pack_from_document(user_id, title, short_name, doc, emoji=DEFAULT_EMOJI, animated=True):
    """
    Create sticker set (emoji pack) with the given doc (Document object).
    doc should be a telethon.types.Document (uploaded to 'me').
    """
    # InputStickerSetItem is not required explicitly by Telethon if we use InputDocument in CreateStickerSetRequest
    from telethon.tl.types import InputStickerSetItem

    try:
        # Create set with single sticker
        req = CreateStickerSetRequest(
            user_id=user_id,
            title=title,
            short_name=short_name,
            stickers=[InputStickerSetItem(document=InputDocument(id=doc.id, access_hash=doc.access_hash, file_reference=doc.file_reference), emoji=emoji)],
            animated=animated
        )
        await client(req)
        return True, None
    except RPCError as e:
        return False, str(e)

async def add_to_pack(short_name, doc, emoji=DEFAULT_EMOJI, animated=True):
    """Add sticker document to existing pack."""
    from telethon.tl.types import InputStickerSetItem
    try:
        req = AddStickerToSetRequest(
            stickerset=InputStickerSetShortName(short_name),
            sticker=InputStickerSetItem(document=InputDocument(id=doc.id, access_hash=doc.access_hash, file_reference=doc.file_reference), emoji=emoji)
        )
        await client(req)
        return True, None
    except RPCError as e:
        return False, str(e)

async def pack_exists(short_name):
    try:
        await client(GetStickerSetRequest(stickerset=InputStickerSetShortName(short_name), hash=0))
        return True
    except RPCError:
        return False

# ---------------- Handlers ----------------
@client.on(events.NewMessage(pattern=r'^/start$'))
async def on_start(event):
    await event.reply("Halo! Untuk membuat emoji pack baru ketik /new")

@client.on(events.NewMessage(pattern=r'^/new$'))
async def on_new(event):
    chat_id = event.chat_id
    EXPECTING_TGS[chat_id] = True
    await event.reply("Kirim file .tgs sekarang (reply file ini). Bot akan membuat emoji pack otomatis dengan nama 'rensci emoji @r3nsian'.")

@client.on(events.NewMessage)
async def on_any_message(event):
    """
    General handler:
    - If we are expecting .tgs for that chat (after /new), and message contains a .tgs file,
      process create pack flow.
    - Otherwise ignore or respond politely.
    """
    chat_id = event.chat_id
    text = (event.raw_text or "").strip().lower() if event.raw_text else ""
    # If not expecting, ignore common commands handled elsewhere
    if not EXPECTING_TGS.get(chat_id, False):
        # Optionally respond to /help
        if text == "/help":
            await event.reply("/new - buat emoji pack otomatis\nAfter /new send a .tgs file (animated emoji).")
        return

    # Now we are expecting .tgs
    # Check for file/document
    msg = event.message
    doc = None
    if msg.document:
        # document is present; check file name
        fname = getattr(msg.document, "file_name", "") or ""
        if fname.lower().endswith(".tgs") or (msg.document.mime_type and "tgs" in (msg.document.mime_type or "")):
            doc = msg.document
    # also check media with .tgs in attributes
    if not doc:
        await event.reply("File tidak dikenali atau bukan .tgs. Silakan kirim file .tgs saja.")
        EXPECTING_TGS.pop(chat_id, None)
        return

    # Got a .tgs file — proceed
    await event.reply("Menerima file .tgs... proses membuat pack. Tunggu sebentar...")
    EXPECTING_TGS.pop(chat_id, None)  # reset expectation

    # Download it locally
    try:
        # download to temp
        local_path = TMP_DIR / f"{int(time.time())}_{doc.file_name or 'emoji.tgs'}"
        await event.client.download_media(msg, file=str(local_path))
        logger.info("Downloaded to %s", local_path)
    except Exception as e:
        await event.reply(f"Gagal download file: {e}")
        return

    # Upload file to 'me' (self) to get a Document object with id/access_hash
    try:
        self_msg = await client.send_file('me', str(local_path), force_document=True)
        uploaded_doc = self_msg.document
    except Exception as e:
        await event.reply(f"Gagal upload ke akun kamu (internal): {e}")
        return

    # Prepare pack identifiers
    user = await client.get_me()
    user_id = user.id
    title = PACK_TITLE_TEMPLATE
    short_name = make_short_name(user_id)  # must be unique and url-safe

    # Create pack (try)
    try:
        success, err = await create_pack_from_document(user_id=user_id, title=title, short_name=short_name, doc=uploaded_doc, emoji=DEFAULT_EMOJI, animated=True)
        if not success:
            # if creation failed due to e.g. short_name conflict, try alternate short_name
            logger.warning("Create pack failed: %s", err)
            # try some retries with slightly different short_name
            for i in range(3):
                short_name = make_short_name(user_id) + f"_{i}"
                success, err = await create_pack_from_document(user_id=user_id, title=title, short_name=short_name, doc=uploaded_doc, emoji=DEFAULT_EMOJI, animated=True)
                if success:
                    break
        if not success:
            # maybe pack exists or other issue; try to add to an existing pack named by pattern (rare)
            await event.reply(f"Gagal membuat pack: {err}")
            # cleanup local file
            try:
                local_path.unlink(missing_ok=True)
            except Exception:
                pass
            return
    except Exception as e:
        await event.reply(f"Terjadi error saat membuat pack: {e}")
        return

    # Success — build link and reply
    pack_link = f"https://t.me/addstickers/{short_name}"
    await event.reply(f"Pack berhasil dibuat: {title}\nLink: {pack_link}\nEmoji otomatis: {DEFAULT_EMOJI}\nKamu bisa pakai emoji ini untuk profil Telegram (jika akun mendukung).")

    # Send back the .tgs file so user can download/use
    try:
        await event.
        reply(file=str(local_path))
    except Exception:
        # fallback: send the original document if possible
        try:
            await event.reply(await client.get_messages('me', ids=uploaded_doc.id))
        except Exception:
            pass

    # cleanup local
    try:
        local_path.unlink(missing_ok=True)
    except Exception:
        pass

# ---------------- Run ----------------
if name == "__main__":
    print("Pastikan kamu sudah meng-autentikasi user session secara lokal terlebih dahulu.")
    print("Jika belum, jalankan python main.py di mesin lokal, masukkan nomor Telegram untuk login.")
    print("Set environment variables: API_ID, API_HASH, BOT_TOKEN (opsional).")
    client.start()  # will prompt login locally (interactive) if session not present
    print("Client started. Bot siap menerima perintah.")
    client.run_until_disconnected()
        
