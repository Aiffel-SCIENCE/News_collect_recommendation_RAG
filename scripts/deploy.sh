#!/bin/bash

echo "🚀 Aigen_science 서버 배포 스크립트 시작..."

# 1. 필수 패키지 설치
echo "📦 필수 패키지 설치 중..."
sudo apt update
sudo apt install -y git docker.io docker-compose

# 2. GitHub에서 코드 클론 (주석 처리됨 - 현재 디렉토리 코드를 사용)
# echo "📁 코드 클론 중..."
# git clone https://github.com/Real-Aiffelthon/Aigen_science.git
# cd Aigen_science
# git checkout MVP

# 3. config 파일 확인
if [ ! -f config/config.yaml ]; then
  echo "⚠️  [주의] config/config.yaml 파일이 없습니다!"
  echo "➡️  템플릿 파일(config.yaml.template)을 참고하여 직접 작성하세요."
  exit 1
fi

# 4. Docker Compose 실행
echo "🐳 Docker Compose 실행 중..."
docker-compose up --build -d

echo "✅ 배포 완료! 컨테이너 상태 확인은 'docker ps' 명령으로 확인하세요."
