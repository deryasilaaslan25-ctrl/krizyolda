FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# NRC EmoLex lisansı gereği imaja gömülmez; çalışma zamanında indirilir ya da birim olarak bağlanır.
CMD ["sh", "-c", "[ -f data/nrc/Turkish-NRC-EmoLex.txt ] || python scripts/indir_nrc.py || true; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
