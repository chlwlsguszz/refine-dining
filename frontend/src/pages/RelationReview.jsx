import { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './nutrition.css';

const api = import.meta.env.VITE_API_BASE ?? '';
const queuePath = api + '/api/admin/nutrition/proposals';
const statusNames = { PENDING: '검수 대기', APPROVED: '승인', HELD: '보류 확정' };

function SourceLink({ code, version, children }) {
    const query = version ? '?version=' + encodeURIComponent(version) : '';
    return <a href={api + '/api/nutrition/foods/' + encodeURIComponent(code) + query}
        target="_blank" rel="noreferrer">{children || code}</a>;
}

function ReviewDetail({ proposal, busy, onDecide }) {
    const [reviewer, setReviewer] = useState('');
    const [note, setNote] = useState('');
    const source = proposal.evidenceSource;
    const pending = proposal.reviewStatus === 'PENDING';
    const rawAvailable = Boolean(proposal.selectedCd);

    return <section className="rd-panel rd-review-detail" aria-label="제안 상세">
        <div className="rd-meta">{statusNames[proposal.reviewStatus]} · {proposal.verdict}</div>
        <h2>{proposal.targetQuote}</h2>
        <SourceLink code={proposal.targetCd} version={proposal.version} />
        <p>{proposal.reason}</p>
        {source && <section className="rd-evidence">
            <h3>가공 근거</h3>
            {source.quote && <blockquote>{source.quote}</blockquote>}
            {source.summary && <p>{source.summary}</p>}
            <a href={source.url} target="_blank" rel="noreferrer">{source.title}{source.locator && ' · ' + source.locator}</a>
            {source.limitations && <p className="rd-meta">{source.limitations}</p>}
        </section>}
        <h3>생것 후보 원문</h3>
        <ol className="rd-candidates">{proposal.candidates.map(({ record, reason }) =>
            <li key={record.foodCd}>
                <SourceLink code={record.foodCd} version={proposal.version}>{record.foodNm}</SourceLink>
                {record.foodCd === proposal.selectedCd && <strong className="rd-flag">제안된 후보</strong>}
                <div className="rd-meta">{[record.foodCd, record.basis, record.country, record.region, record.month]
                    .filter(v => v && v !== '해당없음').join(' · ')}</div>
                {reason && <small>{reason}</small>}
            </li>)}</ol>
        {pending ? <form className="rd-form" onSubmit={event => {
            event.preventDefault();
            const decision = event.nativeEvent.submitter?.value;
            if (busy || !reviewer.trim() || !note.trim() || !decision || (decision === 'APPROVED' && !rawAvailable)) return;
            onDecide(proposal, { decision, reviewer: reviewer.trim(), note: note.trim() });
        }}>
            <h3>검수 기록</h3>
            <label>검수자<input required maxLength={80} autoComplete="off"
                value={reviewer} onChange={e => setReviewer(e.target.value)} /></label>
            <label>판단 근거<textarea required maxLength={1000} rows={3} value={note}
                placeholder="원문에서 확인한 품종·부위·기준량 또는 부족한 자료"
                onChange={e => setNote(e.target.value)} /></label>
            <div className="rd-actions">
                {rawAvailable && <button type="submit" value="APPROVED" disabled={busy}>제안된 관계 승인</button>}
                <button className="rd-secondary" type="submit" value="HELD" disabled={busy}>보류 확정</button>
            </div>
        </form> : <section className="rd-evidence">
            <h3>{statusNames[proposal.reviewStatus]} 기록</h3>
            {proposal.reviewer && <p>{proposal.reviewer} {proposal.decidedAt}</p>}
            {proposal.note && <p>{proposal.note}</p>}
        </section>}
    </section>;
}

export default function RelationReview() {
    const [key, setKey] = useState('');
    const [proposals, setProposals] = useState(null);
    const [selection, setSelection] = useState(null);
    const [filter, setFilter] = useState('PENDING');
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState('');
    const headers = { 'X-Admin-Key': key };
    const visible = (proposals || []).filter(p => filter === 'all' || p.reviewStatus === filter)
        .sort((a, b) => Number(Boolean(b.selectedCd)) - Number(Boolean(a.selectedCd)));
    const active = visible.find(p => p.reviewId === selection) ?? visible[0];

    async function load() {
        const { data } = await axios.get(queuePath, { headers });
        setProposals(data);
    }

    async function unlock(event) {
        event.preventDefault();
        if (!key || busy) return;
        setBusy(true);
        setMessage('');
        try {
            await load();
        } catch (error) {
            setMessage(error.response?.data?.message || '검수 목록을 열 수 없습니다. 관리자 키와 서버 상태를 확인하세요.');
        } finally {
            setBusy(false);
        }
    }

    async function decide(proposal, body) {
        setBusy(true);
        setMessage('');
        try {
            const { data } = await axios.post(queuePath + '/' + encodeURIComponent(proposal.reviewId), body, { headers });
            // Reflect the server acknowledgment even if the subsequent list refresh fails.
            setProposals(items => items.map(item => item.reviewId === proposal.reviewId ? data : item));
            setMessage(proposal.targetQuote + ' · ' + statusNames[body.decision] + ' 저장됨');
            await load();
        } catch (error) {
            try { await load(); } catch { /* The user may re-open the queue to retry. */ }
            setMessage(error.response?.data?.message || '최신 상태를 확인할 수 없습니다. 검수 목록을 다시 열어 확인하세요.');
        } finally {
            setBusy(false);
        }
    }

    return <main className="rd-workspace"><div className="rd-wrap">
        <header className="rd-header"><Link to="/">Refine Dining</Link><h1>비교 관계 검수</h1></header>
        {!proposals ? <form className="rd-panel rd-form rd-login" onSubmit={unlock}>
            <label>관리자 키<input type="password" value={key} required autoComplete="off"
                onChange={e => setKey(e.target.value)} /></label>
            <button type="submit" disabled={busy}>{busy ? '열고 있습니다…' : '검수 목록 열기'}</button>
        </form> : <>
            <div className="rd-toolbar"><label>상태 <select value={filter} disabled={busy}
                onChange={e => setFilter(e.target.value)}>
                {Object.entries({ ...statusNames, all: '전체' }).map(([value, name]) =>
                    <option key={value} value={value}>{name}</option>)}
            </select></label><span>{visible.length}건</span><button type="button" className="rd-secondary" disabled={busy}
                onClick={() => { setProposals(null); setKey(''); setMessage(''); }}>목록 닫기</button></div>
            {visible.length > 0 ? <div className="rd-grid">
                <nav className="rd-list" aria-label="검수 대상">{visible.map(p =>
                    <button type="button" disabled={busy} aria-pressed={active.reviewId === p.reviewId}
                        key={p.reviewId} onClick={() => setSelection(p.reviewId)}>
                        {p.targetQuote}<small>{p.targetCd} · {p.verdict}</small>
                    </button>)}</nav>
                <ReviewDetail key={active.reviewId} proposal={active} busy={busy} onDecide={decide} />
            </div> : <p>이 상태의 제안이 없습니다.</p>}
        </>}
        <p role="status" className="rd-status">{message}</p>
    </div></main>;
}
