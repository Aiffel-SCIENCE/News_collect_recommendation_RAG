# Dockerfile
FROM python:3.12-slim

# 시스템 패키지 업데이트 및 필요한 패키지 설치
# 각 패키지 뒤에 `\` (역슬래시)가 꼭 있어야 합니다!
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    libgomp1 \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/* # 이 줄은 `\` 없이 바로 이어져야 합니다.

# 작업 디렉토리 설정
WORKDIR /app

# Python 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# pip 업그레이드 및 requirements.txt 복사
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . /app

# 포트 노출 (FastAPI용)
EXPOSE 8000

# 기본 명령어 (테스트 실행)
CMD ["python", "tests/main_test.py"]
# 기본 명령어 (FastAPI 서버 실행)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
