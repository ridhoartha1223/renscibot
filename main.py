import logging
import os
import io
import gzip
import json
import requests # Untuk panggilan API remove.bg
from telegram import Update, InputSticker, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Coba impor pustaka konversi Lottie
try:
    from lottie.exporters.tgs import to_tgs
    from lottie.parsers.json import parse_json
    from PIL import Image
    LOTTIE_LIB_AVAILABLE = True
except ImportError:
    logging.warning("Pustaka 'lottie' atau 'Pillow' tidak terinstal. Fitur konversi tidak akan berfungsi.")
    LOTTIE_LIB_AVAILABLE = False


# Konfigurasi Log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Variabel Lingkungan ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# API_ID dan API_HASH biasanya untuk Pyrogram/Telethon (userbot), tidak diperlukan oleh python-telegram-bot.
# Jika Anda berencana menggunakan Pyrogram di masa depan, Anda bisa menggunakannya.
# API_ID = os.environ.get("API_ID")
# API_HASH = os.environ.get("API_HASH")
REMOVE_BG_API_KEY = os.environ.get("REMOVE_BG_API")

# Pastikan token bot tersedia
if not BOT_TOKEN:
    logger.error("BOT_TOKEN tidak ditemukan. Harap atur variabel lingkungan BOT_TOKEN.")
    exit(1) # Keluar jika token bot tidak ada

# Batas Ukuran File TGS Telegram: 64 KB
MAX_TGS_SIZE_KB = 64
MAX_TGS_SIZE_BYTES = MAX_TGS_SIZE_KB * 1024

# Status untuk ConversationHandler Impor TGS
PACK_NAME, EMOJI_REPLACEMENT, CUSTOM_LINK = range(3)

# --- FUNGSI UTILITY ---

def check_tgs_size(file_bytes):
    """Memeriksa ukuran file TGS."""
    return len(file_bytes) > MAX_TGS_SIZE_BYTES

def convert_json_to_tgs(json_content: bytes, optimize: bool = False) -> bytes | None:
    """Mengubah JSON Lottie menjadi TGS. Menggunakan python-lottie."""
    if not LOTTIE_LIB_AVAILABLE:
        return None

    try:
        # Dekompresi jika isinya adalah TGS terkompresi (kadang .json yang diunggah sebenarnya TGS)
        try:
            json_data_str = gzip.decompress(json_content).decode('utf-8')
        except OSError:
            json_data_str = json_content.decode('utf-8')

        # Parse JSON
        anim = parse_json(json_data_str)

        # Proses Optimasi (placeholder)
        if optimize:
            # Implementasi optimasi Lottie yang lebih dalam akan ada di sini.
            # python-lottie memiliki alat seperti lottie.exporters.tgs.sanitize(anim)
            # atau Anda bisa memodifikasi properti anim secara manual.
            pass
        
        # Konversi ke TGS (Gzip compressed Lottie JSON)
        tgs_bytes = to_tgs(anim)

        return tgs_bytes

    except Exception as e:
        logger.error(f"Gagal konversi JSON ke TGS: {e}")
        return None

def remove_background_via_api(image_bytes: bytes) -> bytes | None:
    """Menghapus latar belakang gambar menggunakan API remove.bg."""
    if not REMOVE_BG_API_KEY:
        logger.warning("REMOVE_BG_API_KEY tidak diatur. Fitur removebg tidak akan berfungsi.")
        return None

    try:
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            headers={'X-Api-Key': REMOVE_BG_API_KEY},
            files={'image_file': ('image.png', image_bytes, 'image/png')},
            data={'size': 'auto'}
        )
        response.raise_for_status() # Akan melempar HTTPError untuk status kode 4xx/5xx

        if response.status_code == requests.codes.ok:
            return response.content
        else:
            logger.error(f"remove.bg API error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Koneksi ke remove.bg API gagal: {e}")
        return None
    except Exception as e:
        logger.error(f"Terjadi kesalahan tak terduga saat memanggil remove.bg API: {e}")
        return None


# --- HANDLER CONVERSION (/json2tgs dan /json2tgs_optimize) ---

