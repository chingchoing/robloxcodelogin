#!/usr/bin/env python3
"""
Telegram OCR Bot — Updated for group and private chats
Features:
- OCR (Tesseract) on photos or image files
- Works in groups and DMs
- Optional: only reply when mentioned in group
"""

import os
import logging
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8262121748:AAH_tqT0xvv0yOUY1O4hGuiU8Cvt6_MVNME")
TESSERACT_LANG = os.environ.get("TESSERACT_LANG", "eng")

# If you're on Windows and Tesseract isn't in PATH, uncomment and set path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# Only respond to mentions in group chats (True/False)
REPLY_ONLY_WHEN_MENTIONED = False
# ----------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def preprocess_image_for_ocr(pil_img: Image.Image) -> Image.Image:
    """Basic image cleanup for better OCR accuracy."""
    img = pil_img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.SHARPEN)

    # Optional resize if small
    if max(img.size) < 1000:
        scale = min(1600 / max(img.size), 2.0)
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.BILINEAR)
    return img


def perform_ocr(pil_img: Image.Image, lang: str = TESSERACT_LANG) -> str:
    """Run OCR with Tesseract."""
    try:
        img = preprocess_image_for_ocr(pil_img)
        text = pytesseract.image_to_string(img, lang=lang, config="--oem 3 --psm 3")
        return text.strip()
    except Exception:
        logger.exception("OCR failed")
        return ""


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Hi! Send me a photo or an image file and I'll extract any text using OCR.\n"
        "You can also add me to a group — I’ll reply to images there too!"
    )


def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("📸 Just send an image with text — I'll extract it for you!")


def handle_image(update: Update, context: CallbackContext):
    message = update.message

    # --- Optional mention filter for groups ---
    if message.chat.type in ["group", "supergroup"] and REPLY_ONLY_WHEN_MENTIONED:
        if not message.caption or f"@{context.bot.username}" not in message.caption:
            return  # Ignore unless bot is mentioned

    try:
        # Determine image source
        if message.photo:
            file = message.photo[-1].get_file()
        elif message.document and message.document.mime_type.startswith("image/"):
            file = message.document.get_file()
        else:
            message.reply_text("Please send a valid image file.")
            return

        # Download and open image
        bio = BytesIO()
        file.download(out=bio)
        bio.seek(0)
        pil_img = Image.open(bio).convert("RGB")

        # Notify user
        processing_msg = message.reply_text("🕓 Extracting text...")

        # Run OCR
        text = perform_ocr(pil_img)

        # Respond with result
        if text:
            if len(text) > 4000:
                bio_out = BytesIO()
                bio_out.name = "ocr_result.txt"
                bio_out.write(text.encode("utf-8"))
                bio_out.seek(0)
                message.reply_document(
                    document=bio_out,
                    filename="ocr_result.txt",
                    caption="📄 Extracted text attached.",
                )
            else:
                message.reply_text(f"📝 *Extracted text:*\n\n{text}", parse_mode="Markdown")
        else:
            message.reply_text("😕 No readable text found in that image.")

        processing_msg.delete()

    except Exception as e:
        logger.exception("Error handling image")
        message.reply_text("❌ Error processing image. Check the logs for details.")


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))

    # Handle photos & image documents from private or group chats
    image_filter = Filters.photo | (Filters.document & Filters.document.mime_type("image/"))
    dp.add_handler(MessageHandler(image_filter & (Filters.chat_type.private | Filters.chat_type.groups), handle_image))

    logger.info("🤖 Bot started and ready.")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
