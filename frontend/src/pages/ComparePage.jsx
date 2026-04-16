import { useState } from 'react';
import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';
import { commonStyles } from '../styles/commonStyles';

function ComparePage() {
    const apiBase = import.meta.env.VITE_API_BASE ?? '';
    const location = useLocation();
    const navigate = useNavigate();
    const { parentData, childData } = location.state || {};

    const [leftWeight, setLeftWeight] = useState(100);
    const [rightWeight, setRightWeight] = useState(100);
    const [aiLoading, setAiLoading] = useState(false);
    const [aiError, setAiError] = useState(null);
    const [aiPrediction, setAiPrediction] = useState(null);

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
        if (v === '') { setLeftWeight(''); return; }
        const num = Number(v);
        if (!isNaN(num)) setLeftWeight(num);
    };

    // 오른쪽 핸들러 (추가)
    const handleRightWeightChange = (v) => {
        if (v === '') { setRightWeight(''); return; }
        const num = Number(v);
        if (!isNaN(num)) setRightWeight(num);
    };

    const cookingVerbMap = {
        '구운것': '구우면', '삶은것': '삶으면', '튀긴것': '튀기면', '찐것': '쪄면',
        '데친것': '데치면', '볶은것': '볶으면', '조린것': '조리면',
        '전자레인지로 가열한것': '전자레인지로 가열하면', '생것': '그대로 두면',
    };
    const getCookingVerb = () => cookingVerbMap[childData?.cookingMethod] || '조리하면';

    const handleAiRecommend = async () => {
        if (!parentData?.name || leftWeight === '' || leftWeight <= 0) return;
        setAiError(null);
        setAiPrediction(null);
        setAiLoading(true);
        try {
            const res = await axios.post(`${apiBase}/api/weight/predict`, {
                foodName: parentData.name,
                cookingMethod: childData?.cookingMethod ?? null,
                baseWeight: Number(leftWeight),
            });
            const predicted = Math.round(res.data.predictedWeight * 10) / 10;
            setAiPrediction({ foodName: parentData.name, baseWeight: leftWeight, predicted, cookingVerb: getCookingVerb() });
        } catch (err) {
            setAiError(err.response?.data?.message || err.message || 'AI 예측에 실패했습니다.');
        } finally {
            setAiLoading(false);
        }
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
                        <label style={styles.weightControlLabel}>중량 (g)</label>
                        <input
                            type="number"
                            value={rightWeight}
                            onChange={(e) => handleRightWeightChange(e.target.value)}
                            onBlur={() => { if (rightWeight === '') setRightWeight(0); }}
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
                                        <span style={{...styles.diff, color: isPlus ? '#c45c4a' : '#6b9b6e'}}>
                                            {isPlus ? '+' : ''}{diff}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            <div style={styles.aiSection}>
                <button
                    type="button"
                    style={{...styles.aiButton, ...(aiLoading ? styles.aiButtonDisabled : {})}}
                    onClick={handleAiRecommend}
                    disabled={aiLoading}
                >
                    {aiLoading ? '예측 중...' : '조리 후 예상 중량 알려주기'}
                </button>
                {aiPrediction && (
                    <div style={styles.aiPredictionCard}>
                        {aiPrediction.foodName} {aiPrediction.baseWeight}g을(를) {aiPrediction.cookingVerb} 약 <strong>{aiPrediction.predicted}g</strong>이 될 것으로 예상됩니다.
                    </div>
                )}
                {aiError && <div style={styles.aiError}>{aiError}</div>}
            </div>
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
    cardLeft: { borderTop: '4px solid #6b9b6e' },
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
    aiSection: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        marginTop: '40px',
        gap: '12px',
    },
    aiButton: {
        padding: '12px 24px',
        borderRadius: '14px',
        border: 'none',
        backgroundColor: '#d4a574',
        color: '#fff',
        cursor: 'pointer',
        fontSize: '0.95rem',
        fontWeight: 600,
        boxShadow: '0 2px 8px rgba(212,165,116,0.35)',
        transition: 'all 0.2s',
    },
    aiButtonDisabled: { opacity: 0.7, cursor: 'not-allowed' },
    aiPredictionCard: {
        padding: '16px 24px',
        backgroundColor: '#fdf8f2',
        border: '1px solid #eeddc9',
        borderRadius: '14px',
        color: '#5c574f',
        fontSize: '0.95rem',
        maxWidth: '480px',
        textAlign: 'center',
    },
    aiError: {
        color: '#c45c4a',
        fontSize: '0.9rem',
    },
};

export default ComparePage;