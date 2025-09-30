import os
import logging
import re
import subprocess
from typing import Optional
# PERBAIKAN: Impor utama dari telegram
from telegram import Update, ForceReply
# Impor constants (ChatAction dan ParseMode) dari telegram.constants
from telegram.constants import ParseMode, ChatAction 
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from removebg import RemoveBg

# --- Konfigurasi Awal ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Ambil variabel lingkungan
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMOVE_BG_KEY = os.getenv("REMOVE_BG_KEY")
DOWNLOADS_DIR = "downloads"

# Definisikan State untuk ConversationHandler (Feature 2: .tgs)
GET_PACK_NAME = 1 

# Pastikan folder downloads ada
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# --- FUNGSI IMPLEMENTASI LOTTIE/TGS NYATA ---

def run_lottie_min(input_path: str, output_path: str):
    """Menjalankan command lottie-min untuk optimasi/konversi."""
    command = ['lottie-min', input_path, '-o', output_path]
    logging.info(f"Running lottie-min command: {' '.join(command)}")
    
    # Jalankan command dengan timeout
    result = subprocess.run(command, capture_output=True, text=True, timeout=90) 
    
    if result.returncode != 0:
        logging.error(f"lottie-min failed. Stderr: {result.stderr}")
        if os.path.exists(output_path):
            os.remove(output_path)
        
        error_msg = result.stderr.strip()
        if "must be an absolute path" in error_msg:
             user_friendly_error = "File Lottie/JSON tampaknya memiliki masalah path internal atau format."
        elif "JSON is malformed" in error_msg:
             user_friendly_error = "Struktur file JSON/Lottie rusak atau tidak valid."
        else:
             user_friendly_error = f"Kesalahan pemrosesan Lottie (Code {result.returncode})."
             
        raise Exception(user_friendly_error)
        
    logging.info(f"lottie-min finished successfully.")

