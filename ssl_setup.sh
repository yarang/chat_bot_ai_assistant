#!/bin/bash

# SSL 인증서 설정 스크립트 (Let's Encrypt 사용)

set -e

DOMAIN="oci-fcoinfup-arm2.fcoinfup.com"
EMAIL="your-email@example.com"  # 실제 이메일로 변경하세요

echo "🔐 Setting up SSL certificate for $DOMAIN"

# Certbot 설치 (Ubuntu)
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing Certbot..."
    sudo apt update
    sudo apt install -y snapd
    sudo snap install core; sudo snap refresh core
    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot
fi

# 기존 봇 프로세스 중지
echo "⏹️ Stopping existing bot process..."
sudo pkill -f "python.*main.py" || true

# Nginx 설치 및 설정
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing Nginx..."
    sudo apt install -y nginx
fi

# Nginx 설정 파일 생성
sudo tee /etc/nginx/sites-available/telegram-bot > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 사이트 활성화
sudo ln -sf /etc/nginx/sites-available/telegram-bot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
sudo nginx -t

# Nginx 시작
sudo systemctl start nginx
sudo systemctl enable nginx

# SSL 인증서 발급
echo "🔐 Obtaining SSL certificate..."
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL

# Nginx 재시작
sudo systemctl reload nginx

echo "✅ SSL certificate setup complete!"
echo "🔗 Your bot will be available at: https://$DOMAIN"

# 봇 다시 시작 안내
echo ""
echo "🤖 Now restart your bot:"
echo "cd /path/to/your/bot && nohup uv run python main.py > bot.log 2>&1 &"
