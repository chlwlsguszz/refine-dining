# Refine Dining

공공데이터 식품 영양 정보를 수집/정제하여 검색하고, 조리 방법별 영양소를 비교할 수 있는 웹 서비스입니다.

- Backend: Spring Boot, JPA, MySQL
- Frontend: React + Vite
- Infra: Docker, Nginx, Docker Compose
- AI: Gemini API 기반 조리 후 예상 중량 추천

## 주요 기능

- 식품명 검색 및 페이지네이션
- 대표 식품(원재료)과 조리 방법별 식품 영양소 비교
- 조리 후 예상 중량 AI 추천
- 관리자 배치 API
  - 공공데이터 원본 동기화
  - 정제 데이터 생성/계층화

## 시스템 구조

1. `sync-raw`로 공공데이터 API 원본을 `raw_food_materials`에 저장
2. `refine`로 서비스용 정제 데이터(`food_materials`) 생성
3. 검색 API가 정제 데이터를 조회
4. 비교 화면에서 AI 예측 API 호출 시 Gemini 기반 예상 중량 반환

## 프로젝트 구조

```text
refine-dining
├─ backend/   # Spring Boot API 서버
├─ frontend/  # React(Vite) 클라이언트
├─ docker-compose.yml
└─ README.md
```

## 로컬 실행 (개발 모드)

### 1) Backend

`backend/src/main/resources/application-local.yml` 또는 환경변수에 다음 값을 준비합니다.

- `DB_PASSWORD`
- `PUBLIC_DATA_API_KEY`
- `GEMINI_API_KEY`

실행:

```bash
cd backend
./gradlew bootRun
```

### 2) Frontend

```bash
cd frontend
npm ci
npm run dev
```

브라우저: `http://localhost:5173`

## Docker Compose 실행 (로컬 배포)

루트에 `.env` 파일을 생성합니다.

```env
SPRING_PROFILES_ACTIVE=local
DB_NAME=refine_dining
DB_USERNAME=refine_user
DB_PASSWORD=change_me
MYSQL_ROOT_PASSWORD=change_me_root
PUBLIC_DATA_API_KEY=your_public_data_api_key
GEMINI_API_KEY=your_gemini_api_key
```

실행:

```bash
docker compose up -d --build
```

접속:

- App: `http://localhost`

중지:

```bash
docker compose down
```

볼륨까지 초기화:

```bash
docker compose down -v
```

## API 예시

### 식품 검색

```http
GET /api/food/search?name=감자&page=0&size=10
```

### AI 중량 예측

```http
POST /api/weight/predict
Content-Type: application/json

{
  "foodName": "삼겹살",
  "cookingMethod": "구운것",
  "baseWeight": 100
}
```

### 관리자 배치

```http
POST /api/admin/food-data/sync-raw
POST /api/admin/food-data/refine
```

## 트러블슈팅 메모

- 공공데이터 API는 HTTP 요청 시 301 리다이렉트(HTML)를 반환할 수 있어 `public-data.base-url`을 HTTPS로 사용합니다.
- 외부 API 응답이 비정상(HTML 등)일 때를 대비해 PublicDataClient에서 문자열 응답 검증 및 예외 로그를 남깁니다.

## 보안 주의사항

- API 키/비밀번호는 절대 Git에 커밋하지 마세요.
- `.env`, `application-local.yml` 등 로컬 비밀 설정은 버전 관리에서 제외하세요.