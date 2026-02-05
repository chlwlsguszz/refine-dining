import { useState } from 'react';
import axios from 'axios';
import {useNavigate} from "react-router-dom";

function SearchPage() {
    const [keyword, setKeyword] = useState('');
    const [foods, setFoods] = useState([]);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [expandedId, setExpandedId] = useState(null);
    const navigate = useNavigate();

    const goToCompare = (parentFood, childFood) => {
        navigate(`/compare/${childFood.id}`, {
            state: {
                parentData: parentFood, // 부모 정보
                childData: childFood    // 선택한 자식 정보
            }
        });
    };
    const SIZE = 10; // 한 번에 가져올 개수

    const handleSearch = async (isNewSearch = true) => {
        const currentPage = isNewSearch ? 0 : page;

        try {
            const response = await axios.get(`http://localhost:8080/api/food/search`, {
                params: {
                    name: keyword.trim(),
                    page: currentPage,
                    size: SIZE
                }
            });
            const newData = response.data;

            if (isNewSearch) {
                setFoods(newData);
                setPage(1);
            } else {
                setFoods(prev => [...prev, ...newData]);
                setPage(prev => prev + 1);
            }

            // 가져온 데이터가 SIZE보다 작으면 더 이상 데이터가 없는 것으로 판단
            setHasMore(newData.length === SIZE);
            if (isNewSearch) setExpandedId(null);

        } catch (error) {
            console.error("검색 실패:", error);
        }
    };

    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id);
    };

    return (
        <div style={styles.container}>
            <div style={styles.contentCard}>
                <header style={styles.header}>
                    <h1 style={styles.title}>🥗 Refine Dining</h1>
                    <p style={styles.subtitle}>정제된 식품 영양 성분 데이터를 확인하세요</p>
                </header>

                {/* 검색 섹션 */}
                <div style={styles.searchBox}>
                    <input
                        type="text"
                        value={keyword}
                        onChange={(e) => setKeyword(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                        style={styles.input}
                        placeholder="식품 이름을 입력하세요 (예: 감자)"
                    />
                    <button onClick={() => handleSearch(true)} style={styles.button}>검색</button>
                </div>

                {/* 결과 리스트 */}
                <div style={styles.listContainer}>
                    {foods.length > 0 ? (
                        foods.map((food) => (
                            <div key={food.id} style={styles.foodItem}>
                                <div onClick={() => toggleExpand(food.id)} style={styles.parentRow}>
                                    <span style={styles.foodName}>{food.name}</span>
                                    <div style={styles.parentRight}>
                                        <span style={styles.mainKcal}>{food.calories || 0} <small>kcal</small></span>
                                        <span style={styles.arrow}>{expandedId === food.id ? '▲' : '▼'}</span>
                                    </div>
                                </div>

                                {expandedId === food.id && (
                                    <div style={styles.childContainer}>
                                        {food.cookingMethods?.length > 0 ? (
                                            food.cookingMethods.map(child => (
                                                <div
                                                    key={child.id}
                                                    style={{...styles.childItem, cursor: 'pointer'}}
                                                    onClick={() => goToCompare(food, child)} // 클릭 이벤트 연결
                                                >
                                                    <span style={styles.methodTag}>{child.cookingMethod || '일반'}</span>
                                                    <div style={styles.nutritionGrid}>
                                                        <span>🔥 {child.calories}kcal</span>
                                                        <span>💪 {child.protein}g</span>
                                                        <span>🧂 {child.sodium}mg</span>
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <p style={styles.noData}>상세 조리법 정보가 없습니다.</p>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        <div style={styles.emptyState}>
                            {keyword ? "검색 결과가 없습니다." : "무엇을 먹을지 검색해보세요!"}
                        </div>
                    )}

                    {/* 더 보기 버튼 */}
                    {foods.length > 0 && hasMore && (
                        <button
                            onClick={() => handleSearch(false)}
                            style={styles.loadMoreButton}
                        >
                            결과 더 보기 (10개)
                        </button>
                    )}

                    {foods.length > 0 && !hasMore && (
                        <p style={styles.noMoreText}>모든 결과를 불러왔습니다.</p>
                    )}

                </div>
            </div>
        </div>
    );
}

// 스타일 객체 분리 (가독성을 위해)
const styles = {
    container: {
        backgroundColor: '#121212',
        minHeight: '100vh',
        width: '100vw', // 화면 전체 너비
        display: 'flex',
        flexDirection: 'column', // 위에서 아래로 정렬
        alignItems: 'center',    // 가로축 중앙 정렬
        padding: '60px 20px',    // 상단 여유 공간
        fontFamily: "'Pretendard', -apple-system, sans-serif",
        boxSizing: 'border-box'
    },
    contentCard: {
        width: '100%',
        maxWidth: '600px', // 너무 넓어지지 않게 제한
        display: 'flex',
        flexDirection: 'column'
    },
    header: {
        textAlign: 'center',
        marginBottom: '50px' // 타이틀과 검색창 사이 간격
    },
    title: {
        fontSize: '2.5rem',
        color: '#ffffff',
        marginBottom: '10px'
    },
    subtitle: {
        color: '#888',
        fontSize: '1rem'
    },
    searchBox: {
        display: 'flex',
        gap: '12px',
        width: '100%',     // 부모 너비에 맞춤
        marginBottom: '40px',
        justifyContent: 'center' // 검색창 내부 요소들 중앙 정렬
    },
    input: {
        flex: 1,
        padding: '12px 16px',
        borderRadius: '12px',
        border: '1px solid #333',
        backgroundColor: '#1e1e1e',
        color: '#fff',
        fontSize: '16px',
        outline: 'none',
        transition: 'border 0.2s',
    },
    button: {
        padding: '12px 24px',
        borderRadius: '12px',
        border: 'none',
        backgroundColor: '#4daafc',
        color: '#fff',
        fontWeight: 'bold',
        cursor: 'pointer',
        transition: 'transform 0.1s',
    },
    listContainer: {
        display: 'flex',
        flexDirection: 'column',
        gap: '15px'
    },
    foodItem: {
        backgroundColor: '#1e1e1e',
        borderRadius: '16px',
        overflow: 'hidden',
        border: '1px solid #2d2d2d'
    },
    parentRow: {
        padding: '20px',
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        transition: 'background 0.2s',
    },
    foodName: {
        fontSize: '1.1rem',
        fontWeight: '600',
        color: '#e0e0e0'
    },
    parentRight: {
        display: 'flex',
        alignItems: 'center',
        gap: '15px'
    },
    mainKcal: {
        color: '#4daafc',
        fontWeight: '700'
    },
    arrow: {
        color: '#555',
        fontSize: '0.8rem'
    },
    childContainer: {
        backgroundColor: '#262626',
        padding: '15px',
        borderTop: '1px solid #333',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
    },
    childItem: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px',
        backgroundColor: '#2d2d2d',
        borderRadius: '10px'
    },
    methodTag: {
        backgroundColor: '#ffcc0022',
        color: '#ffcc00',
        padding: '4px 8px',
        borderRadius: '6px',
        fontSize: '0.8rem',
        fontWeight: 'bold'
    },
    nutritionGrid: {
        display: 'flex',
        gap: '12px',
        fontSize: '0.85rem',
        color: '#bbb'
    },
    noData: {
        textAlign: 'center',
        color: '#666',
        fontSize: '0.9rem'
    },
    emptyState: {
        textAlign: 'center',
        marginTop: '50px',
        color: '#555'
    },
    loadMoreButton: {
        marginTop: '20px',
        padding: '12px',
        backgroundColor: 'transparent',
        border: '1px solid #4daafc',
        color: '#4daafc',
        borderRadius: '12px',
        cursor: 'pointer',
        fontWeight: 'bold'
    },
    noMoreText: {
        textAlign: 'center',
        color: '#555',
        marginTop: '20px',
        fontSize: '0.9rem'
    }
};

export default SearchPage;