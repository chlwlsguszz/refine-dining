import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import './cooking-yield.css';

const api = import.meta.env.VITE_API_BASE ?? '';
const number = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 });

function ManualWeight({ baseWeight, manualInputId }) {
    const [measured, setMeasured] = useState('');
    if (manualInputId) {
        return <button className="yield-secondary" type="button"
            onClick={() => document.getElementById(manualInputId)?.focus()}>
            조리 후 중량 직접 입력
        </button>;
    }
    return <label className="yield-field">직접 잰 조리 후 중량 (g)
        <input type="number" min="0" step="any" value={measured} onChange={e => setMeasured(e.target.value)} />
        {Number(measured) > 0 && <span className="yield-note">
            입력한 중량의 수율 {number.format(100 * Number(measured) / baseWeight)}%
        </span>}
    </label>;
}

function Estimate({ result, baseWeight, onApply }) {
    const record = result.evidence;
    return <div className="yield-result">
        <p className="yield-result-title">조리 후 예상 중량</p>
        <strong className="yield-weight">{number.format(result.predictedWeight)} g</strong>
        <p>조리 전 {number.format(baseWeight)} g × 평균 수율 {number.format(result.yieldPercent)}%</p>
        {result.minWeight != null && result.maxWeight != null && <p>
            연구의 최저·최고 수율로 계산한 범위 <strong>{number.format(result.minWeight)}–{number.format(result.maxWeight)} g</strong>
        </p>}
        <dl className="yield-evidence">
            <dt>실험 조건</dt><dd>{record.foodLabel} · {record.methodLabel}<br />{record.conditions}</dd>
            <dt>중량 기준</dt><dd>{record.rawBasis}</dd>
            {record.sampleCount != null && <><dt>표본 수</dt><dd>{number.format(record.sampleCount)}개</dd></>}
            <dt>출처</dt><dd><a href={record.sourceUrl} target="_blank" rel="noreferrer">{record.title}</a>
                {' · 원표 '}{record.sourceRow}</dd>
        </dl>
        {onApply && <button type="button" className="yield-action"
            onClick={() => onApply(result.predictedWeight)}>비교 화면에 {number.format(result.predictedWeight)} g 적용</button>}
    </div>;
}

export default function CookingYieldPanel({ foodName, foodCd, cookingMethod, baseWeight, onApply, onChangeCondition, manualInputId, onSuggestedFood }) {
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [selectedId, setSelectedId] = useState('');
    const pending = useRef(null);
    // The caller keys this panel by the submitted food, method and raw weight.
    useEffect(() => () => { pending.current?.abort(); }, []);

    async function lookup(evidenceId) {
        pending.current?.abort();
        const request = new AbortController();
        pending.current = request;
        setBusy(true);
        setError('');
        try {
            const { data } = await axios.post(api + '/api/weight/predict', {
                foodName, foodCd, cookingMethod, baseWeight: Number(baseWeight), evidenceId: evidenceId || null,
            }, { signal: request.signal });
            if (request.signal.aborted) return;
            setResult(data);
            setSelectedId('');
        } catch (err) {
            if (request.signal.aborted) return;
            setError(err.response?.data?.message || '수율을 조회할 수 없습니다. 잠시 후 다시 시도해 주세요.');
        } finally {
            if (!request.signal.aborted) setBusy(false);
        }
    }

    const ready = foodName?.trim() && cookingMethod?.trim() && Number.isFinite(Number(baseWeight)) && Number(baseWeight) > 0;
    return <section className="yield-panel" aria-label="실측 수율로 예상 중량 계산" aria-busy={busy}>
        {!result && <button type="button" className="yield-action" disabled={!ready || busy} onClick={() => lookup()}>
            {busy ? '수율 조회 중…' : '실측 수율 조회'}
        </button>}
        {error && <p role="alert" className="yield-error">{error}</p>}
        {result?.status === 'NEED_CONDITIONS' && <>
            <fieldset className="yield-options" disabled={busy}>
                <legend>실제 조리 조건과 일치하는 기록을 선택하세요</legend>
                {result.candidates.map(row => <label className="yield-choice" key={row.id}>
                    <input type="radio" name="yield-study" value={row.id}
                        checked={selectedId === row.id} onChange={() => setSelectedId(row.id)} />
                    <span><strong>{row.foodLabel} · {row.methodLabel}</strong>
                        <span>{row.conditions}</span>
                        <small>{row.rawBasis}</small>
                    </span>
                </label>)}
            </fieldset>
            <button type="button" className="yield-action" disabled={busy || !selectedId} onClick={() => lookup(selectedId)}>
                {busy ? '계산 중…' : '선택한 조건으로 계산'}
            </button>
            <details className="yield-manual"><summary>일치하는 조건이 없나요?</summary>
                <ManualWeight baseWeight={baseWeight} manualInputId={manualInputId} />
            </details>
        </>}
        {result?.status === 'ESTIMATED' && <>
            <Estimate result={result} baseWeight={baseWeight} onApply={onApply} />
            <button type="button" className="yield-secondary yield-change" onClick={() => {
                onChangeCondition?.();
                setResult(null);
                lookup();
            }} disabled={busy}>
                조건 다시 선택
            </button>
        </>}
        {result?.status === 'NO_MATCH' && <div className="yield-manual">
            <p role="status">{result.explanation || '조건에 맞는 실측 수율이 없습니다.'}</p>
            <ManualWeight baseWeight={baseWeight} manualInputId={manualInputId} />
            {onSuggestedFood && result.suggestedFoods?.length > 0 && <div className="yield-suggestions">
                <p>비슷한 식품명입니다. 실제 부위가 일치하면 식품명을 선택한 뒤 다시 조회하세요.</p>
                {result.suggestedFoods.map(name => <button type="button" key={name} className="yield-secondary"
                    onClick={() => onSuggestedFood(name)}>{name}</button>)}
            </div>}
        </div>}
    </section>;
}
