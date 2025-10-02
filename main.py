import logging
import requests
import os
from telegram import Update
from telegram.ext import Application, CommandHandler
from io import BytesIO

# --- 1. KONFIGURASI BOT DAN API KEY (Ambil dari Environment Variables Railway) ---

# Railway akan menyediakan variabel ini di pengaturan Environment Variables Anda.
# Kita ambil menggunakan os.environ.get()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
HUGGING_FACE_API_KEY = os.environ.get("HUGGING_FACE_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # Ini URL yang dibuat oleh Railway

# Tambahkan PORT karena Railway mengharuskan kita mendengarkan port tertentu
PORT = int(os.environ.get("PORT", "8080"))

# Model Hugging Face dan Headers
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1" 
HEADERS = {"Authorization": f"Bearer {HUGGING_FACE_API_KEY}"}

# Konfigurasi Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 2. FUNGSI UNTUK MENGIRIM PERMINTAAN KE HUGGING FACE ---

def query_huggingface(payload):
    """Mengirim prompt ke API Hugging Face dan mengembalikan data gambar biner."""
    response = requests.post(API_URL, headers=HEADERS, json=payload)
    
    if response.status_code == 200:
        return response.content
    else:
        logger.error(f"Error dari Hugging Face API: {response.status_code} - {response.text}")
        if "is currently loading" in response.text:
            raise Exception("Model AI sedang dimuat (Cold Start). Coba lagi dalam 10 detik.")
        raise Exception("Gagal menghasilkan gambar dari Hugging Face.")

# --- 3. FUNGSI BOT TELEGRAM ---

async def start(update: Update, context) -> None:
    """Mengirim pesan sambutan saat perintah /start digunakan."""
    await update.message.reply_text(
        "Halo! Saya adalah Bot Generator Gambar AI GRATIS (di-host di Railway). "
        "Gunakan perintah /gambar [teks deskripsi Anda] untuk membuat gambar.\n\n"
        "Contoh: /gambar king arthur"
    )

async def generate_image(update: Update, context) -> None:
    """Menghasilkan gambar AI dari teks pengguna menggunakan Hugging Face."""
    
    if not context.args:
        await update.message.reply_text("Mohon berikan deskripsi gambar setelah perintah /gambar.")
        return

    user_prompt = " ".join(context.args)
    
    # LOGIKA CHIBI OTOMATIS
    chibi_style = ", cute chibi style, miniature figure, vibrant colors, digital illustration, high quality"
    final_prompt = user_prompt + chibi_style
    
    await update.message.reply_text(
        f"⏳ Sedang membuat gambar untuk '{user_prompt}' dalam gaya chibi. "
        f"Ini mungkin memakan waktu 30-60 detik karena menggunakan layanan gratis. Mohon bersabar..."
    )

    try:
        image_bytes = query_huggingface({"inputs": final_prompt})
        
        image_file = BytesIO(image_bytes)
        image_file.name = "ai_chibi_image.png"
        
        await update.message.reply_photo(
            photo=image_file, 
            caption=f"✨ {user_prompt} (Gaya Chibi)"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Maaf, terjadi kesalahan: {e}")


# --- 4. FUNGSI UNTUK MENJALANKAN BOT DENGAN WEBHOOKS ---

def main() -> None:
    """Menjalankan bot menggunakan Webhooks untuk deployment."""
    
    if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL:
        logger.error("TELEGRAM_BOT_TOKEN atau WEBHOOK_URL belum diset. Bot tidak bisa dijalankan.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Menambahkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gambar", generate_image))

    # Konfigurasi Webhook untuk Railway
    # Path (jalur) yang akan didengarkan oleh bot di Railway
    webhook_path = "/telegram" 

    # 1. Menentukan URL untuk didengarkan (port Railway)
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=webhook_path
    )
    # 2. Memberi tahu Telegram URL Webhook kita
    # URL lengkap yang didaftarkan ke Telegram adalah URL domain Railway + path
    full_webhook_url = WEBHOOK_URL + webhook_path
    application.bot.set_webhook(full_webhook_url)

    logger.info(f"Bot berjalan dengan Webhook di URL: {full_webhook_url}")

if __name__ == "__main__":
    main()

