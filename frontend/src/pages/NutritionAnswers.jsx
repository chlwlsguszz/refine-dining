import { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './nutrition.css';
import './nutrition-answers.css';

const api = import.meta.env.VITE_API_BASE ?? '';
const cellStatus = { missing: '원천 결측', conflict: '원천 값 불일치', unverified: '원천 미확인' };
const examples = ['귀리_겉귀리_도정_생것 150g 단백질', '인삼_홍삼_말린것 150g 단백질 비교'];

function displayValue(value, status) {
    if (value == null) return cellStatus[status] || '계산할 수 없음';
    return String(value);
}

function FoodEvidence({ food, keys }) {
    const [record, setRecord] = useState(null);
    const [loading, setLoading] = useState(false);
    const [failed, setFailed] = useState(false);
    const href = api + (food.href || '/api/nutrition/foods/' + encodeURIComponent(food.foodCd));

    async function load() {
        if (record || loading) return;
        setFailed(false);
        setLoading(true);
        try {
            const { data } = await axios.get(href);
            setRecord(data);
        } catch {
            setFailed(true);
        } finally {
            setLoading(false);
        }
    }

    return <details className="rd-source" onToggle={e => { if (e.currentTarget.open) load(); }}>
        <summary>{food.foodNm} <small>{food.foodCd} · {food.basis}</small></summary>
        {loading && <p role="status">원문 불러오는 중…</p>}
        {failed && <p role="status">원문을 열 수 없습니다. <button type="button" onClick={load}>다시 열기</button></p>}
        {record && <>
            <p>{[record.original?.src_nm, record.original?.coo_nm, record.original?.crtr_ymd]
                .filter(value => value && value !== '해당없음').join(' · ')}</p>
            <dl className="rd-source-values">{keys.map(key => {
                const cell = record.cells[key];
                if (!cell) return null;
                const sourceText = cell.sourceText == null || cell.sourceText === '' ? '원천 표기 없음' : cell.sourceText;
                return <div key={key}><dt>{cell.label} ({cell.unit})</dt>
                    <dd>{sourceText}{cell.status !== 'observed' && ' · ' + (cellStatus[cell.status] || '미확인')}</dd></div>;
            })}</dl>
            <p className="rd-meta">원문 버전 {record.version}</p>
        </>}
        <div className="rd-actions"><a href={href} target="_blank" rel="noreferrer">전체 식품 원문</a>
            {record?.sourceUrl && <a href={record.sourceUrl} target="_blank" rel="noreferrer">공공데이터 출처</a>}</div>
    </details>;
}

function Answer({ result, onChoose, busy }) {
    const { message, status, choices = [], foods = [], rows = [], relation } = result;
    const compare = Boolean(relation && foods.length > 1);
    const passage = relation?.evidenceSource;
    const amount = result.amount != null && result.unit ? result.amount + result.unit : null;

    return <section className="rd-panel rd-answer" aria-label="질문 결과">
        <h2>{status === 'CHOOSE_FOOD' ? '식품 선택' : '답변'}</h2>
        <p role="status">{message}</p>
        {choices.length > 0 && <div className="rd-list rd-choices">{choices.map(food =>
            <button type="button" key={food.foodCd} disabled={busy} onClick={() => onChoose(food.foodCd)}>
                {food.foodNm}<small>{food.foodCd}</small>
            </button>)}</div>}
        {rows.length > 0 && <>
            <h3>{amount ? amount + ' 기준 영양값' : '영양값'}</h3>
            {compare && <p className="rd-meta">차이는 같은 양의 대상 식품에서 생것의 값을 뺀 결과입니다.</p>}
            <div className="rd-table-scroll"><table className="rd-values">
                <thead><tr><th scope="col">영양소</th><th scope="col">{foods[0]?.foodNm || '대상 식품'}</th>
                    {compare && <><th scope="col">{foods[1]?.foodNm || '생것'}</th><th scope="col">차이</th></>}
                </tr></thead>
                <tbody>{rows.map(row => <tr key={row.key}>
                    <th scope="row">{row.label} <small>({row.unit})</small></th>
                    <td>{displayValue(row.target, row.status)}</td>
                    {compare && <><td>{displayValue(row.candidate, row.candidateStatus)}</td>
                        <td>{displayValue(row.delta)}</td></>}
                </tr>)}</tbody>
            </table></div>
        </>}
        {relation && <section className="rd-evidence">
            <h3>비교 승인 근거 · {relation.verdict}</h3>
            <p>{relation.reason}</p>
            {relation.note && <p>검수 기록 · {relation.note}</p>}
            {passage?.quote && <blockquote>{passage.quote}</blockquote>}
            {passage?.summary && <p>{passage.summary}</p>}
            {passage?.url && <a href={passage.url} target="_blank" rel="noreferrer">
                {passage.title}{passage.locator && ' · ' + passage.locator}</a>}
            {passage?.limitations && <p className="rd-meta">{passage.limitations}</p>}
        </section>}
        {foods.length > 0 && <section><h3>계산에 사용한 식품 원문</h3>{foods.map(food =>
            <FoodEvidence key={food.href || food.foodCd} food={food} keys={rows.map(row => row.key)} />)}
        </section>}
    </section>;
}

export default function NutritionAnswers() {
    const [question, setQuestion] = useState('');
    const [submitted, setSubmitted] = useState('');
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);

    async function ask(text, foodCd) {
        const value = text.trim();
        if (!value || busy) return;
        setBusy(true);
        setQuestion(value);
        setSubmitted(value);
        setResult(null);
        setError('');
        try {
            const { data } = await axios.post(api + '/api/nutrition/answers', { question: value, foodCd });
            setResult(data);
        } catch (issue) {
            setError(issue.response?.data?.message || '질문을 처리할 수 없습니다. 서버 연결을 확인한 뒤 다시 시도해 주세요.');
        } finally {
            setBusy(false);
        }
    }

    return <main className="rd-workspace"><div className="rd-wrap rd-answer-wrap">
        <header className="rd-header"><Link to="/">Refine Dining</Link><h1>영양 질의응답</h1></header>
        <form className="rd-panel rd-form" onSubmit={e => { e.preventDefault(); ask(question); }}>
            <label htmlFor="nutrition-question">어떤 식품과 양이 궁금한가요?</label>
            <textarea id="nutrition-question" rows={2} required maxLength={300} value={question}
                disabled={busy} placeholder="식품명, 먹는 양, 궁금한 영양소를 입력하세요."
                onChange={e => { setQuestion(e.target.value); setResult(null); setError(''); }} />
            <div className="rd-question-actions"><div className="rd-example-group">{examples.map(example =>
                <button type="button" key={example} disabled={busy} className="rd-secondary"
                    onClick={() => ask(example)}>{example}</button>)}</div>
                <button type="submit" disabled={busy || !question.trim()}>{busy ? '조회 중…' : '질문하기'}</button>
            </div>
        </form>
        {error && <p role="alert" className="rd-status">{error}</p>}
        {result && <Answer key={submitted} result={result} busy={busy} onChoose={code => ask(submitted, code)} />}
    </div></main>;
}
