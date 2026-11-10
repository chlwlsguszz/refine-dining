import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import CookingYieldPanel from '../components/CookingYieldPanel';

const api = import.meta.env.VITE_API_BASE ?? '';
const custom = '__direct_input__';

export default function WeightPage() {
    const [records, setRecords] = useState(null);
    const [food, setFood] = useState('');
    const [method, setMethod] = useState('');
    const [typedFood, setTypedFood] = useState('');
    const [typedMethod, setTypedMethod] = useState('');
    const [baseWeight, setBaseWeight] = useState('200');
    const [loadError, setLoadError] = useState('');
    useEffect(() => {
        const abort = new AbortController();
        axios.get(api + '/api/weight/options', { signal: abort.signal })
            .then(({ data }) => { if (!abort.signal.aborted) setRecords(data); })
            .catch(() => {
                if (abort.signal.aborted) return;
                setLoadError('목록을 불러오지 못했습니다. 식품과 조리법을 직접 입력해 주세요.');
                setRecords([]);
            });
        return () => abort.abort();
    }, []);

    const foods = [...new Set((records || []).map(row => row.foodLabel))];
    const typeFood = records?.length === 0 || food === custom;
    const typeMethod = typeFood || method === custom;
    const methods = [...new Set((records || []).filter(r => r.foodLabel === food).map(r => r.methodLabel))];
    const foodName = (typeFood ? typedFood : food).trim();
    const cookingMethod = (typeMethod ? typedMethod : method).trim();
    function changeFood(value) {
        setFood(value);
        setMethod('');
        setTypedFood('');
        setTypedMethod('');
    }

    return <main className="yield-page"><div className="yield-wrap">
        <header><nav><Link to="/">Refine Dining</Link><Link to="/nutrition">영양 질의응답</Link></nav>
            <h1>조리 후 중량 계산</h1>
            <p>식품과 조리법을 고르면 해당 실험의 평균 수율로 조리 후 중량을 계산합니다.</p>
        </header>
        <div className="yield-card">
            {loadError && <p role="alert" className="yield-error">{loadError}</p>}
            <div className="yield-fields">
                {foods.length > 0 && <label className="yield-field">식품·부위
                    <select value={food} onChange={e => changeFood(e.target.value)}>
                        <option value="">식품 선택</option>
                        {foods.map(name => <option key={name}>{name}</option>)}
                        <option value={custom}>식품명 직접 입력</option>
                    </select>
                </label>}
                {typeFood && <label className="yield-field">식품명 직접 입력
                    <input value={typedFood} maxLength={200} onChange={e => setTypedFood(e.target.value)} />
                </label>}
                {!typeFood && <label className="yield-field">조리법
                    <select value={method} disabled={!food} onChange={e => setMethod(e.target.value)}>
                        <option value="">조리법 선택</option>
                        {methods.map(name => <option key={name}>{name}</option>)}
                        <option value={custom}>조리법 직접 입력</option>
                    </select>
                </label>}
                {typeMethod && <label className="yield-field">조리법 직접 입력
                    <input value={typedMethod} maxLength={100} onChange={e => setTypedMethod(e.target.value)} />
                </label>}
                <label className="yield-field">조리 전 중량 (g)
                    <input type="number" min="0" step="any" value={baseWeight} onChange={e => setBaseWeight(e.target.value)} />
                </label>
            </div>
            {records === null && <p role="status">실측 자료를 불러오는 중…</p>}
            <CookingYieldPanel key={JSON.stringify([foodName, cookingMethod, baseWeight])}
                foodName={foodName} cookingMethod={cookingMethod} baseWeight={baseWeight}
                onSuggestedFood={name => {
                    setFood(custom);
                    setTypedFood(name);
                    setTypedMethod(cookingMethod);
                }} />
        </div>
    </div></main>;
}
