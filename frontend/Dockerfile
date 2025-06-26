# === 빌더 스테이지 ===
FROM node:20-slim AS builder
WORKDIR /app

# 1. package.json과 lock 파일을 먼저 복사하고 의존성을 설치합니다.
#    이렇게 하면 package.json이 변경되지 않는 한 npm install 단계는 캐시됩니다.
COPY package*.json ./
RUN npm install

# 2. 모든 소스 코드를 복사합니다. (node_modules는 이미 설치되었으므로 덮어쓰지 않습니다)
#    .dockerignore 파일에 node_modules가 있다면 여기서 무시됩니다.
COPY . .

# 3. NEXT_PUBLIC_SUPABASE_REDIRECT_URL 환경 변수를 ARG/ENV에 추가합니다.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

ARG NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}

ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}

# 🔴🔴🔴 추가: 이 부분!
ARG NEXT_PUBLIC_SUPABASE_REDIRECT_URL
ENV NEXT_PUBLIC_SUPABASE_REDIRECT_URL=${NEXT_PUBLIC_SUPABASE_REDIRECT_URL}

ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}

# 빌드 명령 실행
RUN npm run build

# === 프로덕션 스테이지 ===
FROM node:20-slim
WORKDIR /app

# 빌더 스테이지에서 빌드된 애플리케이션 파일만 복사합니다.
# node_modules 포함 (Next.js 빌드 시 필요한 경우).
# .next 폴더, public 폴더 등 최종 빌드된 결과물이 복사됩니다.
COPY --from=builder /app .

# PATH 설정 (npm run start 실행에 필요할 수 있음)
ENV PATH="/app/node_modules/.bin:${PATH}"

# 애플리케이션 포트 노출
EXPOSE 3000

# 애플리케이션 시작 명령어
CMD ["npm", "start"]
