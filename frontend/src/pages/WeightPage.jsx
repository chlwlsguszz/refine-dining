import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import YieldSearchResults, { YieldEstimate, ManualYield } from '../components/YieldSearchResults';
import '../components/cooking-yield.css';

const api = import.meta.env.VITE_API_BASE ?? '';
const examples = ['닭다리살', '소고기 안심', '돼지 등심'];

export default function WeightPage() {
    const [foodName, setFoodName] = useState('');
    const [cookingMethod, setCookingMethod] = useState('');
    const [baseWeight, setBaseWeight] = useState('200');
    const [searchResult, setSearchResult] = useState(null);
    const [submittedQuery, setSubmittedQuery] = useState(null);
    const [selectedId, setSelectedId] = useState('');
    const [acknowledged, setAcknowledged] = useState(false);
    const [estimate, setEstimate] = useState(null);
    const [searching, setSearching] = useState(false);
    const [calculating, setCalculating] = useState(false);
    const [searchError, setSearchError] = useState('');
    const [calculationError, setCalculationError] = useState('');
    const searchRequest = useRef(null);
    const predictionRequest = useRef(null);

    useEffect(() => () => {
        searchRequest.current?.abort();
        predictionRequest.current?.abort();
    }, []);

    const selected = searchResult?.matches?.find(match => match.evidence.id === selectedId);
    const validWeight = Number.isFinite(Number(baseWeight)) && Number(baseWeight) > 0
        && Number(baseWeight) <= 1000000 && /^\d+(?:\.\d{1,3})?$/.test(baseWeight);

    function clearSelection() {
        predictionRequest.current?.abort();
        setSelectedId('');
        setAcknowledged(false);
        setEstimate(null);
        setCalculating(false);
        setCalculationError('');
    }

    function changeQuery(field, value) {
        searchRequest.current?.abort();
        clearSelection();
        setSearching(false);
        setSearchResult(null);
        setSubmittedQuery(null);
        setSearchError('');
        if (field === 'food') setFoodName(value);
        else setCookingMethod(value);
    }

    function changeWeight(value) {
        predictionRequest.current?.abort();
        setBaseWeight(value);
        setEstimate(null);
        setCalculating(false);
        setCalculationError('');
    }

    async function search(query) {
        if (!query.foodName) return;
        searchRequest.current?.abort();
        clearSelection();
        const request = new AbortController();
        searchRequest.current = request;
        setSearching(true);
        setSearchResult(null);
        setSubmittedQuery(query);
        setSearchError('');
        try {
            const { data } = await axios.post(api + '/api/weight/search', query, { signal: request.signal });
            if (!request.signal.aborted) setSearchResult(data);
        } catch (error) {
            if (!request.signal.aborted) {
                setSearchError(error.response?.data?.message || '검색하지 못했습니다. 잠시 후 다시 시도해 주세요.');
            }
        } finally {
            if (!request.signal.aborted) setSearching(false);
        }
    }

    function submitSearch(event) {
        event.preventDefault();
        search({ foodName: foodName.trim(), cookingMethod: cookingMethod.trim() });
    }

    function searchExample(name) {
        setFoodName(name);
        setCookingMethod('');
        search({ foodName: name, cookingMethod: '' });
    }

    function selectEvidence(id) {
        clearSelection();
        setSelectedId(id);
    }

    async function calculate() {
        if (!selected?.canEstimate || !acknowledged || !validWeight || !submittedQuery) return;
        predictionRequest.current?.abort();
        const request = new AbortController();
        predictionRequest.current = request;
        setCalculating(true);
        setCalculationError('');
        setEstimate(null);
        try {
            const { data } = await axios.post(api + '/api/weight/predict', {
                ...submittedQuery, baseWeight: Number(baseWeight), evidenceId: selectedId, confirmReference: true,
            }, { signal: request.signal });
            if (request.signal.aborted) return;
            if (data.status === 'ESTIMATED') setEstimate(data);
            else setCalculationError(data.explanation || '선택한 기록을 계산에 적용할 수 없습니다. 다른 조건을 확인해 주세요.');
        } catch (error) {
            if (!request.signal.aborted) {
                setCalculationError(error.response?.data?.message || '계산하지 못했습니다. 잠시 후 다시 시도해 주세요.');
            }
        } finally {
            if (!request.signal.aborted) setCalculating(false);
        }
    }

    const confirmation = selected && <section className="yield-confirmation" aria-label="선택한 실험으로 중량 계산">
        <h2>선택한 실험으로 참고 계산</h2>
        <p><strong>입력한 식품</strong> {submittedQuery.foodName}
            {submittedQuery.cookingMethod && ` · ${submittedQuery.cookingMethod}`}</p>
        <p><strong>참고할 실험</strong> {selected.evidence.foodLabel} · {selected.evidence.methodLabel}</p>
        <p className="yield-note">선택한 실험의 평균 수율을 적용합니다. 실제 재료나 조리 조건의 차이에 따른 보정은 포함하지 않습니다.</p>
        <label className="yield-acknowledgement">
            <input type="checkbox" checked={acknowledged} onChange={event => {
                setAcknowledged(event.target.checked);
                predictionRequest.current?.abort();
                setEstimate(null);
                setCalculating(false);
            }} />
            <span>위의 조건과 차이를 확인했고, 이 실험의 수율로 참고 중량을 계산합니다.</span>
        </label>
        {!validWeight && <p role="alert" className="yield-error">조리 전 중량은 0보다 크고 1,000,000g 이하인 값으로 입력해 주세요. 소수 셋째 자리까지 사용할 수 있습니다.</p>}
        <button type="button" className="yield-action" disabled={!acknowledged || !validWeight || calculating}
            onClick={calculate}>{calculating ? '계산 중…' : `${baseWeight || '—'}g에 선택한 수율 적용`}</button>
        {calculationError && <p role="alert" className="yield-error">{calculationError}</p>}
        {estimate && <YieldEstimate result={estimate} query={submittedQuery} baseWeight={Number(baseWeight)} />}
    </section>;

    return <main className="yield-page"><div className="yield-wrap yield-search-wrap">
        <header><nav><Link to="/">Refine Dining</Link><Link to="/nutrition">영양 질의응답</Link></nav>
            <h1>검색해서 찾는 조리 후 중량</h1>
            <p>식품명을 입력하면 비슷한 실측 자료를 찾습니다. 내 재료와 실험의 차이를 확인하고 중량을 계산해 보세요.</p>
        </header>

        <form className="yield-card yield-search-form" onSubmit={submitSearch} noValidate>
            <div className="yield-fields">
                <label className="yield-field">식품명
                    <input type="search" value={foodName} maxLength={250} autoComplete="off"
                        placeholder="예: 닭다리살, 소고기 안심"
                        onChange={event => changeQuery('food', event.target.value)} />
                </label>
                <label className="yield-field"><span>조리법 <span className="yield-label-hint">선택</span></span>
                    <input value={cookingMethod} maxLength={100} autoComplete="off" placeholder="예: 구이, 삶기"
                        onChange={event => changeQuery('method', event.target.value)} />
                </label>
                <label className="yield-field">조리 전 중량 (g)
                    <input type="number" min="0.001" max="1000000" step="0.001" value={baseWeight}
                        onChange={event => changeWeight(event.target.value)} />
                </label>
            </div>
            <div className="yield-search-actions">
                <button type="submit" className="yield-action" disabled={!foodName.trim() || searching}>
                    {searching ? '비슷한 자료 찾는 중…' : '비슷한 실측 자료 찾기'}
                </button>
                <p className="yield-note">조리법을 비워 두면 여러 조리 조건을 함께 찾습니다.</p>
            </div>
            <div className="yield-examples"><span>검색 예시</span>{examples.map(name =>
                <button type="button" key={name} onClick={() => searchExample(name)}>{name}</button>
            )}</div>
        </form>

        {searchError && <p role="alert" className="yield-error">{searchError}</p>}
        {searching && <p role="status" className="yield-search-status">“{submittedQuery.foodName}”와 이름·조건이 가까운 실험을 찾고 있습니다.</p>}

        {searchResult && <section className="yield-search-results" aria-label="실측 자료 검색 결과">
            <div className="yield-search-heading"><h2>“{submittedQuery.foodName}” 검색 결과</h2>
                <p>{submittedQuery.cookingMethod ? `조리법 ${submittedQuery.cookingMethod} · ` : ''}
                    총 {searchResult.matches.length}개 후보 중 조건 확인 가능 {searchResult.matches.filter(match => match.canEstimate).length}개
                    {searchResult.sourceCount > 0 ? ` · ${searchResult.sourceCount}개 실측 기록에서 검색` : ''}</p>
            </div>
            {searchResult.message && <p className="yield-search-message">{searchResult.message}</p>}
            {searchResult.matches.length > 0 ? <>
                <p className="yield-note">조건을 확인해 계산에 적용할 수 있는 후보를 먼저 표시합니다. 부위·손질 상태·조리법의 차이를 확인해 주세요.</p>
                <YieldSearchResults matches={searchResult.matches} selectedId={selectedId} onSelect={selectEvidence}
                    selection={confirmation} />
            </> : <p className="yield-no-results">대응할 실측 기록을 찾지 못했습니다. 부위나 조리법을 바꿔 검색하거나, 직접 잰 중량을 입력할 수 있습니다.</p>}

            <ManualYield key={JSON.stringify(submittedQuery)} baseWeight={Number(baseWeight)} />
        </section>}
        <p className="yield-corpus-note">현재 실측 자료는 USDA의 육류·가금류 자료입니다. 식품명은 자유롭게 검색할 수 있으며, 근거가 없는 식품에는 예상값을 제시하지 않습니다.</p>
    </div></main>;
}