def optimize_tgs_file(file_path: str) -> str:
    """Menerima path .tgs, optimasi, dan mengembalikan path baru."""
    optimized_path = os.path.join(DOWNLOADS_DIR, f"opt_{os.urandom(4).hex()}.tgs")
    run_lottie_min(file_path, optimized_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    return optimized_path

def convert_json_to_tgs_file(json_path: str) -> str:
    """Menerima path .json, konversi ke .tgs, dan mengembalikan path .tgs."""
    tgs_path = os.path.join(DOWNLOADS_DIR, f"conv_{os.urandom(4).hex()}.tgs")
    run_lottie_min(json_path, tgs_path)
    if os.path.exists(json_path):
        os.remove(json_path)
    return tgs_path


# --- HANDLER: /start (Feature 1) ---
async def start_command(update: Update, context) -> None:
    """Menampilkan pesan selamat datang, command, dan kegunaan."""
    
    # Kirim Chat Action: TYPING
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    welcome_message = (
        "👋 **Selamat datang! Saya Bot Stiker Animasi (.tgs) Anda.**\n\n"
        "Saya dapat membantu Anda membuat dan mengoptimalkan stiker animasi untuk Telegram.\n\n"
        "**Cara Penggunaan:**\n"
        "🔸 Stiker .TGS: Cukup kirim file .tgs Anda, dan saya akan secara otomatis "
        "mengoptimalkan ukurannya, lalu meminta Anda membuat *share link* pack.\n"
        "🔸 Konversi: Gunakan perintah `/json2tgs` dengan membalas file .json Anda.\n"
        "🔸 Background: Gunakan `/removebg` dengan membalas foto (.jpg/.png) untuk menghapus latar belakang.\n\n"
        "Tekan tombol Menu (`/`) di bawah untuk melihat daftar perintah lengkap."
    )
    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

# --- HANDLER: Feature 2: Proses Otomatis .TGS (Multi-Langkah) ---

async def handle_tgs_file(update: Update, context) -> int:
    """Langkah 1: Menerima file .tgs, mengoptimalkan, dan meminta nama pack."""
    file_id = update.message.document.file_id
    user_id = update.effective_user.id
    download_path: Optional[str] = None
    await update.message.reply_text("📥 File .tgs diterima. Mulai proses *minifikasi*...")
    
    try:
        # 1. Unduh File
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        new_file = await context.bot.get_file(file_id)
        safe_name = f"{user_id}_{os.urandom(4).hex()}.tgs"
        download_path = os.path.join(DOWNLOADS_DIR, safe_name)
        await new_file.download_to_drive(download_path)
        
        # 2. Optimasi (Minify)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        optimized_path = optimize_tgs_file(download_path) 
        
        # Simpan path file di context.user_data
        context.user_data['tgs_path'] = optimized_path
        
        await update.message.reply_text(
            "✨ Optimasi Berhasil! File siap untuk diunggah.\n"
            "Sekarang, balas pesan ini dengan nama unik untuk paket emoji Anda (contoh: `my_cool_emojis`)\n"
            "*(Hanya huruf dan angka, tanpa spasi)*",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return GET_PACK_NAME
        
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal Memproses. Error Lottie: `{e}`")
        if download_path and os.path.exists(download_path):
            os.remove(download_path)
        return ConversationHandler.END

async def get_pack_name(update: Update, context) -> int:
    """Langkah 2: Menerima nama pack, generate link, kirim file, dan selesai."""
    pack_name = update.message.text.strip()
    original_file_path: Optional[str] = context.user_data.pop('tgs_path', None)
    
    def cleanup():
        if original_file_path and os.path.exists(original_file_path):
            os.remove(original_file_path)

    if not original_file_path or not os.path.exists(original_file_path):
        await update.message.reply_text("❌ Proses kadaluarsa. Silakan kirim ulang file .tgs Anda.")
        return ConversationHandler.END

    if not re.fullmatch(r'^[a-zA-Z0-9]+$', pack_name):
        await update.message.reply_text(
            "⚠️ Nama paket tidak valid. Harap gunakan hanya huruf dan angka (misalnya: `MyPack123`)."
        )
        cleanup()
        return ConversationHandler.END

    # Generate Link & Kirim Hasil
    emoji_pack_link = f"t.me/addemoji/{pack_name}"
    
    response_message = (
        f"🥳 **Paket Emoji Anda Siap!**\n\n"
        f"Nama Paket: `{pack_name}`\n"
        f"Link Tambah Emoji: [KLIK DI SINI]({emoji_pack_link})\n\n"
        f"File .tgs yang sudah dioptimalkan terlampir di bawah ini. Gunakan file ini saat Anda membuka tautan di atas."
    )
    
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        with open(original_file_path, 'rb') as f:
            await update.message.reply_document(
                document=f, 
                caption=response_message, 
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal mengirim file hasil optimasi: `{e}`")
    finally:
        cleanup()

    return ConversationHandler.END

async def cancel_tgs(update: Update, context) -> int:
    """Membatalkan proses .tgs jika ada teks yang tidak terduga."""
    if 'tgs_path' in context.user_data:
        file_path = context.user_data.pop('tgs_path')
        if os.path.exists(file_path):
            os.remove(file_path)
    
    if update.message.document is None or not (filters.Document.ALL & filters.Regex(r"\.tgs$")).check(update.message):
        await update.message.reply_text("❌ Proses pembuatan paket dibatalkan.")
    return ConversationHandler.END


# --- HANDLER: Feature 3: Konversi .json ke .tgs ---
async def json2tgs_command(update: Update, context) -> None:
    """Convert file .json menjadi .tgs"""
    message = update.message
    # Periksa pesan balasan atau pesan itu sendiri
    target_message = message.reply_to_message if message.reply_to_message and message.reply_to_message.document else message
    
    if not (target_message.document and target_message.document.mime_type == 'application/json'):
        await message.reply_text("⚠️ Format Salah. Balas file .json dengan perintah /json2tgs.")
        return

    file_id = target_message.document.file_id
    json_path: Optional[str] = None
    tgs_path: Optional[str] = None
    
    try:
        await message.reply_text("⏳ File .json diterima. Mengkonversi dan mengoptimalkan...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)

        # 1. Unduh File
        new_file = await context.bot.get_file(file_id)
        json_path = os.path.join(DOWNLOADS_DIR, f"temp_{os.urandom(4).hex()}.json")
        await new_file.download_to_drive(json_path)
        
        # 2. Convert & Optimasi
        tgs_path = convert_json_to_tgs_file(json_path) 
        
        # 3. Kirim Balik
        with open(tgs_path, 'rb') as f:
             await message.reply_document(document=f, caption="✅ Konversi Selesai! File .tgs terlampir.", parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await message.reply_text(f"❌ Gagal Konversi. Error Lottie: `{e}`")
    finally:
        if json_path and os.path.exists(json_path):
            os.remove(json_path)
        if tgs_path and os.path.exists(tgs_path):
            os.remove(tgs_path)

# --- HANDLER: Feature 4: Remove Background (.png/.jpg) ---
async def removebg_command(update: Update, context) -> None:
    """Hapus background dari gambar menggunakan remove.bg API"""
    message = update.message
    target_message = message.reply_to_message if message.reply_to_message else message
    
    if not REMOVE_BG_KEY:
        await message.reply_text("❌ Konfigurasi Kurang. API Key Remove.bg belum disetel.")
        return
    
    # Cek file: foto atau dokumen (.png/.jpg)
    is_photo = bool(target_message.photo)
    is_document = target_message.document and target_message.document.mime_type in ['image/png', 'image/jpeg']

    if not (is_photo or is_document):
        await message.reply_text("⚠️ Format Salah. Balas file gambar (.png/.jpg) dengan perintah /removebg.")
        return
        
    file_id = target_message.photo[-1].file_id if is_photo else target_message.document.file_id
    
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    
    try:
        await message.reply_text("⏳ Gambar diterima. Memproses penghapusan latar belakang...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)

        # 1. Unduh File
        new_file = await context.bot.get_file(file_id)
        input_path = os.path.join(DOWNLOADS_DIR, f"in_{os.urandom(4).hex()}.temp")
        output_path = os.path.join(DOWNLOADS_DIR, f"out_{os.urandom(4).hex()}_nobg.png")
        await new_file.download_to_drive(input_path)
        
        # 2. Proses Remove.bg
        rmbg = RemoveBg(REMOVE_BG_KEY, "error.log") 
        rmbg.remove_background_from_img_file(input_path, size="regular", output_path=output_path)
        
        # 3. Kirim Balik
        with open(output_path, 'rb') as f:
             await message.reply_document(document=f, caption="✅ Background Dihapus! File PNG transparan terlampir.", parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await message.reply_text(f"❌ Gagal Menghapus Background. Pastikan Anda memiliki kuota API dan file valid: `{e}`")
    finally:
        # 4. Bersihkan
        if input_path and os.path.exists(input_path):
            os.remove(input_path)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)

# --- FUNGSI UTAMA (MAIN) ---
def main() -> None:
    """Menjalankan bot."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN tidak ditemukan. Bot tidak bisa dijalankan.")

    application = Application.builder().token(BOT_TOKEN).build()
    
    # Definisikan Filter Kustom menggunakan Regex
    TGS_FILTER = filters.Document.ALL & filters.Regex(r"\.tgs$")
    JSON_FILTER = filters.Document.ALL & filters.Regex(r"\.json$")
    
    # Conversation Handler untuk proses .tgs (Feature 2)
    tgs_handler = ConversationHandler(
        entry_points=[MessageHandler(TGS_FILTER, handle_tgs_file)], 
        states={
            GET_PACK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pack_name)],
        },
        fallbacks=[MessageHandler(filters.ALL, cancel_tgs)], 
    )

    # 2. Tambahkan Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(tgs_handler)
    
    # Handlers untuk /json2tgs (Feature 3)
    application.add_handler(CommandHandler("json2tgs", json2tgs_command))
    application.add_handler(MessageHandler(JSON_FILTER & filters.Caption("json2tgs"), json2tgs_command))

    # Handlers untuk /removebg (Feature 4)
    application.add_handler(CommandHandler("removebg", removebg_command))
    application.add_handler(MessageHandler((filters.PHOTO | filters.Document.ALL) & (filters.Caption("removebg") | filters.Caption("/removebg")), removebg_command))
    
    # 3. Jalankan Bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

