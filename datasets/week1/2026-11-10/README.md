# 식품 매칭 1주차

**[어려운 식품 77건의 생것 후보와 보류 이유](dev-matching/results.html)** · [판정 JSON](dev-matching/proposals.json)

**[키워드·벡터·혼합 검색의 실제 결과 열기](retrieval-comparison.html)** · [행별 측정 JSON](retrieval-comparison.json)

## 이름만 보고 생것 찾기

오미자 말린것처럼 원문에서 대응하는 생것을 확인할 수 있는 가공 식품으로 첫 검색 실험을 진행했습니다. 동결 스냅샷에서 가공법 하나만 다른 이름을 찾고, 출처·분류·영양 기준량·수입 여부·저장된 관측 조건이 일치하며 생것이 하나인 쌍을 선정했습니다. 두 행이 같은 시료인지, 영양학적으로 비교할 수 있는지까지는 이 기준으로 알 수 없습니다.

- **실험 범위.** 명시적인 쌍 496건 중 기존 최종 평가 식품군의 41건을 보존하고, 199개 식품군의 **455건**을 측정했습니다. 이 455건에는 서로 다른 생것 326개가 대응합니다. 앞서 검수용으로 나눈 어려운 109건은 명시 쌍에 포함되지 않습니다.
- **검색 방법.** 매번 카탈로그 전체 생것 2,388행의 식품명만 검색합니다. 원문 식품명의 단어와 한글 두 글자 단위를 BM25로 비교했습니다. 정답 선정에 활용한 식품코드·분류 코드·출처·영양값은 점수 계산에서 제외했습니다. 동점 후보들이 경계를 걸치면 모두 경계 안에 들어갈 때만 확실한 적중으로 셉니다.
- **결과.** 단독 1위 **442/455건(97.1%)**, 상위 5개 안 **452/455건(99.3%)**입니다. `오미자_말린것`은 `오미자_생것`을 단독 1위로 찾았습니다. 상위 5개에서 놓친 3건은 모두 느타리버섯의 다른 처리 상태였습니다. 식품명에 ‘느타리버섯’이 반복되는 세부 품종 기록이 앞서면서 `느타리버섯_생것`은 6위였습니다.
- **잘못된 연결.** 원문에서 부위가 다른 것으로 확인한 6쌍은 모두 충돌로 분류했고, 같은 부위 대조 5쌍은 한 쌍도 차단하지 않았습니다. 부위 관계가 불명확한 2쌍은 판단을 유보했습니다. 예를 들어 `순무_뿌리_데친것`을 검색하면 `순무_잎_생것`이 1위였지만 뿌리와 잎의 차이로 제외됐습니다. 이 13쌍은 특정 오류 동작을 확인하기 위해 고른 사례입니다.

**해석 범위.** 이 실험은 표기가 가까운 식품을 다시 찾는 난이도를 측정합니다. 품종이 빠진 건포도 같은 어려운 식품의 매칭 성공률은 별도 평가가 필요합니다. 기존 109건은 독립적인 원문 근거가 확보된 경우에만 정답으로 편입합니다.

[455건의 기준 생것·실제 1위·순위 및 부위 검사 13쌍](name-benchmark.json)

저장소 루트에서 같은 결과를 다시 생성할 수 있습니다.

```powershell
$data = 'datasets/week1/2026-11-10'
python backend/tools/rag_match/run_name_benchmark.py --snapshot "$data/raw-snapshot.json" --split "$data/review/split-manifest.json" --output "backend/build/name-benchmark.json"
```

## 로컬 벡터 검색도 같은 짝을 찾는가

동일한 가공식품 455건을 동일한 생것 2,388개에서 검색했습니다. 키워드 BM25, 다국어 E5의 384차원 벡터 간 코사인 유사도, 둘의 순위를 합친 RRF를 비교했습니다. 모든 방식에 식품명만 전달했습니다. 순위는 원래 식품코드와 대조해 채점합니다. 외부 추론 API 호출은 0건입니다.

