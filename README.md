# Telegram Gemini Bot

Google Gemini AI를 사용하는 Telegram 챗봇입니다. FastAPI와 uv 개발 환경을 사용하여 구축되었습니다.

## 🚀 기능

- ✅ Google Gemini AI 통합
- ✅ Telegram Webhook 지원
- ✅ 대화 맥락 유지
- ✅ FastAPI 기반 웹 서버
- ✅ JSON 설정 파일
- ✅ 환경 변수 지원
- ✅ 로깅 시스템
- ✅ 에러 핸들링

## 📋 요구사항

- Python 3.8+
- uv (Python 패키지 매니저)
- Telegram Bot Token
- Google Gemini API Key

## 🛠️ 설치

### 1. 저장소 클론

```bash
git clone <repository-url>
cd telegram-gemini-bot
```

### 2. uv 설치 (아직 설치하지 않은 경우)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 프로젝트 의존성 설치

```bash
uv sync
```

### 4. 설정 파일 구성

`config.json` 파일을 편집하여 토큰과 API 키를 설정하세요:

```json
{
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE",
    "webhook_url": "https://your-domain.com/webhook",
    "webhook_path": "/webhook",
    "port": 8000,
    "host": "0.0.0.0"
  },
  "gemini": {
    "api_key": "YOUR_GEMINI_API_KEY_HERE",
    "model_name": "gemini-1.5-flash",
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.8,
    "top_k": 40
  }
}
```

## 🔑 API 키 및 토큰 획득

### Telegram Bot Token

1. Telegram에서 [@BotFather](https://t.me/botfather)에게 메시지 보내기
2. `/newbot` 명령어 사용
3. 봇 이름과 사용자명 설정
4. 받은 토큰을 `config.json`에 입력

### Google Gemini API Key

1. [Google AI Studio](https://makersuite.google.com/app/apikey) 방문
2. 새 API 키 생성
3. 받은 키를 `config.json`에 입력

## 🚀 실행

### 개발 환경

```bash
uv run python main.py
```

### 프로덕션 환경

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker 사용 (선택사항)

```bash
# Dockerfile 생성 후
docker build -t telegram-gemini-bot .
docker run -p 8000:8000 telegram-gemini-bot
```

## 🌐 Webhook 설정

봇을 프로덕션에서 사용하려면 HTTPS 도메인이 필요합니다:

1. 도메인 구입 및 SSL 인증서 설정
2. `config.json`에서 `webhook_url` 업데이트
3. 봇 실행 시 자동으로 webhook 설정됨

## 📝 환경 변수 사용

설정을 환경 변수로도 지정할 수 있습니다:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export GEMINI_API_KEY="your_gemini_api_key"
export TELEGRAM_WEBHOOK_URL="https://your-domain.com/webhook"
export PORT=8000
export DEBUG=false
export LOG_LEVEL=INFO
```

## 🎯 사용법

### 봇 명령어

- `/start` - 봇 시작 및 환영 메시지
- `/help` - 도움말 보기
- `/clear` - 대화 기록 초기화
- `/info` - 봇 및 AI 모델 정보
- `/settings` - 현재 설정 보기

### AI 채팅

- 봇에게 아무 메시지나 보내면 Gemini AI가 응답합니다
- 대화 맥락이 자동으로 유지됩니다
- 긴 대화 후에는 `/clear`로 초기화하는 것을 권장합니다

## 📁 프로젝트 구조

```
telegram-gemini-bot/
├── main.py              # FastAPI 메인 애플리케이션
├── bot.py               # Telegram 봇 핸들러
├── gemini_client.py     # Gemini API 클라이언트
├── config_loader.py     # 설정 로더
├── config.json          # 설정 파일
├── pyproject.toml       # uv 프로젝트 설정
└── README.md           # 이 파일
```

## 🔧 개발

### 코드 스타일

```bash
# 코드 포맷팅
uv run black .

# Import 정렬
uv run isort .

# 린트 체크
uv run flake8 .
```

### 테스트

```bash
uv run pytest
```

## 🐛 문제 해결

### 일반적인 문제

1. **봇이 응답하지 않음**
   - Telegram Bot Token 확인
   - Webhook URL이 HTTPS인지 확인
   - 로그 확인

2. **Gemini API 오류**
   - API 키 확인
   - API 할당량 확인
   - 모델명 확인

3. **Webhook 오류**
   - SSL 인증서 확인
   - 도메인이 접근 가능한지 확인
   - 포트 방화벽 설정 확인

### 로그 확인

애플리케이션 로그를 확인하여 문제를 진단하세요:

```bash
# 개발 환경에서 자세한 로그 보기
LOG_LEVEL=DEBUG uv run python main.py
```

## 📄 라이선스

MIT License

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 지원

문제가 있거나 도움이 필요하시면 이슈를 생성해주세요.