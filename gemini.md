# Gemini Client (gemini_client.py) 가이드

이 문서는 `gemini_client.py`의 `GeminiClient` 클래스에 대한 개발자 가이드입니다. 이 클래스는 Google Gemini API와의 모든 상호작용을 관리하며, 대화 기록을 데이터베이스에 영구적으로 저장하는 역할을 합니다.

## 1. 개요

`GeminiClient`는 다음과 같은 주요 기능을 수행합니다.

-   **Gemini API 연동**: Google의 생성형 AI 모델(Gemini)을 사용하여 사용자의 메시지에 대한 응답을 생성합니다.
-   **대화 컨텍스트 관리**: `MessageStorage`와 연동하여 이전 대화 내용을 가져와 문맥을 유지한 답변을 생성할 수 있습니다.
-   **메시지 및 토큰 사용량 저장**: 사용자와 봇의 모든 메시지, 그리고 각 API 호출에 대한 토큰 사용량을 SQLite 데이터베이스에 기록합니다.
-   **모델 설정 및 관리**: API 요청에 사용될 모델(`gemini-pro` 등), `temperature`, `max_tokens` 등의 파라미터를 동적으로 설정하고 관리합니다.
-   **통계 및 데이터 관리**: 사용자별, 채팅방별 통계 조회, 대화 내용 내보내기, 오래된 데이터 정리 등의 유틸리티 기능을 제공합니다.

## 2. 초기화

`GeminiClient`는 설정 객체(`config`)와 `MessageStorage` 인스턴스를 인자로 받아 초기화됩니다.

```python
from config_loader import get_gemini_config
from message_storage import MessageStorage
from gemini_client import GeminiClient

# 설정 및 스토리지 로드
gemini_config = get_gemini_config()
storage = MessageStorage("bot_messages.db")

# GeminiClient 인스턴스 생성
gemini_client = GeminiClient(config=gemini_config, storage=storage)
```

-   **`config`**: Gemini API 키, 모델 이름, 기본 생성 옵션(`temperature`, `top_p` 등)이 포함된 딕셔너리입니다.
-   **`storage`**: `MessageStorage` 객체입니다. 만약 제공되지 않으면 `GeminiClient`가 내부적으로 새로운 인스턴스를 생성합니다.

초기화 과정에서 클라이언트는 설정된 API 키를 사용하여 `genai.configure()`를 호출하고, 지정된 모델이 사용 가능한지 검증한 후 생성 모델을 초기화합니다.

## 3. 핵심 메서드

### `generate_response`

가장 중요한 메서드로, 사용자의 메시지를 받아 Gemini API를 호출하고 응답을 반환합니다.

```python
async def generate_response(
    self,
    chat_id: int,
    user_id: int,
    message: str,
    maintain_context: bool = True,
    context_length: int = 10,
) -> str:
```

**작동 순서:**

1.  **고유 상호작용 ID 생성**: 각 "질문-응답" 쌍을 식별하기 위해 `interaction_id`를 생성합니다.
2.  **사용자 메시지 저장**: 입력받은 메시지를 `Message` 객체로 만들어 `MessageStorage`를 통해 데이터베이스에 저장합니다. 이때 `interaction_id`도 함께 기록됩니다.
3.  **컨텍스트 로드 (`maintain_context=True`인 경우)**:
    -   `storage.get_conversation_history()`를 호출하여 해당 채팅방의 이전 대화 기록을 가져옵니다.
    -   가져온 기록을 "User: ..."와 "Assistant: ..." 형식의 프롬프트로 재구성합니다.
4.  **프롬프트 생성**: 컨텍스트가 포함된 프롬프트 또는 사용자의 메시지 자체를 최종 프롬프트로 결정합니다.
5.  **Gemini API 호출**: `self.model.generate_content()`를 사용하여 응답 생성을 요청합니다.
6.  **토큰 사용량 기록**: API 응답에 포함된 `usage_metadata`를 분석하여 `prompt_token_count`(입력)와 `candidates_token_count`(출력)를 가져옵니다.
7.  **AI 응답 저장**: 생성된 응답 텍스트를 `Message` 객체로 만들어 데이터베이스에 저장합니다. 이때도 동일한 `interaction_id`가 사용됩니다.
8.  **토큰 사용량 저장**: 입력 및 출력 토큰 사용량을 `storage.save_token_usage()`를 통해 별도의 `token_usage` 테이블에 기록합니다. 이 기록은 `interaction_id`와 연결되어 어떤 대화에서 토큰이 사용되었는지 추적할 수 있게 합니다.
9.  **응답 반환**: 최종 응답 텍스트를 반환합니다.

## 4. 대화 및 데이터 관리

`GeminiClient`는 `MessageStorage`의 기능을 활용하여 다양한 데이터 관리 메서드를 제공합니다.

-   **`clear_conversation(chat_id, user_id)`**: 특정 사용자의 대화 기록을 모두 삭제합니다.
-   **`get_conversation_length(chat_id, user_id)`**: 대화 기록의 길이를 반환합니다.
-   **`get_chat_statistics(chat_id)`**: 특정 채팅방의 통계(총 메시지 수, 사용자 수 등)를 반환합니다.
-   **`get_user_statistics(user_id)`**: 특정 사용자의 통계(메시지 수, 토큰 사용량 등)를 반환합니다.
-   **`search_messages(query, ...)`**: 메시지 내용에서 특정 키워드를 검색합니다.
-   **`export_conversation(chat_id, format)`**: 대화 기록을 `json` 또는 `txt` 형식으로 내보냅니다.
-   **`cleanup_old_data(days_to_keep)`**: 지정된 기간보다 오래된 메시지를 삭제하여 데이터베이스를 정리합니다.

## 5. 모델 설정 변경

봇이 실행 중인 상태에서도 다음 메서드를 통해 Gemini 모델의 파라미터를 동적으로 변경할 수 있습니다.

-   **`set_model_parameters(...)`**: `temperature`, `max_tokens`, `top_p`, `top_k` 값을 변경합니다. 이 메서드가 호출되면 새로운 설정으로 모델이 다시 초기화됩니다.
-   **`get_model_info()`**: 현재 적용된 모델의 설정과 데이터베이스 통계 정보를 함께 반환합니다.

## 6. 데이터베이스 상호작용

`GeminiClient`는 모든 데이터 영속성을 `MessageStorage`에 위임합니다. 주요 상호작용은 다음과 같습니다.

-   **`storage.save_message()`**: 사용자와 AI의 메시지를 `messages` 테이블에 저장합니다.
-   **`storage.save_token_usage()`**: API 호출 시 발생한 토큰 사용량을 `token_usage` 테이블에 저장합니다.
-   **`storage.get_conversation_history()`**: `messages` 테이블에서 대화 기록을 조회하여 컨텍스트를 구성합니다.
-   **`storage.clear_conversation()`**: `messages` 테이블에서 특정 대화 기록을 삭제합니다.

이러한 구조 덕분에 `GeminiClient`는 API 로직에 집중하고, 데이터 저장 및 관리는 `MessageStorage`가 전담하여 역할과 책임이 명확하게 분리됩니다.
