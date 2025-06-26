# AIGEN Science 간단한 알림 시스템 가이드

## 개요

이 시스템은 `news_recommendation.py`의 기존 함수들을 활용하여 사용자들에게 정기적으로 개인화된 뉴스 추천을 Slack과 이메일로 전송하는 시스템입니다.

## 주요 특징

- **기존 코드 재활용**: `news_recommendation.py`의 `extract_profile_keywords` 함수 활용
- **간단한 구조**: 하나의 파일로 모든 기능 구현
- **Docker 불필요**: 로컬에서 직접 실행 가능
- **실제 서버 연동**: `http://34.61.170.171:8001/recommendations` API 사용

## 핵심 함수

### 1. 프로필 키워드 추출
```python
from src.app.news_recommendation import extract_profile_keywords

# 프로필 컨텍스트에서 키워드 추출
keywords = extract_profile_keywords("바이오 제약 배고픔 빵 과자 세포")
# 결과: ['바이오', '제약', '세포'] (예시)
```

### 2. 개인화된 쿼리 생성
```python
def generate_personalized_query(profile_context: str) -> str:
    keywords = extract_profile_keywords(profile_context)
    if keywords:
        query = f"{' '.join(keywords)} 뉴스"
        return query
    return "최신 과학 뉴스"
```

### 3. RAG 추천 생성
```python
def RAG(profile_context: str, notification_query: str = None):
    # 사용자 설정 쿼리 우선, 없으면 프로필 기반 자동 생성
    if notification_query and notification_query.strip():
        query = notification_query
    elif profile_context:
        query = generate_personalized_query(profile_context)
    else:
        query = "최신 과학 뉴스"
    
    # API 호출하여 뉴스 추천 받기
    # ...
```

## 필요한 것들

### 1. 의존성 설치
```bash
pip install schedule sib-api-v3-sdk supabase requests python-dotenv
```

### 2. 환경 설정
- `.env` 파일에 필요한 환경 변수 설정
- Supabase 연결 정보 확인
- Brevo API 키 설정

### 3. 뉴스 추천 API 실행
알림 시스템이 작동하려면 뉴스 추천 API가 실행 중이어야 합니다:
```bash
# 뉴스 추천 API 실행 (포트 8001)
python src/app/news_recommendation.py
```

## 사용법

### 1. 알림 시스템 실행
```bash
python simple_notification_system.py
```

### 2. 테스트
```bash
python test_simple_notification.py
```

## 작동 방식

1. **매시간 정각**에 시스템이 실행됩니다
2. **Supabase**에서 모든 사용자 정보를 가져옵니다
3. **현재 시간**과 **알림 시간**이 일치하는 사용자를 찾습니다
4. **쿼리 우선순위**:
   - 사용자가 설정한 `notification_query` (우선)
   - `extract_profile_keywords` 함수로 프로필에서 키워드 추출
   - 기본 쿼리 "최신 과학 뉴스"
5. **뉴스 추천 API**를 호출하여 개인화된 뉴스를 받습니다
6. **Slack**과 **이메일**로 알림을 전송합니다

## 알림 메시지 예시

### 프로필: "바이오 제약 배고픔 빵 과자 세포"
```
[사용자명] 📰 새로운 바이오 제약 기술 개발: 혁신적인 세포 치료제가 임상시험을 통과했습니다...
📰 제약 산업 투자 동향: 바이오테크 스타트업들이 활발한 투자를 받고 있습니다...
📰 세포 치료 연구 성과: 암 치료를 위한 새로운 세포 치료법이 개발되었습니다...
```

### 프로필: "AI 연구원"
```
[사용자명] 📰 GPT-5 개발 진행상황: OpenAI의 차세대 언어모델 개발이 순조롭게 진행되고 있습니다...
📰 머신러닝 알고리즘 혁신: 새로운 딥러닝 아키텍처가 성능을 크게 향상시켰습니다...
📰 AI 윤리 가이드라인: 인공지능 개발에 대한 새로운 윤리 기준이 제정되었습니다...
```

## 설정 방법

### 1. 사용자 프로필 설정
프론트엔드에서 다음 정보를 설정:
- **프로필 컨텍스트**: "무엇에 관심이 있으신가요?" (자동 쿼리 생성용)
- **슬랙 WebHook URL**: Slack 알림을 받을 웹훅 URL
- **이메일**: 이메일 알림을 받을 주소
- **알림 시간**: 매시간 중 언제 알림을 받을지 (HH:MM 형식)
- **알림 쿼리**: 직접 설정하고 싶은 쿼리 (선택사항)

### 2. 데이터베이스 설정
```sql
-- notification_query 필드 추가 (선택사항)
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS notification_query TEXT DEFAULT '최신 과학 뉴스';
```

## 문제 해결

### 1. 뉴스 추천 API 연결 실패
- 뉴스 추천 API가 포트 8001에서 실행 중인지 확인
- `http://34.61.170.171:8001/recommendations` 접근 가능한지 확인

### 2. 키워드 추출 실패
- OpenAI API 키가 올바르게 설정되었는지 확인
- 프로필 컨텍스트가 비어있지 않은지 확인

### 3. 알림이 전송되지 않음
- 사용자의 알림 시간 설정 확인
- Slack WebHook URL과 이메일 주소가 올바른지 확인
- Brevo API 키가 유효한지 확인

### 4. 로그 확인
```bash
# 실시간 로그 확인
tail -f notification_system.log
```

## 테스트 옵션

```bash
python test_simple_notification.py
```

1. **프로필 키워드 추출 테스트**: `extract_profile_keywords` 함수 테스트
2. **API 연결 테스트**: 뉴스 추천 API 연결 확인
3. **RAG 함수 테스트**: 전체 추천 로직 테스트
4. **사용자 정보 조회 테스트**: Supabase 연결 확인
5. **현재 시간 알림 대상 확인**: 알림 대상 사용자 확인
6. **전체 시스템 테스트**: 실제 전송 없이 전체 로직 테스트

## 장점

1. **코드 재사용**: 기존 `news_recommendation.py` 함수 활용
2. **간단한 구조**: 하나의 파일로 모든 기능 구현
3. **Docker 불필요**: 로컬에서 직접 실행 가능
4. **개인화**: 사용자 프로필 기반 자동 쿼리 생성
5. **유연성**: 수동 쿼리 설정도 지원

## 주의사항

1. **API 키 보안**: Brevo API 키가 코드에 하드코딩되어 있으므로 환경 변수로 관리하는 것을 권장
2. **네트워크 연결**: 뉴스 추천 API와의 연결이 실패해도 기본 메시지로 대체
3. **시간대**: 시스템은 서버의 로컬 시간을 기준으로 작동
4. **의존성**: `news_recommendation.py`가 정상적으로 실행되어야 함

## 확장 가능성

- 더 많은 알림 채널 추가 (Discord, Telegram 등)
- 알림 빈도 조정 (매일, 매주 등)
- 알림 내용 커스터마이징
- 알림 전송 성공/실패 통계
- 더 정교한 NLP 기반 쿼리 생성 