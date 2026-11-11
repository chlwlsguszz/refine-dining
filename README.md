# Refine Dining
## 원문을 확인하는 로컬 영양 RAG

[프로젝트 포트폴리오 · 같은 옥수수인데 왜 비교를 보류했을까?](docs/portfolio/README.md)

‘옥수수_강다옥_말린것 100g 단백질 비교’라고 물으면, 말린 강다옥의 단백질 9.82g과 식품코드를 보여줍니다. 가장 가까운 생것 후보는 다른 품종인 고당옥이라 두 식품의 차이는 보류합니다. 검수자가 승인한 쌍은 양쪽 원문과 차이를 함께 표시합니다. 영상의 승인 사례는 격리된 시연 DB에서 검증했고, 새 DB는 승인 0건으로 시작합니다. [3분 영상](datasets/week1/2026-11-10/release/nutrition-demo.mp4) · [최종 평가 32건](datasets/week1/2026-11-10/release/README.md) · [질문별 검증 결과](datasets/week1/2026-11-10/release/answer-checks.json)

- **검색**. 동결 원본 3,701행에서 생것 2,388개를 E5로 벡터화합니다. 같은 대표식품에서 최대 3개를 확보하고 전체 검색으로 보완해 5개를 제시합니다. 개발 77건 중 같은 대표식품이 검색된 경우가 71건에서 77건으로 늘었고, 이름이 명확한 455쌍은 모두 상위 5개에 남았습니다. [네 가지 검색 방식과 개별 순위](datasets/week1/2026-11-10/retrieval-policy/comparison.json)
- **근거와 판정**. 가공 상태에 맞는 공식 문단을 별도로 검색합니다. 로컬 Qwen3-8B가 후보 코드·판정·인용을 생성하고, 서버에 넘기기 전에 후보 범위·원문·단위·부위 충돌을 검증합니다. 개발 자료에서 원문 기준으로 제안한 참고 후보는 1건, 가공 정의를 더하면 3건입니다. 같은 자료를 받은 Qwen은 77건을 모두 보류했습니다. 서비스의 검수 목록은 확인 가능한 3건의 참고 제안과 74건의 보류를 담습니다. [개발 결과](datasets/week1/2026-11-10/local-rag/development.json) · [74건별 부족한 근거](datasets/week1/2026-11-10/evidence/hold-audit.json) · [로컬 추론 측정](datasets/week1/2026-11-10/local-rag/runtime-measurement.json)
- **계산과 공개**. 공공데이터포털 공개 다운로드 3,704행과 동결 DB의 식품코드·출처·관측 조건을 대조했습니다. 24개 영양 항목 88,824칸 가운데 원문 수치 63,125칸(그중 실제 0은 11,048칸), 결측 25,699칸을 구별합니다. MySQL 또는 로컬 H2에 버전별 원문·제안·검수 사유를 보관합니다. 수치와 차이는 서버가 계산하고, 자유형 설명에서 로컬 모델은 승인 근거 중 제시할 문장을 선택합니다. [공공데이터 원자료](https://www.data.go.kr/data/15100065/standard.do) · [보관한 다운로드 원본](datasets/week1/2026-11-10/nutrition/official-materials.json.gz)
- **평가 범위**. 14개 식품군 32건의 최종 평가 결과는 직접 0·참고 0·보류 32건입니다. 독립 검수 정답이 없어 최종 정확도·회수율·오연결률은 산출할 수 없습니다. 455쌍은 이름이 명확한 사례의 검색 회귀에 사용합니다. [동결 설정](datasets/week1/2026-11-10/release/freeze.json) · [식품별 후보와 응답](datasets/week1/2026-11-10/release/report.json)

새 체크아웃에서 인덱스를 다시 만들고 77건을 생성했을 때 검색 순위·선택 코드·판정·인용은 일치했습니다. GPU에서 다시 생성한 응답 5건은 설명에 표시할 차이 항목이 달랐습니다. 캐시를 사용한 재실행에서는 77건의 응답이 일치했습니다. [새 체크아웃 재현 기록](datasets/week1/2026-11-10/release/reproduction.json)

### 조리 후 중량 검색과 계산

[중량 화면](http://127.0.0.1:18082/weight)에서 식품명을 자유롭게 검색합니다. `닭다리살`, `소고기 안심`, `돼지 등심`처럼 입력하면 로컬 E5가 USDA 원표 173개 기록에서 비슷한 식품·부위·조리법을 찾습니다. 각 후보에는 검색한 이유, 입력과의 차이, 실험 조건과 원문 위치가 표시됩니다. 검색어는 그대로 유지하고 참고할 실험을 별도로 선택합니다. [자료 범위와 검색 방식](datasets/cooking-yield/README.md)

사용자가 조건을 확인한 뒤 계산을 요청하면 서버가 생중량에 선택한 실험의 평균 수율을 곱합니다. 껍질 포함 닭 넓적다리 오븐구이 기록의 수율 69%를 200g에 적용하면 참고 중량 138g입니다. 확인되지 않거나 충돌하는 동물 종류·부위·손질 상태·조리법이 있으면 후보의 차이는 보여주되 계산에는 적용하지 않습니다. 현재 원표는 육류·가금류이므로 채소 등 자료가 없는 식품에는 숫자를 제시하지 않습니다.

기존 28개 기록으로 진행했던 외부 패티 연구 평가에서는 13개 조리군 중 5개에 수율을 적용했습니다. 중량을 보고한 두 조리군의 평균 절대오차는 3.15g, 같은 두 건에 고정 70% 수율을 쓴 오차는 2.10g이었습니다. 이 결과는 확대된 173개 기록의 검색 정확도를 평가한 수치가 아닙니다. [평가 입력·결과와 한계](datasets/cooking-yield/evaluation/README.md)

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

- **Backend**: Spring Boot 3.3, Spring Data JPA, MySQL 8.0
- **Frontend**: React 19 + Vite
- **Infra**: Docker, Nginx, Docker Compose
- 조리 중량 데이터: USDA 육류·가금류 실측 수율

## 주요 기능

- **식품명 검색 및 페이지네이션**: 정확도순 정렬 및 배치 페치(`default_batch_fetch_size`) 최적화
- **대표 식품(원재료)과 조리 방법별 영양소 비교**: 중량 변경에 따른 실시간 영양소 증감 비교 및 URL 직접 공유 지원
- **조리 후 중량 계산**: 원표의 부위·조리법·지방 범위를 확인하고 예상 중량과 원문을 조회
- **관리자 배치 API (`X-Admin-Key` 보호 지원)**:
  - 공공데이터 원본 동기화 (페이지별 독립 트랜잭션 및 일괄 조회로 N+1 방지)
  - 정제 데이터 생성 및 부모(생것)-자식(조리법) 계층화
  - 현재 정제 규칙으로 제외되는 원본 행의 사유별 건수와 예시 조회

## 시스템 구조

```mermaid
flowchart LR
    PD[공공데이터포털 API] -->|sync-raw| RAW[(raw_food_materials)]
    RAW -->|refine| REF[(food_materials)]
    REF --> SEARCH[식품 검색 / 비교 API]
    SEARCH --> FE[React Client]
    FE -->|predict| WEIGHT[중량 예측 API]
    WEIGHT --> YIELD[USDA 실측 수율표]
```

1. `sync-raw`로 공공데이터 API 원본을 `raw_food_materials`에 페이지 단위로 동기화
2. `refine`로 소분류(`foodLv6Cd`) 기준 원재료(`01`, 생것)와 조리 방법별 자식 데이터를 계층화하여 `food_materials` 생성
3. 검색/비교 API가 정제 데이터를 조회
4. 비교 화면에서 실측 수율의 적용 조건을 확인하고 조리 후 예상 중량을 반영

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
- `ADMIN_API_KEY` (선택, 설정 시 관리자 배치 API에서 `X-Admin-Key` 헤더 검증)

실행:

```bash
cd backend
./gradlew bootRun
```

### 2) Frontend

Vite 개발 서버 프록시(`/api` → `http://localhost:8080`)가 설정되어 있어 별도 환경변수 없이 바로 실행할 수 있습니다.

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
ADMIN_API_KEY=your_optional_admin_key
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

### 비교 데이터 단건 조회

```http
GET /api/food/compare/{childId}
```

### 실측 조리 수율 검색

`POST /api/weight/search`에 `foodName`과 선택적인 `cookingMethod`를 보냅니다. 자유 입력 질의에 대해 검색 이유·차이·원문을 담은 후보를 반환합니다. `canEstimate`가 참인 후보만 사용자가 확인한 뒤 `POST /api/weight/predict`에 원래 질의, g 단위 `baseWeight`, 선택한 `evidenceId`, `confirmReference:true`를 보냅니다. 서버는 해당 기록이 현재 검색 결과에 있는지와 조건 충돌을 다시 검사합니다. `GET /api/weight/options`는 전체 원표 목록입니다.

```json
{"foodName":"닭다리살","cookingMethod":"구이","baseWeight":200,"evidenceId":"usda-r2-05094","confirmReference":true}
```

로컬 의미 검색은 `python backend/tools/cooking_yield/suggest_names.py --port 18086`으로 시작하고 Spring에 `YIELD_SEARCH_URL=http://127.0.0.1:18086`을 설정합니다. 검색기가 없으면 제한된 이름·부위 검색으로 전환되며 응답에 이 상태를 표시합니다. 외부 LLM API는 사용하지 않습니다.

### 관리자 배치

```http
POST /api/admin/food-data/sync-raw
X-Admin-Key: your_optional_admin_key

POST /api/admin/food-data/refine
X-Admin-Key: your_optional_admin_key
```

### 정제 제외 건수 조회

`GET /api/admin/food-data/refine-report`는 조회 시점의 `raw_food_materials`에 현재 정제 규칙을 적용해 집계합니다. 정제 테이블을 다시 만들 필요 없이 조회할 수 있습니다. 전체 수집분을 보려면 `sync-raw`가 완료된 뒤 호출하세요. 집계는 원본 테이블에 적재된 행부터 시작하므로 수집 실패 페이지나 식품코드 누락으로 적재되지 않은 항목은 범위 밖입니다.

다음은 로컬 백엔드용 PowerShell 예시입니다. Docker Compose로 접속할 때는 주소를 `http://localhost/api/admin/food-data/refine-report`로 바꾸세요. 서버에 관리자 키를 설정했다면 현재 PowerShell 세션의 `ADMIN_API_KEY` 환경변수에 같은 값을 지정하세요. 키를 사용하지 않는 환경에서는 헤더를 비워 둡니다.

```powershell
$headers = @{}
if ($env:ADMIN_API_KEY) {
    $headers['X-Admin-Key'] = $env:ADMIN_API_KEY
}
$report = Invoke-RestMethod -Uri 'http://localhost:8080/api/admin/food-data/refine-report' -Headers $headers
$report | Format-Table totalRawRows, retainedParents, retainedChildren, excludedRows
$report.exclusions.PSObject.Properties | Format-Table Name, @{Name='Count'; Expression={$_.Value.count}}
```

`totalRawRows`는 생것으로 유지되는 `retainedParents`, 조리식품으로 유지되는 `retainedChildren`, 제외되는 `excludedRows`의 합입니다. `exclusions`는 0건인 사유까지 모두 담으며 각 사유에 설명(`description`), 행 수(`count`), 최대 3개의 원본 예시(`examples`)를 제공합니다. 예시의 `foodCd`, `foodNm`, `foodLv6Cd`, `foodLv7Cd`, `foodLv7Nm`으로 원본과 분류를 확인할 수 있습니다.

각 행에는 주된 제외 사유를 하나만 부여합니다.

1. 식품명이 null이면 `MISSING_FOOD_NAME`, 수산물 출처 코드 2의 식품명에 ‘대표’와 ‘평균’ 중 하나라도 없으면 `SEAFOOD_NAME_FILTER`, 소분류 코드가 비어 있으면 `MISSING_LV6_CODE`로 차례대로 분류합니다.
2. 남은 행을 소분류로 묶습니다. 그룹에 생것(`01`)이 없으면 그룹의 모든 행을 `NO_RAW_PARENT`로 셉니다.
3. 생것이 있는 그룹에서 두 번째 이후의 생것은 `ADDITIONAL_RAW_PARENT`로 셉니다. 조리식품의 세분류 코드가 비어 있으면 `MISSING_COOKING_CODE`, 값이 있어도 현재 조리법으로 매핑되지 않으면 `UNMAPPED_COOKING_CODE`로 셉니다. `unmappedCookingCodes`에서 이 미등록 코드별 건수를 확인할 수 있습니다.
4. 그룹에 인식 가능한 조리식품이 없으면 첫 번째 생것을 `NO_SUPPORTED_CHILD`로 셉니다.

### 생것 후보 RAG 매칭 검토

[1주차 원본 스냅샷과 개발용 20건 검수 화면](datasets/week1/2026-11-10/README.md)에서 상위 분류 탐색 대상 109건의 식품군별 분할과 사람 검수 방법을 확인할 수 있습니다.

정제 과정에서 같은 소분류의 생것 부모를 찾지 못한 행 중, 원본에 같은 출처·대표식품·소분류의 생것 후보가 둘 이상 있는 행을 검토합니다. MySQL에서 후보 전부의 식품명과 관측 정보를 조회합니다. 기본 경로는 로컬에서 관측 조건을 대조하고, 결과와 원문을 오프라인 HTML 파일로 저장합니다.

아래 명령은 저장소 루트에서 실행합니다. 원본이 적재된 Compose MySQL과 Python 3.9 이상이 필요합니다. 이미 저장한 `evidence.json`이 있으면 로컬 매칭부터 다시 실행할 수 있습니다.

```powershell
docker compose start mysql
$out = 'backend/build/rag-review'
python backend/tools/rag_match/retrieve.py --output "$out/evidence.json"
python backend/tools/rag_match/local_review.py --evidence "$out/evidence.json" --output "$out/local.json"
python backend/tools/rag_match/render_review.py --evidence "$out/evidence.json" --matches "$out/local.json" --output "$out/review.html"
```

Gemini 판정과 비교하는 실험은 별도로 실행합니다. 이때 프로젝트 `.env` 또는 환경변수의 `GEMINI_API_KEY`를 사용해 원문과 후보를 모델에 보냅니다. 이미 생성된 판정을 검증하거나 HTML로 열 때는 API 키가 필요하지 않습니다.

```powershell
python backend/tools/rag_match/match.py --evidence "$out/evidence.json" --output "$out/decisions.json"
python backend/tools/rag_match/match.py --evidence "$out/evidence.json" --output "$out/decisions.json" --validate-only
python backend/tools/rag_match/render_review.py --evidence "$out/evidence.json" --matches "$out/decisions.json" --baseline "$out/local.json" --output "$out/comparison.html"
```

`review.html`을 브라우저에서 열면 판정별 필터와 식품명·코드 검색을 사용할 수 있습니다. **직접 비교**는 품목·부위·기준량과 관측 범위가 일치하는 경우, **참고 비교**는 한 후보를 고를 근거가 있지만 지역이나 월 등 차이가 남는 경우입니다. **보류**에서는 경합한 후보와 선택하기 어려운 이유를 확인할 수 있습니다. 배치가 중단되면 같은 근거·모델·출력 경로로 재개할 수 있습니다.

원문 대조 후 일부 행을 다시 판정하려면 `--review-notes`에 식품코드를 키로, 확인할 사실을 값으로 담은 JSON을 전달합니다. 기존 출력에서 재검토 메모가 바뀐 행과 미완료 행만 호출합니다. 필요한 경우 `--continue-with-model`로 이 행에 쓸 Gemini 모델을 지정할 수 있습니다. 검토 화면에는 행마다 실제 판정 모델과 재검토 메모가 표시됩니다.

## 트러블슈팅 메모

- **공공데이터 HTTPS 및 비정상 응답 방어**: 공공데이터 API는 HTTP 요청 시 301 리다이렉트(HTML)를 반환할 수 있어 `public-data.base-url`을 HTTPS로 사용하며, `PublicDataClient`에서 HTML 응답 여부를 사전 검증합니다.
- **컬렉션 Fetch Join 페이징(HHH90003004) 해결**: `OneToMany` 컬렉션(`children`)을 Fetch Join과 함께 페이징할 때 발생하는 인메모리 페이징 문제를 방지하기 위해, 부모 엔티티만 DB 페이징 조회하고 `default_batch_fetch_size: 100`으로 자식 컬렉션을 IN 쿼리로 일괄 조회합니다.
- **Gemini 2.5 Thinking 토큰 한도 이슈 해결**: `gemini-2.5-flash` 모델 호출 시 내부 thinking 토큰이 `maxOutputTokens`를 소진하여 빈 응답이 반환되는 문제를 `thinkingBudget: 0` 설정 및 헤더 기반 인증(`x-goog-api-key`)으로 해결했습니다.

## 보안 주의사항

- API 키/비밀번호는 절대 Git에 커밋하지 마세요.
- `.env`, `application-local.yml` 등 로컬 비밀 설정은 `.gitignore` 및 `.dockerignore`로 버전 관리와 Docker 이미지 빌드 컨텍스트에서 제외됩니다.
