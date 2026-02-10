FROM python:3.12-slim

WORKDIR /app

# CA証明書（必要な場合のみ）
COPY certs/custom_cacerts.pem /usr/local/share/ca-certificates/custom_cacerts.crt
RUN update-ca-certificates

ENV SSL_CERT_FILE=/usr/local/share/ca-certificates/custom_cacerts.crt
ENV REQUESTS_CA_BUNDLE=/usr/local/share/ca-certificates/custom_cacerts.crt

# 依存関係
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# アプリ本体
COPY . /app

# ログが即時出るようにする
ENV PYTHONUNBUFFERED=1

CMD ["python", "slack_bot.py"]
