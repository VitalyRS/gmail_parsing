#!/bin/bash

# Устанавливаем переменные окружения вручную
export PATH="/home/vitaly/anaconda3/bin:/snap/bin:/usr/bin:/bin:$PATH"

# Пути
PYTHON_BIN="/home/vitaly/anaconda3/envs/NLP_ENV/bin/python3"
JQ_BIN="/home/vitaly/anaconda3/bin/jq"
NGROK_BIN="/snap/bin/ngrok"
SCRIPT_PATH="/home/vitaly/PycharmProjects/Cron_Aut/read_corr_imap_Flask04.py"
ENV_FILE="/home/vitaly/PycharmProjects/Cron_Aut/read_email.env"
RUN_LOG="/home/vitaly/cron_ngrok_last_run.log"

# Проверка: запускался ли скрипт сегодня?
TODAY=$(date +%Y-%m-%d)

if [ -f "$RUN_LOG" ]; then
  LAST_RUN=$(cat "$RUN_LOG")
  if [ "$LAST_RUN" = "$TODAY" ]; then
    echo "🔁 Скрипт уже запускался сегодня: $LAST_RUN" >> /home/vitaly/cron_debug.log
    exit 0
  fi
fi

# Запись сегодняшней даты в лог
echo "$TODAY" > "$RUN_LOG"

# Убиваем старый ngrok (если есть)
pkill -f "$NGROK_BIN http" || true

# Запускаем ngrok на 5000 порту
nohup $NGROK_BIN http 5000 > /home/vitaly/ngrok.log 2>&1 &

# Ждём, пока API не станет доступно (макс 30 сек)
for i in $(seq 1 30); do
  if curl -s http://localhost:4040/api/tunnels | grep -q "public_url"; then
    break
  fi
  sleep 1
done

# Получаем HTTPS URL ngrok
TUNNELS_JSON=$(curl -s http://localhost:4040/api/tunnels)
WEBHOOK_BASE_URL=$(echo "$TUNNELS_JSON" | $JQ_BIN -r '.tunnels[] | select(.proto == "https") | .public_url' | head -n 1)

# Проверяем URL
if [[ -z "$WEBHOOK_BASE_URL" || "$WEBHOOK_BASE_URL" == "null" ]]; then
  echo "❌ Не удалось получить ngrok URL" >> /home/vitaly/cron_debug.log
  exit 1
fi

echo "✅ Ngrok URL: $WEBHOOK_BASE_URL" >> /home/vitaly/cron_debug.log

# Завершающий таймер на 1 минуту
(
  sleep 60
  echo "⏰ Завершаем процессы ngrok и python" >> /home/vitaly/cron_debug.log
  pkill -f "$NGROK_BIN http"
  pkill -f "$PYTHON_BIN $SCRIPT_PATH"
) &

# Запуск Python-скрипта с передачей переменных окружения
WEBHOOK_BASE_URL="$WEBHOOK_BASE_URL"  $PYTHON_BIN $SCRIPT_PATH >> /home/vitaly/cron_debug.log 2>&1

