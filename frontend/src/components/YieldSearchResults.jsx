import { useState } from 'react';

const number = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 });
const relationLabels = { MATCH: '조건 확인', REFERENCE: '참고 후보', INCOMPATIBLE: '조건 차이로 계산 제외' };

function SourceDetails({ evidence }) {
    return <details className="yield-source-details"><summary>원문과 실측 수율 보기</summary>
        <dl className="yield-evidence">
            {evidence.sourceDescription && <><dt>원문 식품명</dt><dd>{evidence.sourceDescription}</dd></>}
            {evidence.sourceMethod && <><dt>원문 조리법</dt><dd>{evidence.sourceMethod}</dd></>}
            <dt>중량 기준</dt><dd>{evidence.rawBasis}</dd>
            <dt>평균 수율</dt><dd>{number.format(evidence.meanPercent)}%</dd>
            {evidence.minPercent != null && evidence.maxPercent != null && <>
                <dt>관측 수율 범위</dt><dd>{number.format(evidence.minPercent)}–{number.format(evidence.maxPercent)}%</dd>
            </>}
            <dt>표본 수</dt><dd>{evidence.sampleCount == null ? '원표에 미기재' : number.format(evidence.sampleCount)}</dd>
            <dt>출처</dt><dd><a href={evidence.sourceUrl} target="_blank" rel="noreferrer">{evidence.title}</a>
                <span className="yield-source-position">{evidence.version} · {evidence.sourceRow}</span></dd>
        </dl>
        {evidence.statisticNote && <p className="yield-note">{evidence.statisticNote}</p>}
    </details>;
}

function EvidenceCard({ match, index, selected, onSelect, selection }) {
    const evidence = match.evidence;
    return <li className={`yield-search-candidate${selected ? ' is-selected' : ''}`}>
        <div className="yield-candidate-top"><span className="yield-candidate-rank">후보 {index + 1}</span>
            <span className={`yield-relation${match.canEstimate ? '' : ' is-incompatible'}`}>
                {relationLabels[match.relation] || '조건 확인 필요'}
            </span>
        </div>
        <h3>{evidence.foodLabel}</h3><p className="yield-candidate-method">{evidence.methodLabel}</p>
        {match.reasons?.length > 0 && <div className="yield-match-reasons"><strong>검색한 이유</strong>
            <ul>{match.reasons.map((reason, index) => <li key={`${index}-${reason}`}>{reason}</li>)}</ul>
        </div>}
        {match.differences?.length > 0 && <div className="yield-match-differences"><strong>확인할 차이</strong>
            <ul>{match.differences.map((difference, index) => <li key={`${index}-${difference}`}>{difference}</li>)}</ul>
        </div>}
        <p className="yield-candidate-conditions"><strong>실험 조건</strong> {evidence.conditions}</p>
        <p className="yield-note"><strong>중량 기준</strong> {evidence.rawBasis}</p>
        <SourceDetails evidence={evidence} />
        {match.canEstimate ? <label className="yield-candidate-select">
            <input type="radio" name="yield-evidence" checked={selected} onChange={() => onSelect(evidence.id)} />
            <span>이 실험을 참고할 자료로 선택</span>
        </label> : <p className="yield-note yield-excluded">이 기록은 차이를 확인하는 참고 자료이며 중량 계산에는 적용할 수 없습니다.</p>}
        {selected && selection}
    </li>;
}

export default function YieldSearchResults({ matches, selectedId, onSelect, selection }) {
    const ranked = matches.map((match, index) => ({ match, index }));
    const applicable = ranked.filter(({ match }) => match.canEstimate);
    const different = ranked.filter(({ match }) => !match.canEstimate);
    function cards(rows) {
        return <ol className="yield-candidate-list">{rows.map(({ match, index }) =>
            <EvidenceCard key={match.evidence.id} match={match} index={index}
                selected={selectedId === match.evidence.id} onSelect={onSelect} selection={selection} />
        )}</ol>;
    }
    if (applicable.length === 0) return cards(ranked);
    return <>
        {cards(applicable)}
        {different.length > 0 && <details className="yield-different-candidates"
            defaultOpen={different.some(({ match }) => match.evidence.id === selectedId)}>
            <summary>조건 차이가 있는 후보 {different.length}개 보기</summary>
            {cards(different)}
        </details>}
    </>;
}

export function YieldEstimate({ result, query, baseWeight }) {
    return <div className="yield-result yield-search-estimate" role="status">
        <p className="yield-result-title">선택한 실험 수율로 계산한 참고 중량</p>
        <strong className="yield-weight">{number.format(result.predictedWeight)} g</strong>
        <p>{query.foodName} {number.format(baseWeight)}g × 참고 수율 {number.format(result.yieldPercent)}%</p>
        {result.explanation && <p className="yield-note">{result.explanation}</p>}
        {result.minWeight != null && result.maxWeight != null && <p>
            연구의 최저·최고 수율을 환산한 범위 <strong>{number.format(result.minWeight)}–{number.format(result.maxWeight)}g</strong>
        </p>}
        {result.minWeight != null && result.maxWeight != null && <p className="yield-note">표시한 범위는 연구에서 관측한 값입니다. 실제 조리 결과의 보장 범위나 예측 구간은 아닙니다.</p>}
        <SourceDetails evidence={result.evidence} />
    </div>;
}

export function ManualYield({ baseWeight }) {
    const [measuredWeight, setMeasuredWeight] = useState('');
    const showRatio = Number.isFinite(Number(measuredWeight)) && Number(measuredWeight) > 0
        && Number.isFinite(baseWeight) && baseWeight > 0;
    return <details className="yield-manual yield-search-manual"><summary>직접 잰 조리 후 중량 입력</summary>
        <label className="yield-field">직접 잰 조리 후 중량 (g)
            <input type="number" min="0" step="any" value={measuredWeight}
                onChange={event => setMeasuredWeight(event.target.value)} />
        </label>
        {showRatio && <p className="yield-note">입력한 중량의 수율 {number.format(Number(measuredWeight) / baseWeight * 100)}%</p>}
    </details>;
}
