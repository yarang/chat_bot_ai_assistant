# 🗄️ SQLite 메시지 저장소 사용 가이드

## ✨ 새로운 기능들

### **1. 영구 대화 저장**
- ✅ 봇 재시작해도 대화 기록 유지
- ✅ 채팅방별 독립적 대화 관리
- ✅ 사용자별 맞춤 컨텍스트 제공

### **2. 강력한 검색 기능**
```
/search 파이썬
/search 머신러닝
/search "정확한 구문"
```

### **3. 상세 통계**
```
/stats  # 개인 및 채팅 통계
/info   # 전체 시스템 정보
```

### **4. 대화 내보내기**
```
/export  # 현재 채팅 대화 기록 다운로드
```

## 🚀 설치 및 실행

### **1. 기존 파일 백업 (선택사항)**
```bash
cp bot_messages.db bot_messages.db.backup
```

### **2. 새 파일들 추가**
- `message_storage.py` - SQLite 저장소
- 업데이트된 `gemini_client.py` 
- 업데이트된 `bot.py`

### **3. 봇 실행**
```bash
# Polling 방식 (권장)
uv run python main_polling.py

# 또는 Webhook 방식
uv run python main.py
```

## 📊 데이터베이스 구조

### **테이블들:**
- `users` - 사용자 정보
- `chats` - 채팅방 정보  
- `messages` - 모든 메시지 (사용자 + AI 응답)

### **인덱스:**
- 채팅별 시간순 조회 최적화
- 사용자별 조회 최적화
- 검색 성능 향상

## 🔧 관리 기능

### **1. 데이터베이스 크기 확인**
```python
# Python 코드에서
storage = MessageStorage()
stats = storage.get_database_stats()
print(f"DB 크기: {stats['db_size_mb']} MB")
```

### **2. 오래된 메시지 정리**
```python
# 30일 이전 메시지 삭제
deleted_count = storage.cleanup_old_messages(days_to_keep=30)
```

### **3. 대화 내보내기**
```python
# JSON 형태로 내보내기
json_data = storage.export_chat_history(chat_id, format='json')

# 텍스트 형태로 내보내기  
txt_data = storage.export_chat_history(chat_id, format='txt')
```

## 📈 성능 특징

### **장점:**
- 🚀 빠른 조회 (인덱스 최적화)
- 💾 효율적 저장 (SQLite 압축)
- 🔒 데이터 무결성 (ACID)
- 🔄 동시성 지원 (파일 잠금)

### **한계:**
- 👥 동시 사용자: ~1,000명
- 💬 일일 메시지: ~10,000개
- 💽 데이터베이스 크기: ~1GB 권장

## 🛠️ 트러블슈팅

### **문제 1: 데이터베이스 잠금**
```bash
# 해결: 봇 프로세스 확인 및 정리
ps aux | grep python
sudo pkill -f "python.*main"
```

### **문제 2: 저장소 오류**
```python
# Python에서 직접 확인
from message_storage import MessageStorage
storage = MessageStorage()
print("Storage initialized successfully")
```

### **문제 3: 디스크 공간 부족**
```python
# 오래된 데이터 정리
storage.cleanup_old_messages(days_to_keep=7)
```

## 📋 마이그레이션 체크리스트

- [ ] `message_storage.py` 파일 추가
- [ ] `gemini_client.py` 업데이트
- [ ] `bot.py` 업데이트  
- [ ] 봇 재시작
- [ ] `/info` 명령으로 통계 확인
- [ ] `/search` 명령 테스트
- [ ] `/export` 명령 테스트

## 🎯 사용 팁

### **효율적인 검색:**
```
/search 키워드        # 기본 검색
/search "정확한 문구"  # 구문 검색
```

### **정기적인 관리:**
- 월 1회 오래된 데이터 정리
- 주 1회 데이터베이스 백업
- 일 1회 통계 확인

### **백업 전략:**
```bash
# 매일 자동 백업 (cron)
0 2 * * * cp /path/to/bot_messages.db /backup/bot_messages_$(date +\%Y\%m\%d).db
```

이제 모든 대화가 안전하게 보관되고, 강력한 검색과 통계 기능을 사용할 수 있습니다! 🎉