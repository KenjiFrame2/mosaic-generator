# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем зависимости для Tkinter и Pillow
RUN apt-get update && apt-get install -y \
    python3-tk \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# По умолчанию запускаем GUI
CMD ["python", "main_gui.py"]