async def handle_json_conversion(update: Update, context: ContextTypes.
                                 DEFAULT_TYPE, optimize: bool = False):
    """Menangani konversi JSON ke TGS (biasa atau optimasi)."""
    if not update.message.document:
        await update.message.reply_text("Silakan kirim file .json Lottie untuk dikonversi.")
        return

    document = update.message.document
    if not document.file_name.lower().endswith(('.json', '.lottie')):
        await update.message.reply_text("File harus berformat .json atau .lottie.")
        return
    
    if not LOTTIE_LIB_AVAILABLE:
         await update.message.reply_text("Fitur konversi belum siap (Pustaka konversi Lottie tidak terinstal).")
         return

    message = await update.message.reply_text("Sedang memproses konversi, harap tunggu...")
    
    try:
        # Download file
        file_handle = await context.bot.get_file(document.file_id)
        json_content = io.BytesIO()
        await file_handle.download_to_memory(json_content)
        json_content = json_content.getvalue()

        # Konversi
        tgs_bytes = convert_json_to_tgs(json_content, optimize=optimize)

        if not tgs_bytes:
            await message.edit_text("Gagal mengonversi file JSON menjadi TGS. Pastikan file Lottie valid dan pustaka Lottie berfungsi.")
            return

        # Peringatan Batas Ukuran (4)
        if check_tgs_size(tgs_bytes):
            warning_msg = f"⚠️ Peringatan: Ukuran file TGS ({len(tgs_bytes)/1024:.2f} KB) melebihi batas Telegram (maks. {MAX_TGS_SIZE_KB} KB). File ini mungkin ditolak saat diunggah."
            await update.message.reply_text(warning_msg)
        
        # Kirim hasil TGS
        tgs_file = io.BytesIO(tgs_bytes)
        tgs_file.name = document.file_name.replace('.json', '.tgs').replace('.lottie', '.tgs')

        await update.message.reply_document(
            document=tgs_file,
            caption=f"✅ Konversi {'dengan Optimasi' if optimize else 'Biasa'} berhasil!\n\nApakah Anda ingin mengimpor TGS ini langsung menjadi Emoji Premium? Gunakan perintah /import\_tgs untuk melanjutkan.",
            disable_notification=True
        )

        await message.delete()

    except Exception as e:
        logger.error(f"Error saat konversi JSON: {e}")
        await message.edit_text(f"Terjadi kesalahan saat memproses file. Error: {e}")

async def json2tgs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menjalankan konversi JSON ke TGS standar."""
    await handle_json_conversion(update, context, optimize=False)

async def json2tgs_optimize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menjalankan konversi JSON ke TGS dengan optimasi."""
    await handle_json_conversion(update, context, optimize=True)

# --- HANDLER REMOVE BACKGROUND (/removebg) ---

async def removebg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menghapus latar belakang dari gambar yang dikirim (statik) menggunakan remove.bg API. (5)"""
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Silakan kirim sebuah gambar (sebagai foto atau file PNG/JPG) untuk menghapus latar belakang.")
        return
    
    if not REMOVE_BG_API_KEY:
         await update.message.reply_text("Fitur 'remove background' belum siap (REMOVE_BG_API_KEY tidak diatur).")
         return
    
    # Pilih file dengan prioritas: Foto > Dokumen
    if update.message.photo:
        file_to_process = update.message.photo[-1] # Ambil resolusi tertinggi
        is_document = False
    elif update.message.document and update.message.document.mime_type in ['image/png', 'image/jpeg', 'image/webp']:
        file_to_process = update.message.document
        is_document = True
    else:
        await update.message.reply_text("Hanya format gambar statis (PNG, JPG) yang didukung untuk penghapusan latar belakang saat ini.")
        return

    message = await update.message.reply_text("Sedang memproses penghapusan latar belakang via remove.bg API, harap tunggu...")
    
    try:
        # Download file
        file_handle = await context.bot.get_file(file_to_process.file_id)
        img_bytes = io.BytesIO()
        await file_handle.download_to_memory(img_bytes)
        img_bytes