- **키워드 검색**은 단독 1위 442건, 상위 5개 안에 452건을 찾았습니다.
- **벡터 검색**은 단독 1위 440건, 상위 5개 안에 455건을 찾았습니다. 키워드 기준에서 13건을 새로 1위에 올렸고 15건은 1위에서 밀렸습니다. 느타리버섯 3건은 모두 6위에서 1위로 올랐습니다. 반대로 달걀 분말의 1위는 ‘달걀 생것’에서 ‘달걀 난백 생것’으로 바뀌었습니다.
- **혼합 검색**은 단독 1위 437건, 상위 5개 안에 455건을 찾았습니다. 기준 생것이 공동 1위인 14건은 단독 1위에서 제외했습니다. RRF는 두 방식의 양수 점수 후보 순위에 같은 가중치를 주고 상수 60을 적용했습니다. 동점은 구간의 평균 순위를 사용했습니다.
- **부위가 다른 6쌍** 중 잘못된 생것이 상위 5개에 들어간 사례는 키워드 6건, 벡터 4건, 혼합 4건이었습니다. ‘순무 뿌리 ↔ 잎’은 벡터에서 2위로 밀렸지만 ‘해삼 내장 ↔ 육’, ‘미국산 소고기 설도 ↔ 목심’은 세 방식 모두에서 잘못된 후보가 1위였습니다. 검색된 후보를 확정하기 전에 원문 부위를 대조해야 합니다.

상위 5개 성적은 이름과 관측 조건이 명확히 대응하는 사례에 한정됩니다. 아직 정답이 없는 109건의 매칭 성능은 측정하지 않았습니다. 결과 파일에는 모델 리비전·파일 해시·라이브러리 버전·스냅샷 ID가 들어 있습니다.

<details>
<summary>로컬 재현 방법 (Windows PowerShell, Python 3.12)</summary>

