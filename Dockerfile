FROM python:3.10-slim
RUN apt-get update && apt-get install -y tesseract-ocr && apt-get clean
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "telegram_ocr_bot.py"]
