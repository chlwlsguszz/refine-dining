import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import CookingYieldPanel from '../components/CookingYieldPanel';
import { commonStyles } from '../styles/commonStyles';

function ComparePage() {
    const location = useLocation();
    const navigate = useNavigate();
    const { parentData, childData } = location.state || {};

    const [leftWeight, setLeftWeight] = useState(100);
    const [manualWeight, setManualWeight] = useState(100);
    const [estimate, setEstimate] = useState(null);
    const foodCd = /^R\d{3}-\d{9}-\d{4}$/.test(parentData?.foodCd) ? parentData.foodCd : undefined;
    // Refined "구운것" groups pan, grill and oven; preserve the protocol printed in the original food name.
    const cookingMethod = childData?.name?.split('_').find(field => field.startsWith(childData.cookingMethod + '('))
        ?? childData?.cookingMethod;
    const yieldKey = JSON.stringify([foodCd, parentData?.name, childData?.id, childData?.name, cookingMethod, leftWeight]);
    const usingEstimate = estimate?.key === yieldKey;
    const rightWeight = usingEstimate ? estimate.weight : manualWeight;

    if (!parentData || !childData) return <div style={styles.container}>데이터 없음</div>;

    // 실시간 영양소 계산 함수
    const calculate = (value, weight) => {
        if (!value || !weight || weight === '') return '0.0';
        return ((value * weight) / 100).toFixed(1);
    };

    const nutrients = [
        { label: '🔥 칼로리', key: 'calories', unit: 'kcal' },
        { label: '💪 단백질', key: 'protein', unit: 'g' },
        { label: '🥑 지방', key: 'fat', unit: 'g' },
        { label: '🧂 나트륨', key: 'sodium', unit: 'mg' },
        { label: '🍞 탄수화물', key: 'carbohydrate', unit: 'g' },
        { label: '🍬 당류', key: 'sugar', unit: 'g' },  // 추가
    ];

    // 왼쪽 핸들러
    const handleLeftWeightChange = (v) => {
        setEstimate(null);
        if (v === '') { setLeftWeight(''); return; }
        const num = Number(v);
        if (!isNaN(num)) setLeftWeight(num);
    };

    // 오른쪽 핸들러 (추가)
    const handleRightWeightChange = (v) => {
        setEstimate(null);
        if (v === '') { setManualWeight(''); return; }
        const num = Number(v);
        if (!isNaN(num)) setManualWeight(num);
    };

    return (
        <div style={styles.container}>
            <header style={styles.header}>
                <button onClick={() => navigate(-1)} style={styles.backButton}>← 이전</button>
                <h1 style={styles.mainTitle}>영양소 비교</h1>
            </header>

            <div style={styles.comparisonWrapper}>
                <div style={{...styles.card, ...styles.cardLeft}}>
                    <span style={styles.cardLabel}>원재료</span>
                    <h2 style={styles.foodTitle}>{parentData.name}</h2>
                    <div style={styles.weightControl}>
                        <label style={styles.weightControlLabel}>중량 (g)</label>
                        <input
                            type="number"
                            value={leftWeight}
                            onChange={(e) => handleLeftWeightChange(e.target.value)}
                            onBlur={() => { if (leftWeight === '') setLeftWeight(0); }}
                            style={styles.weightInput}
                        />
                    </div>
                    <div style={styles.nutrientList}>
                        {nutrients.map(n => (
                            <div key={n.key} style={styles.nutrientRow}>
                                <span style={styles.nutrientLabel}>{n.label}</span>
                                <strong>{calculate(parentData[n.key], leftWeight)} {n.unit}</strong>
                            </div>
                        ))}
                    </div>
                </div>

                <div style={styles.connector}>
                    <span style={styles.connectorArrow}>→</span>
                </div>

                <div style={{...styles.card, ...styles.cardRight}}>
                    <span style={styles.cardLabel}>조리 후</span>
                    <h2 style={styles.foodTitle}>{childData.name}</h2>
                    <div style={styles.weightControl}>
                        <label htmlFor="yield-cooked-weight" style={styles.weightControlLabel}>
                            비교 중량 (g){usingEstimate ? ' · 실측 수율 추정값' : ''}
                        </label>
                        <input
                            id="yield-cooked-weight"
                            type="number"
                            value={rightWeight}
                            onChange={(e) => handleRightWeightChange(e.target.value)}
                            onBlur={() => { if (rightWeight === '') setManualWeight(0); }}
                            style={styles.weightInput}
                        />
                    </div>
                    <div style={styles.nutrientList}>
                        {nutrients.map(n => {
                            const leftVal = calculate(parentData[n.key], leftWeight);
                            const rightVal = calculate(childData[n.key], rightWeight);
                            const diff = (rightVal - leftVal).toFixed(1);
                            const isPlus = diff > 0;
                            return (
                                <div key={n.key} style={styles.nutrientRow}>
                                    <span style={styles.nutrientLabel}>{n.label}</span>
                                    <div style={styles.nutrientValue}>
                                        <strong>{rightVal} {n.unit}</strong>
                                        <span style={{...styles.diff, color: isPlus ? '#c45c4a' : '#b94f16'}}>
                                            {isPlus ? '+' : ''}{diff}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            <section className="yield-compare">
                <h2>조리 후 예상 중량</h2>
                <p>원재료와 조리 조건에 맞는 실측 수율을 찾아 비교에 적용할 수 있습니다.</p>
                <CookingYieldPanel key={yieldKey} foodName={parentData.name} foodCd={foodCd} cookingMethod={cookingMethod}
                    baseWeight={leftWeight} manualInputId="yield-cooked-weight" onChangeCondition={() => setEstimate(null)}
                    onApply={weight => setEstimate({ key: yieldKey, weight })} />
            </section>
        </div>
    );
}

const styles = {
    container: {
        ...commonStyles.fullContainer,
        padding: '40px 24px 60px',
        backgroundColor: '#f8f6f3',
        color: '#2d2a26',
    },
    header: { width: '100%', maxWidth: '1000px', margin: '0 auto 32px', display: 'flex', alignItems: 'center', gap: '16px' },
    backButton: {
        backgroundColor: '#fff',
        color: '#5c574f',
        border: '1px solid #e5e2dc',
        padding: '10px 18px',
        borderRadius: '12px',
        cursor: 'pointer',
        fontSize: '0.95rem',
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        transition: 'all 0.2s',
    },
    mainTitle: { fontSize: '1.4rem', fontWeight: 600, margin: 0, letterSpacing: '-0.02em', color: '#2d2a26' },
    comparisonWrapper: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'stretch',
        gap: '20px',
        maxWidth: '900px',
        margin: '0 auto',
    },
    card: {
        flex: 1,
        padding: '28px 24px',
        position: 'relative',
        borderRadius: '20px',
        backgroundColor: '#fff',
        border: 'none',
        boxShadow: '0 4px 20px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: '340px',
    },
    cardLeft: { borderTop: '4px solid #c76325' },
    cardRight: { borderTop: '4px solid #d4a574' },
    cardLabel: {
        fontSize: '0.7rem',
        fontWeight: 600,
        letterSpacing: '0.1em',
        color: '#8a857c',
        marginBottom: '12px',
        textTransform: 'uppercase',
    },
    foodTitle: {
        fontSize: '1.5rem',
        fontWeight: 600,
        marginBottom: '20px',
        textAlign: 'left',
        minHeight: '2.4em',
        lineHeight: 1.35,
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
        letterSpacing: '-0.02em',
        color: '#2d2a26',
    },
    connector: {
        width: '48px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
    },
    connectorArrow: {
        fontSize: '1.5rem',
        color: '#b8b2a8',
        fontWeight: 300,
    },
    nutrientList: { display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 'auto' },
    nutrientRow: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 14px',
        backgroundColor: '#faf9f7',
        borderRadius: '12px',
        border: '1px solid #f0ede8',
    },
    nutrientLabel: { fontSize: '0.9rem', color: '#5c574f' },
    nutrientValue: { display: 'flex', alignItems: 'center', gap: '10px' },
    diff: { fontSize: '0.8rem', fontWeight: 600 },
    weightControl: {
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        marginBottom: '20px',
    },
    weightControlLabel: {
        fontSize: '0.8rem',
        color: '#8a857c',
    },
    weightInput: {
        width: '88px',
        padding: '10px 12px',
        borderRadius: '12px',
        border: '1px solid #e5e2dc',
        backgroundColor: '#faf9f7',
        color: '#2d2a26',
        textAlign: 'center',
        fontSize: '1.1rem',
        fontWeight: 600,
        outline: 'none',
    },

};

export default ComparePage;