[E5 모델 카드](https://huggingface.co/intfloat/multilingual-e5-small)의 검색용 접두어를 사용합니다. 질의에는 `query:`, 생것 기록에는 `passage:`를 붙입니다. 밑줄은 공백으로 바꾸고, 양자화 ONNX 모델의 유효 토큰 출력을 평균 내어 L2 정규화합니다. 최초 한 번 모델과 패키지를 내려받은 후 로컬 CPU에서 실행할 수 있습니다.

```powershell
$data = 'datasets/week1/2026-11-10'
$rev = '761b726dd34fb83930e26aab4e9ac3899aa1fa78'
$model = "backend/build/models/multilingual-e5-small/$rev"
$remote = "https://huggingface.co/Xenova/multilingual-e5-small/resolve/$rev"
New-Item -ItemType Directory -Path "$model/onnx" -Force | Out-Null
curl.exe -fL "$remote/tokenizer.json" -o "$model/tokenizer.json"
curl.exe -fL "$remote/onnx/model_quantized.onnx" -o "$model/onnx/model_quantized.onnx"
if ((Get-FileHash "$model/tokenizer.json").Hash -ne '0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39') { throw 'Tokenizer hash mismatch' }
if ((Get-FileHash "$model/onnx/model_quantized.onnx").Hash -ne 'f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193') { throw 'Model hash mismatch' }
py -3.12 -m venv backend/build/e5-env
$py = 'backend/build/e5-env/Scripts/python.exe'
& $py -m pip install numpy==2.5.3 tokenizers==0.23.2 onnxruntime==1.30.0
& $py backend/tools/rag_match/embed_food_names.py --snapshot "$data/raw-snapshot.json" --baseline "$data/name-benchmark.json" --model-dir $model --revision $rev --threads 6 --output backend/build/e5-small-vectors.npz
& $py backend/tools/rag_match/compare_dense.py --snapshot "$data/raw-snapshot.json" --baseline "$data/name-benchmark.json" --vectors backend/build/e5-small-vectors.npz --output backend/build/retrieval-comparison.json
& $py backend/tools/rag_match/render_search_comparison.py --input backend/build/retrieval-comparison.json --output backend/build/retrieval-comparison.html
```

</details>

## 원문 근거가 추가로 필요한 109건

### 개발용 77건에서 실제로 찾은 후보

109건 중 개발로 배정한 33개 식품군의 77건(초기 검수용 20건과 나머지 57건)만 질의에 넣었습니다. 로컬 E5로 생것 2,388개를 식품명만으로 검색해 상위 5개씩 총 385개 후보를 얻었습니다. 최종 평가용 32건과 사람 검수 파일은 이 실험에 사용하지 않았습니다. 기존 수산물 실험의 77건과는 대상이 다릅니다.

- **DB 원문만 함께 읽었을 때:** `밀_통밀가루_분말화한것`에서 `밀_통밀_생것` 한 건을 참고 후보로 제안했습니다. 통밀과 영양 기준량 100g이 대응하지만, 양쪽의 실제 원산지는 확인할 수 없습니다. 나머지 76건은 보류했습니다.
- **공식 자료로 원료를 추가 확인한 결과:** 백삼과 홍삼은 수삼으로 제조한다는 정의가 있습니다. 말린 백삼과 말린 홍삼의 상위 후보에는 같은 출처·100g 기준의 수삼 생것이 한 건씩 있어 참고 후보에 추가했습니다. 두 표본의 산지와 연근 및 동일 시료 여부는 미확인입니다. 홍삼 추출물은 100mL, 수삼은 100g이라 보류했습니다. 보강한 자료와 적용 상태는 [근거 목록](dev-matching/processing-evidence.json)과 [인삼산업법 제2조](https://www.law.go.kr/LSW/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1025789929)에서 확인할 수 있습니다.
- **최종 제안:** 직접 비교 0건, 참고 비교 3건, 보류 74건. 이 수치는 검수 전 제안의 분포입니다. 이 집단은 같은 소분류에 생것이 없는 식품으로 골랐고, 직접 비교 기준에는 소분류 일치를 요구합니다. 보류는 이번에 찾은 후보와 근거만으로 선택하기 어렵다는 뜻입니다.
- **검색 실패 사례:** 미국산 카무트 가루의 상위 5개에는 미국산 양고기·송아지고기·칠면조고기가 나왔습니다. 다섯 후보 모두 밀과의 품목 대응 근거가 없어 보류했습니다. 개발용 77건 중 6건은 상위 5개에 같은 대표식품 코드가 하나도 없었습니다.

각 후보는 검색 순위와 별개로 품목·부위·품종 표기·기준량·원산지 등을 대조합니다. 385쌍 중 44쌍에는 명시적인 조건 충돌을 표시했고, 338쌍은 선택 근거 부족으로 남겼습니다. 어떤 후보도 자동으로 사용자용 비교 관계로 등록하지 않습니다.

<details>
<summary>개발용 매칭 재현</summary>

위의 로컬 재현 절차에서 만든 생것 벡터 파일과 고정 버전 모델을 재사용합니다. 아래는 저장소 루트의 PowerShell 예시입니다.

```powershell
$data = 'datasets/week1/2026-11-10'
$model = 'backend/build/models/multilingual-e5-small/761b726dd34fb83930e26aab4e9ac3899aa1fa78'
$py = 'backend/build/e5-env/Scripts/python.exe'
& $py backend/tools/rag_match/dev_candidate_search.py --snapshot "$data/raw-snapshot.json" --split "$data/review/split-manifest.json" --model-dir $model --raw-vectors backend/build/e5-small-vectors.npz --output backend/build/dev77-retrieved.json
& $py backend/tools/rag_match/assess_development.py --retrieved backend/build/dev77-retrieved.json --snapshot "$data/raw-snapshot.json" --split "$data/review/split-manifest.json" --process-evidence "$data/dev-matching/processing-evidence.json" --output backend/build/dev77-proposals.json
& $py backend/tools/rag_match/render_dev_matches.py --input backend/build/dev77-proposals.json --output backend/build/dev77-results.html
```

</details>

[개발용 20건 검수 화면](review/dev20-review.html)을 브라우저에서 열면 바로 시작할 수 있습니다. 라이브 서버나 API 키는 필요하지 않습니다.

## 검수 방법

1. 대상 식품명과 생것 후보의 품목, 부위, 가공 전 상태, 원산지, 관측 조건, 영양 기준량을 대조합니다. 양쪽 모두 **DB 원본 행 전체**를 펼칠 수 있습니다.
2. 같은 출처·대표식품에 속하는 생것을 초기 후보로 제시합니다. 표시는 식품코드와 고정 시드로 섞은 순서입니다. **전체 생것에서 추가 검색**으로 초기 목록 밖의 생것도 찾아 선택할 수 있습니다.
3. 적합한 후보마다 **직접 비교** 또는 **참고 비교**를 고릅니다. 여러 후보가 타당하면 모두 선택합니다. 적절한 후보가 없음을 확인하면 **비교 불가**, 정보가 부족하면 **판단 보류**로 표시합니다.
4. **판단 근거**에 후보별로 어떤 원문 표현이 일치하거나 충돌하는지 적고 **이 건 확정**을 누릅니다. 확정한 행을 수정하면 작성 중으로 돌아갑니다.
5. **검수 JSON 내보내기**로 진행 중인 작업도 파일로 보관할 수 있습니다. 같은 묶음에서 **검수 JSON 불러오기**로 복원할 수 있습니다. 브라우저의 임시 저장은 브라우저·기기에 종속됩니다.

모든 행은 미검수로 시작합니다. 평가에 쓸 수 있는 정답은 확정된 후보 선택 또는 확정된 비교 불가입니다. 판단 보류, 미검수, 미확정 초안은 평가 분모에서 제외합니다.

## 원본과 분할

- [원본 스냅샷](raw-snapshot.json)은 2026-11-10에 읽기 전용 트랜잭션으로 추출한 MySQL `raw_food_materials`의 3,701행·56열입니다. 영양값은 수집 파서가 변환한 DB 저장값입니다. 과거 결측과 실측 0을 분리하려면 해당 원천 기록을 재확인해야 합니다. 100g 기준은 3,678행, 100mL 기준은 23행입니다.
- [109건 전체 분할표](review/food-groups.csv)는 식품군·식품코드·출처·초기 후보 수·용도를 담습니다. [분할 명세](review/split-manifest.json)에는 스냅샷·검수 묶음 ID, 고정 시드, 이전 감사 CSV와의 대조 기록이 있습니다.
- 대상은 원본 전체에 동일 소분류의 생것이 없고, 같은 출처의 상위 분류에서 생것을 찾을 수 있는 109행입니다. 같은 중분류까지 일치하는 행은 51건, 대표식품까지만 일치하는 행은 58건입니다. 이전 집계와 식품코드 및 구분을 전수 대조했습니다.
- 대표식품(Lv4) 코드 단위로 묶고, 공백 등을 정규화한 공식 대표식품명이 같을 때도 같은 군으로 합쳤습니다. ‘보리’ 코드 01025와 06213을 포함해 총 48개 코드가 47개 식품군을 이룹니다. 이 분할에서 식품군은 이 대표식품 단위를 뜻합니다.
- 시드 `20261110`으로 식품군 전체를 한쪽에만 배정했습니다. 개발은 33군 77행, 최종 평가는 14군 32행입니다. 이번 20행은 개발 중 20개 식품군에서 한 행씩 뽑았습니다. 같은 중분류에서 찾는 9행, 대표식품까지 넓히는 11행이며, 나머지 개발 57행은 후속 작업용입니다. 여기서의 개발 77행은 앞선 수산물 77건 실험과 다른 집합입니다.
- 최종 평가용 질의와 라벨은 이번 검수 화면에 들어 있지 않습니다. 검색 대상인 생것 2,388행은 공통 자료로 사용합니다. 소수 출처인 출처 코드 3의 대상 4행은 모두 개발에 배정되어 이 분할만으로 해당 출처의 평가 성능을 추정할 수 없습니다.

## 재현

프로젝트 루트에서 아래 명령으로 동결된 JSON의 내용 해시를 확인하고 같은 분할·화면을 새 디렉터리에 생성할 수 있습니다. 이전 감사 파일도 확인하려면 `--previous-csv`에 이전에 내보낸 `refinement-candidates.csv` 경로를 전달합니다.

```powershell
python backend/tools/rag_match/prepare_week1.py --snapshot datasets/week1/2026-11-10/raw-snapshot.json --output-dir backend/build/week1-review --seed 20261110
```

스냅샷 내용 해시는 `sha256:cc6de9d66cbfc1c3e71efd886a01483133932e5ab6ff1efd9db6ba1275b20484`입니다. 해시는 스키마와 식품코드 순 전체 행으로 계산합니다. 검수 묶음 ID는 `6b04c5c07d85ac38aa6ae2bd8ce8c79538a67d0dd34c943c35000e126adf825e`입니다.
