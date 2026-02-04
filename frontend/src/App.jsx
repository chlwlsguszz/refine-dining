import { useState } from 'react';
import axios from 'axios';

function App() {
    const [keyword, setKeyword] = useState('');
    const [foods, setFoods] = useState([]);
    const [expandedId, setExpandedId] = useState(null); // 어떤 항목이 펼쳐졌는지 저장

    const handleSearch = async () => {
        //if (!keyword || !keyword.trim()) {
        //    alert("검색어를 입력해주세요!");
        //    return;
        //}
        try {
            const response = await axios.get(`http://localhost:8080/api/food/search`, {
                params: { name: keyword.trim() }
            });
            setFoods(response.data);
            setExpandedId(null); // 검색 시 펼쳐진 항목 초기화
        } catch (error) {
            console.error("검색 실패:", error);
        }
    };

    // 항목 클릭 시 토글 로직
    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id);
    };

    return (
        <div style={{ padding: '20px', maxWidth: '600px', backgroundColor: '#1a1a1a', color: '#ffffff', minHeight: '100vh' }}>
            <h1 style={{ color: '#ffffff' }}>식품 영양 성분 검색</h1>

            {/* 검색창 영역 */}
            <div style={{ marginBottom: '20px' }}>
                <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    style={{ padding: '8px', backgroundColor: '#333', color: '#fff', border: '1px solid #555', borderRadius: '4px' }}
                    placeholder="식품 이름을 입력하세요"
                />
                <button onClick={handleSearch} style={{ padding: '8px 16px', marginLeft: '5px', cursor: 'pointer' }}>검색</button>
            </div>

            <ul style={{ listStyle: 'none', padding: 0 }}>
                {foods.map((food) => (
                    <li key={food.id} style={{ borderBottom: '1px solid #333', padding: '15px 0' }}>
                        {/* 부모 항목: 밝은 글씨 */}
                        <div
                            onClick={() => toggleExpand(food.id)}
                            style={{ cursor: 'pointer', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between', color: '#e0e0e0' }}
                        >
                            <span>{food.name}</span>
                            <span style={{ color: '#4daafc' }}>{food.calories || 0} kcal {expandedId === food.id ? '▲' : '▼'}</span>
                        </div>

                        {/* 자식 항목: 어두운 배경에 대비되는 색상 */}
                        {expandedId === food.id && food.cookingMethods && (
                            <ul style={{
                                backgroundColor: '#2d2d2d', // 진한 회색 배경
                                padding: '15px',
                                marginTop: '10px',
                                borderRadius: '8px',
                                border: '1px solid #444',
                                listStyle: 'none'
                            }}>
                                {food.cookingMethods.length > 0 ? (
                                    food.cookingMethods.map(child => (
                                        <li key={child.id} style={{ fontSize: '0.9em', marginBottom: '8px', color: '#bbbbbb' }}>
                                        <span style={{ color: '#ffcc00', fontWeight: 'bold' }}>
                                            [{child.cookingMethod || '일반'}]
                                        </span>
                                            <span style={{ marginLeft: '10px' }}>
                                            🔥 {child.calories}kcal | 💪 {child.protein}g | 🧂 {child.sodium}mg
                                        </span>
                                        </li>
                                    ))
                                ) : (
                                    <li style={{ color: '#777' }}>상세 조리법 정보가 없습니다.</li>
                                )}
                            </ul>
                        )}
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default App;