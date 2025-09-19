# 1️⃣ Base image
FROM python:3.11-slim

# Sistem paketlar: build-essential, libpq-dev va netcat-openbsd
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3️⃣ App ishchi katalog
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5️⃣ Black formatter install
RUN pip install --no-cache-dir black

# 6️⃣ Loyhani konteynerga copy qilish
COPY . .

# 7️⃣ Runner script entrypoint
ENTRYPOINT ["sh", "runner.sh"]

# 8️⃣ Default command (agar runner.sh ishlatilmasa)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]