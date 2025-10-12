#!/usr/bin/env python3
import os
import logging
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TESSERACT_LANG = os.environ.get("TESSERACT_LANG", "eng")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def preprocess_image_for_ocr(pil_img: Image.Image) -> Image.Image:
    img = pil_img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.SHARPEN)
    if max(img.size) < 1000:
        scale = min(1600 / max(img.size), 2.0)
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.BILINEAR)
    return img

def perform_ocr(pil_img: Image.Image, lang: str = TESSERACT_LANG) -> str:
    try:
        img = preprocess_image_for_ocr(pil_img)
        text = pytesseract.image_to_string(img, lang=lang, config='--oem 3 --psm 3')
        return text.strip()
    except Exception as e:
        logger.exception("OCR failed")
        return ""

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hi — send me a photo and I'll extract text from it using OCR!")

def handle_photo(update: Update, context: CallbackContext):
    message = update.message
    try:
        if message.photo:
            photo = message.photo[-1]
            file = photo.get_file()
        elif message.document and message.document.mime_type.startswith("image/"):
            file = message.document.get_file()
        else:
            message.reply_text("Please send an image (photo or image file).")
            return

        bio = BytesIO()
        file.download(out=bio)
        bio.seek(0)
        pil_img = Image.open(bio).convert("RGB")

        msg = message.reply_text("Processing image for OCR...")
        text = perform_ocr(pil_img)

        if text:
            if len(text) > 4000:
                bio_out = BytesIO()
                bio_out.name = "ocr_result.txt"
                bio_out.write(text.encode("utf-8"))
                bio_out.seek(0)
                message.reply_document(document=bio_out, filename="ocr_result.txt", caption="Extracted text.")
            else:
                message.reply_text(f"Extracted text:\n\n{text}")
        else:
            message.reply_text("No readable text found in the image. Try a clearer photo.")

        msg.delete()
    except Exception as e:
        logger.exception("Error handling image")
        message.reply_text("Error processing image.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.photo | (Filters.document & Filters.document.mime_type("image/")), handle_photo))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
