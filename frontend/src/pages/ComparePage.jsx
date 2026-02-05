import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

function ComparePage() {
    const location = useLocation();
    const navigate = useNavigate();
    const { parentData, childData } = location.state || {};

    // 중량 상태 (기본값 100g)
    const [leftWeight, setLeftWeight] = useState(100);
    const [rightWeight, setRightWeight] = useState(100);

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

    return (
        <div style={styles.container}>
            <header style={styles.header}>
                <button onClick={() => navigate(-1)} style={styles.backButton}>← 이전</button>
                <h1 style={styles.mainTitle}>중량별 영양소 비교</h1>
            </header>

            <div style={styles.comparisonWrapper}>
                {/* 왼쪽 카드: 부모 */}
                <div style={styles.card}>
                    <div style={styles.weightControl}>
                        <label>중량 설정 (g)</label>
                        <input
                            type="number"
                            value={leftWeight}
                            onChange={(e) => handleLeftWeightChange(e.target.value)}
                            onBlur={() => { if (leftWeight === '') setLeftWeight(0); }} // 포커스가 나갈 때 비어있으면 0으로 채워주는 안전장치
                            style={styles.weightInput}
                        />
                    </div>
                    <h2 style={styles.foodTitle}>{parentData.name}</h2>
                    <div style={styles.nutrientList}>
                        {nutrients.map(n => (
                            <div key={n.key} style={styles.nutrientRow}>
                                <span>{n.label}</span>
                                <strong>{calculate(parentData[n.key], leftWeight)} {n.unit}</strong>
                            </div>
                        ))}
                    </div>
                </div>

                <div style={styles.vs}>VS</div>

                {/* 오른쪽 카드: 자식 */}
                <div style={{...styles.card, borderColor: '#4daafc'}}>
                    <div style={styles.weightControl}>
                        <label>중량 설정 (g)</label>
                        <input
                            type="number"
                            value={rightWeight}
                            onChange={(e) => handleRightWeightChange(e.target.value)} // 오른쪽 핸들러 연결
                            onBlur={() => { if (rightWeight === '') setRightWeight(0); }}
                            style={styles.weightInput}
                        />
                    </div>
                    <h2 style={styles.foodTitle}>{childData.name}</h2>
                    <div style={styles.nutrientList}>
                        {nutrients.map(n => {
                            const leftVal = calculate(parentData[n.key], leftWeight);
                            const rightVal = calculate(childData[n.key], rightWeight);
                            const diff = (rightVal - leftVal).toFixed(1);
                            const isPlus = diff > 0;

                            return (
                                <div key={n.key} style={styles.nutrientRow}>
                                    <span>{n.label}</span>
                                    <div>
                                        <strong style={{color: '#4daafc'}}>{rightVal} {n.unit}</strong>
                                        <span style={{...styles.diff, color: isPlus ? '#ff4d4d' : '#4dfc8f'}}>
                                            ({isPlus ? '+' : ''}{diff})
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

const styles = {
    container: { backgroundColor: '#121212', minHeight: '100vh', padding: '40px', color: '#fff' },
    header: { maxWidth: '1000px', margin: '0 auto 40px', display: 'flex', alignItems: 'center', gap: '20px' },
    backButton: { backgroundColor: '#333', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer' },
    mainTitle: { fontSize: '1.5rem', margin: 0 },
    comparisonWrapper: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
        gap: '20px',
        maxWidth: '1200px',
        margin: '0 auto'
    },
    card: {
        flex: 1,
        backgroundColor: '#1e1e1e',
        borderRadius: '20px',
        padding: '30px',
        border: '2px solid #333',
        position: 'relative'
    },
    badge: {
        position: 'absolute', top: '-12px', left: '20px',
        backgroundColor: '#555', padding: '4px 12px', borderRadius: '20px', fontSize: '0.8rem'
    },
    foodTitle: { fontSize: '1.8rem', marginBottom: '30px', textAlign: 'center' },
    vs: { fontSize: '2rem', fontWeight: 'bold', color: '#444', alignSelf: 'center' },
    nutrientList: { display: 'flex', flexDirection: 'column', gap: '20px' },
    nutrientRow: {
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        paddingBottom: '10px', borderBottom: '1px solid #2d2d2d'
    },
    diff: { fontSize: '0.85rem', marginLeft: '8px', fontWeight: 'bold' } ,
    weightControl: {
        marginBottom: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        alignItems: 'center',
        padding: '15px',
        backgroundColor: '#262626',
        borderRadius: '12px'
    },
    weightInput: {
        width: '80px',
        padding: '8px',
        borderRadius: '8px',
        border: '1px solid #444',
        backgroundColor: '#121212',
        color: '#fff',
        textAlign: 'center',
        fontSize: '1.1rem',
        fontWeight: 'bold',
        outline: 'none'
    },
};

export default ComparePage;