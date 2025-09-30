import os
import json
import shutil
import requests
from telethon import TelegramClient, events

# ===== ENV VAR =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
REMOVE_BG_KEY = os.getenv("REMOVE_BG_KEY")  # API key remove.bg

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}

os.makedirs("downloads", exist_ok=True)

# ===== START / HELP =====
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "👋 Selamat datang!\n\n"
        "Perintah tersedia:\n"
        "/json2tgs - Kirim file .json untuk convert ke .tgs\n"
        "/tgs2pack - Kirim file .tgs untuk buat emoji pack link\n"
        "/removebg - Kirim gambar untuk hapus background\n"
        "/help - Tampilkan info perintah"
    )

@client.on(events.NewMessage(pattern="/help"))
async def help(event):
    await start(event)

# ===== COMMAND STATE =====
@client.on(events.NewMessage(pattern="/json2tgs"))
async def json2tgs_command(event):
    user_state[event.sender_id] = "waiting_json"
    await event.reply("📤 Silahkan kirim file .json untuk dikonversi ke .tgs")

@client.on(events.NewMessage(pattern="/tgs2pack"))
async def tgs2pack_command(event):
    user_state[event.sender_id] = "waiting_tgs"
    await event.reply("📤 Silahkan kirim file .tgs untuk dibuat menjadi emoji pack")

@client.on(events.NewMessage(pattern="/removebg"))
async def removebg_command(event):
    user_state[event.sender_id] = "waiting_removebg"
    await event.reply("📤 Silahkan kirim file gambar (png/jpg) untuk dihapus backgroundnya")

# ===== FILE HANDLER =====
@client.on(events.NewMessage(func=lambda e: e.file))
async def file_handler(event):
    state = user_state.get(event.sender_id)
    if not state:
        return

    file_path = f"downloads/{event.file.name}"
    await event.download_media(file_path)

    if state == "waiting_json" and file_path.endswith(".json"):
        await event.reply("✅ File diterima. Sedang konversi .json → .tgs ...")
        try:
            tgs_path = convert_json_to_tgs(file_path)
            await event.reply(file=tgs_path)
        except Exception as e:
            await event.reply(f"❌ Gagal convert: {e}")

    elif state == "waiting_tgs" and file_path.endswith(".tgs"):
        await event.reply("✅ File .tgs diterima. Membuat link emoji pack ...")
        try:
            link = create_emoji_pack(file_path)
            await event.reply(f"🎉 Emoji pack siap: {link}")
        except Exception as e:
            await event.reply(f"❌ Gagal buat link pack: {e}")

    elif state == "waiting_removebg" and file_path.lower().endswith((".png",".jpg",".jpeg")):
        await event.reply("✅ Gambar diterima. Menghapus background ...")
        try:
            out_path = remove_bg(file_path)
            await event.reply(file=out_path)
        except Exception as e:
            await event.reply(f"❌ Gagal hapus background: {e}")

    else:
        await event.reply("⚠️ File tidak sesuai tipe yang diminta")

    user_state.pop(event.sender_id, None)

# ===== FUNCTION =====
def convert_json_to_tgs(json_path):
    """
    Convert JSON ke TGS (minimal optimization)
    """
    import lottie
    tgs_path = json_path.replace(".json", ".tgs")
    animation = lottie.parsers.tgs.parse_tgs(json_path)
    lottie.parsers.tgs.write_tgs(animation, tgs_path)
    return tgs_path

def create_emoji_pack(tgs_path):
    """
    Dummy: generate link untuk user bisa simpan pack
    """
    return f"https://t.me/addemoji/rensciemojipack"

def remove_bg(image_path):
    """
    Remove background via remove.bg API
    """
    out_path = image_path.replace(".", "_nobg.")
    with open(image_path, "rb") as f:
        response = requests.post(
            "https://api.remove.bg/v1.0/removebg",
            files={"image_file": f},
            data={"size":"auto"},
            headers={"X-Api-Key": REMOVE_BG_KEY},
        )
    if response.status_code == 200:
        with open(out_path, "wb") as out:
            out.write(response.content)
            return out_path
    else:
        raise Exception(f"Remove.bg error: {response.status_code} {response.text}")

client.run_until_disconnected()
