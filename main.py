import os
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from lottie import objects, exporters, parsers
from removebg import RemoveBg

# --- Environment Variables from Railway ---
API_HASH = os.getenv("API_HASH")
API_ID = int(os.getenv("API_ID"))
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMOVE_BG_API = os.getenv("REMOVE_BG_API")

# --- Initialize Bot ---
bot = Client("emoji_bot",
             api_id=API_ID,
             api_hash=API_HASH,
             bot_token=BOT_TOKEN)

# --- State storage for interactive import ---
user_state = {}  # {user_id: {"step": ..., "tgs_path": ..., "pack_name": ..., "emoji": ..., "instructions": ...}}

# --- Helper Functions ---
def json_to_tgs(json_file_path, optimize=False):
    """Convert .json Lottie to .tgs"""
    animation = parsers.tgs.parse_tgs(json_file_path)
    if optimize:
        animation = exporters.tgs.minify(animation)
    tgs_path = json_file_path.replace(".json", "_converted.tgs")
    exporters.tgs.export_tgs(animation, tgs_path)
    return tgs_path

def check_size_limit(file_path):
    """Check if tgs size > 64KB"""
    return os.path.getsize(file_path) > 64 * 1024

# --- Start Command ---
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

# --- JSON to TGS ---
@bot.on_message(filters.command(["json2tgs", "json2tgs_optimize"]) & filters.document)
async def json2tgs(client, message: Message):
    optimize = message.text.endswith("optimize")
    
    if not message.document.file_name.endswith(".json"):
        await message.reply_text("❌ File harus berekstensi .json")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, message.document.file_name)
        await message.download(file_path=json_path)
        
        tgs_path = json_to_tgs(json_path, optimize=optimize)
        size_warning = check_size_limit(tgs_path)

        reply_text = f"✅ Konversi selesai.\n"
        if size_warning:
            reply_text += "⚠️ Peringatan: File .tgs lebih dari 64KB, mungkin tidak bisa dijadikan emoji premium."

        await message.reply_document(tgs_path, caption=reply_text)
        
        # Simpan path sementara untuk import interaktif
        user_state[message.from_user.id] = {"tgs_path": tgs_path, "step": "ask_import"}
        await message.reply_text("Apakah kamu ingin mengimpor file ini sebagai New Premium Emoji Pack? Balas 'ya' / 'tidak'.")

# --- Import TGS ke New Premium Emoji Pack ---
@bot.on_message(filters.command("import_tgs") & filters.document)
async def import_tgs(client, message: Message):
    if not message.document.file_name.endswith(".tgs"):
        await message.reply_text("❌ File harus berekstensi .tgs")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        tgs_path = os.path.join(tmpdir, message.document.file_name)
        await message.download(file_path=tgs_path)

        if check_size_limit(tgs_path):
            await message.reply_text("⚠️ File lebih dari 64KB! Tidak bisa dijadikan emoji premium.")
            return

        user_state[message.from_user.id] = {"tgs_path": tgs_path, "step": "input_pack_name"}
        await message.reply_text("Masukkan nama New Premium Emoji Pack:")

# --- Handle interactive text responses ---
@bot.on_message(filters.text)
async def handle_text(client, message: Message):
    user_id = message.from_user.id
    state = user_state.get(user_id)
    if not state:
        return  # tidak ada state aktif

    step = state.get("step")

    # Step 1: Konfirmasi import setelah convert
    if step == "ask_import":
        if message.text.lower() in ["ya", "yes"]:
            await message.reply_text("Masukkan nama New Premium Emoji Pack:")
            state["step"] = "input_pack_name"
        else:
            await message.reply_text("❌ Proses import dibatalkan.")
            user_state.pop(user_id)
        return

    # Step 2: Nama pack
    if step == "input_pack_name":
        state["pack_name"] = message.text
        await message.reply_text("Masukkan replacement emoji untuk pack ini (misal: 😎):")
        state["step"] = "input_emoji"
        return

    # Step 3: Replacement emoji
    if step == "input_emoji":
        state["emoji"] = message.text
        await message.reply_text(
            "Masukkan link referensi (optional) atau ketik 'skip' untuk lewati:"
        )
        state["step"] = "input_link"
        return

    # Step 4: Custom link / finalisasi
    if step == "input_link":
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
        return

# --- Remove Background ---
@bot.on_message(filters.command("removebg") & filters.photo)
async def remove_bg(client, message: Message):
    photo_path = await message.download()
    rmbg = RemoveBg(REMOVE_BG_API, "error.log")
    output_path = photo_path.replace(".jpg", "_transparent.png").replace(".png", "_transparent.png")
    rmbg.remove_background_from_img_file(photo_path)
    await message.reply_document(output_path, caption="✅ Background dihapus (transparan).")

# --- Run Bot ---
bot.run()
