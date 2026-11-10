# Refine Dining

## 원문을 확인하는 로컬 영양 RAG

[프로젝트 포트폴리오 · 같은 옥수수인데 왜 비교를 보류했을까?](docs/portfolio/README.md)

‘옥수수_강다옥_말린것 100g 단백질 비교’라고 물으면, 말린 강다옥의 단백질 9.82g과 식품코드를 보여줍니다. 가장 가까운 생것 후보는 다른 품종인 고당옥이라 두 식품의 차이는 보류합니다. 검수자가 승인한 쌍은 양쪽 원문과 차이를 함께 표시합니다. 영상의 승인 사례는 격리된 시연 DB에서 검증했고, 새 DB는 승인 0건으로 시작합니다. [3분 영상](datasets/week1/2026-11-10/release/nutrition-demo.mp4) · [최종 평가 32건](datasets/week1/2026-11-10/release/README.md) · [질문별 검증 결과](datasets/week1/2026-11-10/release/answer-checks.json)

- **검색**. 동결 원본 3,701행에서 생것 2,388개를 E5로 벡터화합니다. 같은 대표식품에서 최대 3개를 확보하고 전체 검색으로 보완해 5개를 제시합니다. 개발 77건 중 같은 대표식품이 검색된 경우가 71건에서 77건으로 늘었고, 이름이 명확한 455쌍은 모두 상위 5개에 남았습니다. [네 가지 검색 방식과 개별 순위](datasets/week1/2026-11-10/retrieval-policy/comparison.json)
- **근거와 판정**. 가공 상태에 맞는 공식 문단을 별도로 검색합니다. 로컬 Qwen3-8B가 후보 코드·판정·인용을 생성하고, 서버에 넘기기 전에 후보 범위·원문·단위·부위 충돌을 검증합니다. 개발 자료에서 원문 기준으로 제안한 참고 후보는 1건, 가공 정의를 더하면 3건입니다. 같은 자료를 받은 Qwen은 77건을 모두 보류했습니다. 서비스의 검수 목록은 확인 가능한 3건의 참고 제안과 74건의 보류를 담습니다. [개발 결과](datasets/week1/2026-11-10/local-rag/development.json) · [74건별 부족한 근거](datasets/week1/2026-11-10/evidence/hold-audit.json) · [로컬 추론 측정](datasets/week1/2026-11-10/local-rag/runtime-measurement.json)
- **계산과 공개**. 공공데이터포털 공개 다운로드 3,704행과 동결 DB의 식품코드·출처·관측 조건을 대조했습니다. 24개 영양 항목 88,824칸 가운데 원문 수치 63,125칸(그중 실제 0은 11,048칸), 결측 25,699칸을 구별합니다. MySQL 또는 로컬 H2에 버전별 원문·제안·검수 사유를 보관합니다. 수치와 차이는 서버가 계산하고, 자유형 설명에서 로컬 모델은 승인 근거 중 제시할 문장을 선택합니다. [공공데이터 원자료](https://www.data.go.kr/data/15100065/standard.do) · [보관한 다운로드 원본](datasets/week1/2026-11-10/nutrition/official-materials.json.gz)
- **평가 범위**. 14개 식품군 32건의 최종 평가 결과는 직접 0·참고 0·보류 32건입니다. 독립 검수 정답이 없어 최종 정확도·회수율·오연결률은 산출할 수 없습니다. 455쌍은 이름이 명확한 사례의 검색 회귀에 사용합니다. [동결 설정](datasets/week1/2026-11-10/release/freeze.json) · [식품별 후보와 응답](datasets/week1/2026-11-10/release/report.json)

새 체크아웃에서 인덱스를 다시 만들고 77건을 생성했을 때 검색 순위·선택 코드·판정·인용은 일치했습니다. GPU에서 다시 생성한 응답 5건은 설명에 표시할 차이 항목이 달랐습니다. 캐시를 사용한 재실행에서는 77건의 응답이 일치했습니다. [새 체크아웃 재현 기록](datasets/week1/2026-11-10/release/reproduction.json)

### 로컬에서 데모 열기

저장소 루트의 PowerShell에서 실행합니다. Python 3.12, JDK 17, Node 24를 사용했습니다. 저장된 스냅샷과 개발 제안으로 H2 데모를 실행할 수 있습니다. 첫 설치 때 Gradle과 npm 의존성을 준비합니다.

```powershell
py -3.12 backend/tools/rag_match/prepare_rag_catalog.py
Push-Location frontend
npm ci
npm run build -- --mode rag-demo
Pop-Location
Push-Location backend
.\gradlew.bat bootJar
# 검수 화면을 사용할 때만 현재 터미널의 ADMIN_API_KEY를 개인 키로 설정합니다.
java -jar build/libs/backend-0.0.1-SNAPSHOT.jar --spring.profiles.active=rag-demo
```

사용자 화면에서는 식품·중량을 입력하고, 답변 아래 식품명을 눌러 원천 표기와 단위를 확인합니다. 관리자 화면에서는 `X-Admin-Key`에 대응하는 키로 원문 두 건과 공식 문단을 확인한 뒤 승인 또는 보류합니다. 자료·근거 버전이 바뀌면 기존 승인과 구분됩니다. [질의응답](http://127.0.0.1:18082/nutrition) · [관리자 검수](http://127.0.0.1:18082/nutrition/review)

기존 MySQL 서비스에는 먼저 위의 카탈로그를 생성하고 `.env`의 `ADMIN_API_KEY`를 설정한 뒤 `docker compose -f docker-compose.yml -f docker-compose.rag.yml up -d --build`로 연결합니다.

<details><summary>식품 벡터·근거 검색·로컬 모델 재현</summary>

저장소 루트에서 다음 순서로 실행합니다. 가중치 다운로드 후 추론은 로컬에서 실행합니다. [E5 고정 버전](https://huggingface.co/Xenova/multilingual-e5-small/tree/761b726dd34fb83930e26aab4e9ac3899aa1fa78) · [Qwen 고정 버전](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/7c41481f57cb95916b40956ab2f0b139b296d974) · [사용한 llama.cpp b11206](https://github.com/ggml-org/llama.cpp/releases/tag/b11206)

```powershell
$data = 'datasets/week1/2026-11-10'
$tools = 'backend/tools/rag_match'
$rev = '761b726dd34fb83930e26aab4e9ac3899aa1fa78'
$model = "backend/build/models/multilingual-e5-small/$rev"
$remote = "https://huggingface.co/Xenova/multilingual-e5-small/resolve/$rev"
New-Item -ItemType Directory -Force "$model/onnx" | Out-Null
curl.exe -fL "$remote/tokenizer.json" -o "$model/tokenizer.json"
curl.exe -fL "$remote/onnx/model_quantized.onnx" -o "$model/onnx/model_quantized.onnx"
py -3.12 -m venv backend/build/e5-env
$py = 'backend/build/e5-env/Scripts/python.exe'
& $py -m pip install numpy==2.5.3 tokenizers==0.23.2 onnxruntime==1.30.0
& $py "$tools/embed_food_names.py" --snapshot "$data/raw-snapshot.json" --baseline "$data/name-benchmark.json" --model-dir $model --revision $rev --threads 6 --output backend/build/e5-small-vectors.npz
& $py "$tools/retrieval_policy.py" compare --output-dir backend/build/retrieval-comparison
& $py "$tools/retrieval_policy.py" infer --partition dev --output backend/build/dev-ranks.json
```

별도 터미널에서 고정된 GGUF와 llama.cpp를 준비합니다. 아래 명령은 `llama-server` 실행 파일이 PATH에 있는 환경에서 로컬 GPU를 사용합니다. 모델은 약 5.85GB입니다.

```powershell
$rev = '7c41481f57cb95916b40956ab2f0b139b296d974'
$gguf = 'backend/build/models/Qwen3-8B-Q5_K_M.gguf'
curl.exe -fL "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/$rev/Qwen3-8B-Q5_K_M.gguf" -o $gguf
if ((Get-FileHash $gguf).Hash -ne '068bae163faa96ad48032daf4e071a6a28fe67d8dcc95367609c2ff165e52738') { throw 'Unexpected model' }
llama-server --model $gguf --alias refine-qwen3 --host 127.0.0.1 --port 18081 --n-gpu-layers 99 --ctx-size 8192 --parallel 1 --threads 6 --jinja
```

첫 터미널에서 개발 제안을 생성합니다. 캐시는 데이터·후보·문단·프롬프트·모델 버전에 묶입니다. 서비스에서 로컬 설명을 사용할 때는 Spring을 시작하기 전에 `RAG_EXPLAINER=http://127.0.0.1:18081` 환경 변수를 설정합니다.

```powershell
& $py "$tools/run_local_rag.py" --retrieved backend/build/dev-ranks.json --passages "$data/evidence/passages.json" --cache-dir backend/build/local-rag-cache --output backend/build/dev-rag.json
& $py "$tools/release_evaluation.py" verify --dev-rag "$data/local-rag/development.json"
& $py "$tools/verify_nutrition_answers.py" --local-explainer
```

`verify`는 보관한 최종 32건·평가 수치·인용·분할·소스 및 벡터 해시를 대조합니다. 질의응답 검증기는 임시 메모리 DB를 만들고 종료합니다. 실제 MySQL의 승인 중복·버전 변경·롤백도 확인하려면 `bootJar`와 Docker의 `mysql:8.0` 이미지를 준비한 뒤 `$env:RUN_NUTRITION_HTTP_IT='1'`을 설정하고 `python backend/tools/rag_match/test_nutrition_mysql_http.py -v`를 실행합니다.

</details>

<img width="800" height="949" alt="Image" src="https://github.com/user-attachments/assets/42f0e93f-d0f5-485b-a71a-3ba15d4cd63c" />
<img width="800" height="766" alt="Image" src="https://github.com/user-attachments/assets/9f0e5a22-cb73-4908-8581-0c422eb0cef3" />

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
