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

        # Kirim hasil TGS
        sent = await message.reply_document(tgs_path, caption=caption)

        # Simpan state user untuk inline buttons import
        user_state[message.from_user.id] = {
            "tgs_path": tgs_path,
            "step": "ask_import"
        }

        # Kirim inline button
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Import ke New Premium Emoji Pack", callback_data="import_yes")],
            [InlineKeyboardButton("❌ Skip", callback_data="import_no")]
        ])
        await message.reply_text("Apakah ingin mengimpor file ini sebagai New Premium Emoji Pack?", reply_markup=buttons)

# --- Callback button handler ---
@bot.on_callback_query()
async def button_handler(client, callback_query):
    user_id = callback_query.from_user.id
    state = user_state.get(user_id)
    if not state:
        await callback_query.answer("State tidak ditemukan.", show_alert=True)
        return

    if callback_query.data == "import_yes":
        state["step"] = "input_pack_name"
        await callback_query.message.reply_text("Masukkan nama New Premium Emoji Pack:")
    elif callback_query.data == "import_no":
        user_state.pop(user_id)
        await callback_query.message.reply_text("❌ Proses import dibatalkan.")
    await callback_query.answer()

# --- Handle interactive text input for import ---
@bot.on_message(filters.text)
async def handle_text(client, message: Message):
    user_id = message.from_user.id
    state = user_state.get(user_id)
    if not state: return

    step = state.get("step")

    if step == "input_pack_name":
        state["pack_name"] = message.text
        state["step"] = "input_emoji"
        await message.reply_text("Masukkan replacement emoji untuk pack ini (misal: 😎):")
    elif step == "input_emoji":
        state["emoji"] = message.text
        state["step"] = "input_link"
        await message.reply_text("Masukkan link referensi (optional) atau ketik 'skip' untuk lewati:")
    elif step == "input_link":
        link_input = message.text
        state["link"] = None if link_input.lower() == "skip" else link_input

        # Buat instruksi siap pakai
        pack_name = state["pack_name"]
        ready_text = f"✅ New Premium Emoji Pack siap diimpor!\n\n" \
                     f"Nama Pack: {pack_name}\n" \
                     f"Replacement Emoji: {state['emoji']}\n\n" \
                     f"Langkah Import:\n" \
                     f"1. Buka akun Telegram Premium.\n" \
                     f"2. Pilih 'Add Emoji Pack'.\n" \
                     f"3. Upload file .tgs berikut:"

        if state["link"]:
            ready_text += f"\n📌 Referensi Link: {state['link']}"

        await message.reply_text(ready_text)
        await message.reply_document(state["tgs_path"], caption="File .tgs untuk import")

        # Bersihkan state
        user_state.pop(user_id)

# --- Remove background ---
@bot.on_message(filters.command("removebg") & filters.photo)
async def remove_bg(client, message: Message):
    photo_path = await message.download()
    rmbg = RemoveBg(REMOVE_BG_API, "error.log")
    output_path = photo_path.replace(".jpg", "_transparent.png").replace(".png", "_transparent.png")
    rmbg.remove_background_from_img_file(photo_path)
    await message.reply_document(output_path, caption="✅ Background dihapus (transparan).")

# --- Main async run ---
async def main():
    sync_time()
    await bot.start()
    print("Bot started!")
    await idle()
    await bot.stop()

if name == "__main__":
    asyncio.run(main())

