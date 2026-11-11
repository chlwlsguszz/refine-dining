import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

import { commonStyles } from '../styles/commonStyles';

function SearchPage() {
    const apiBase = import.meta.env.VITE_API_BASE ?? '';
    const [keyword, setKeyword] = useState('');
    const [foods, setFoods] = useState([]);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [hasSearched, setHasSearched] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
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
        if (loading) return;
        const currentPage = isNewSearch ? 0 : page;
        setLoading(true);
        setError(null);

        try {
            const response = await axios.get(`${apiBase}/api/food/search`, {
                params: {
                    name: keyword.trim(),
                    page: currentPage,
                    size: SIZE
                }
            });
            const newData = response.data;
            setHasSearched(true);

            if (isNewSearch) {
                setFoods(newData);
                setPage(1);
                setExpandedId(null);
            } else {
                setFoods(prev => [...prev, ...newData]);
                setPage(prev => prev + 1);
            }

            // 가져온 데이터가 SIZE보다 작으면 더 이상 데이터가 없는 것으로 판단
            setHasMore(newData.length === SIZE);
        } catch (err) {
            console.error('검색 실패:', err);
            setError(err.response?.data?.message || '식품 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.');
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.nativeEvent.isComposing) return;
        if (e.key === 'Enter') {
            handleSearch(true);
        }
    };

    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id);
    };

    return (
        <div style={styles.container}>
            <div style={styles.contentCard}>
                <header style={styles.header}>
                    <h1 style={styles.title}>Refine Dining</h1>
                    <p style={styles.subtitle}>식품을 검색하고 조리 방법별 영양소를 비교해보세요</p>
                </header>

                <div style={styles.searchBox}>
                    <input
                        type="text"
                        value={keyword}
                        onChange={(e) => setKeyword(e.target.value)}
                        onKeyDown={handleKeyDown}
                        style={styles.input}
                        placeholder="식품 이름 검색 (예: 감자, 삼겹살)"
                    />
                    <button
                        onClick={() => handleSearch(true)}
                        disabled={loading}
                        style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }}
                    >
                        {loading && page === 0 ? '검색 중...' : '검색'}
                    </button>
                </div>

                {error && <div style={styles.errorBox}>{error}</div>}

                <div style={styles.listContainer}>
                    {foods.length > 0 ? (
                        foods.map((food) => (
                            <div key={food.id} style={styles.foodItem}>
                                <div onClick={() => toggleExpand(food.id)} style={styles.parentRow}>
                                    <span style={styles.foodName}>{food.name}</span>
                                    <div style={styles.parentRight}>
                                        <span style={styles.mainKcal}>{food.calories ?? 0} kcal</span>
                                        <span style={styles.arrow}>{expandedId === food.id ? '▲' : '▼'}</span>
                                    </div>
                                </div>

                                {expandedId === food.id && (
                                    <div style={styles.childContainer}>
                                        {food.cookingMethods?.length > 0 ? (
                                            food.cookingMethods.map(child => (
                                                <div
                                                    key={child.id}
                                                    style={styles.childItem}
                                                    onClick={() => goToCompare(food, child)}
                                                >
                                                    <span style={styles.methodTag}>{child.cookingMethod || '일반'}</span>
                                                    <div style={styles.nutritionGrid}>
                                                        <span>🔥 {child.calories ?? 0} kcal</span>
                                                        <span>💪 {child.protein ?? 0}g</span>
                                                        <span>🥑 {child.fat ?? 0}g</span>
                                                    </div>
                                                    <span style={styles.compareHint}>비교하기 →</span>
                                                </div>
                                            ))
                                        ) : (
                                            <p style={styles.noData}>조리 방법 정보가 없습니다.</p>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        <div style={styles.emptyState}>
                            <p style={styles.emptyText}>
                                {hasSearched ? '검색 결과가 없습니다.' : '식품 이름을 검색해보세요'}
                            </p>
                            <p style={styles.emptyHint}>
                                {hasSearched
                                    ? '다른 검색어(예: 감자, 삼겹살, 닭고기)로 다시 검색해보세요'
                                    : '감자, 삼겹살, 닭가슴살 등을 입력해보세요'}
                            </p>
                        </div>
                    )}

                    {foods.length > 0 && hasMore && (
                        <button
                            onClick={() => handleSearch(false)}
                            disabled={loading}
                            style={styles.loadMoreButton}
                        >
                            {loading ? '불러오는 중...' : '더 보기'}
                        </button>
                    )}

                    {foods.length > 0 && !hasMore && (
                        <p style={styles.noMoreText}>모든 결과를 불러왔습니다</p>
                    )}
                </div>
            </div>
        </div>
    );
}

const styles = {
    container: {
        ...commonStyles.fullContainer,
        backgroundColor: '#f8f6f3',
        color: '#2d2a26',
    },
    contentCard: {
        width: '100%',
        maxWidth: '560px',
        display: 'flex',
        flexDirection: 'column',
    },
    header: { textAlign: 'center', marginBottom: '36px' },
    title: {
        fontSize: '1.8rem',
        fontWeight: 700,
        color: '#2d2a26',
        marginBottom: '8px',
        letterSpacing: '-0.03em',
    },
    subtitle: {
        color: '#8a857c',
        fontSize: '0.95rem',
    },
    searchBox: {
        display: 'flex',
        gap: '12px',
        width: '100%',
        marginBottom: '24px',
    },
    input: {
        flex: 1,
        padding: '14px 18px',
        borderRadius: '14px',
        border: '1px solid #e5e2dc',
        backgroundColor: '#fff',
        color: '#2d2a26',
        fontSize: '1rem',
        outline: 'none',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    },
    button: {
        padding: '14px 28px',
        borderRadius: '14px',
        border: 'none',
        backgroundColor: '#b94f16',
        color: '#fff',
        fontWeight: 600,
        cursor: 'pointer',
        fontSize: '0.95rem',
        boxShadow: '0 2px 8px rgba(185,79,22,0.18)',
        transition: 'opacity 0.2s',
    },
    buttonDisabled: {
        opacity: 0.65,
        cursor: 'not-allowed',
    },
    errorBox: {
        marginBottom: '16px',
        padding: '12px 16px',
        borderRadius: '12px',
        backgroundColor: '#fdf2f0',
        border: '1px solid #f2cfc9',
        color: '#c45c4a',
        fontSize: '0.9rem',
        textAlign: 'center',
    },
    listContainer: { display: 'flex', flexDirection: 'column', gap: '12px' },
    foodItem: {
        backgroundColor: '#fff',
        borderRadius: '16px',
        border: 'none',
        boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
        overflow: 'hidden',
    },
    parentRow: {
        padding: '18px 20px',
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        transition: 'background 0.2s',
    },
    foodName: { fontSize: '1.1rem', fontWeight: 600, color: '#2d2a26' },
    parentRight: { display: 'flex', alignItems: 'center', gap: '16px' },
    mainKcal: { color: '#b94f16', fontWeight: 700, fontSize: '0.95rem' },
    arrow: { color: '#b8b2a8', fontSize: '0.75rem' },
    childContainer: {
        backgroundColor: '#faf9f7',
        padding: '16px',
        borderTop: '1px solid #f0ede8',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
    },
    childItem: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 16px',
        backgroundColor: '#fff',
        borderRadius: '12px',
        border: '1px solid #f0ede8',
        cursor: 'pointer',
        transition: 'all 0.2s',
    },
    methodTag: {
        backgroundColor: '#fdf3e6',
        color: '#c4895a',
        padding: '5px 10px',
        borderRadius: '8px',
        fontSize: '0.8rem',
        fontWeight: 600,
    },
    nutritionGrid: {
        display: 'flex',
        gap: '16px',
        fontSize: '0.9rem',
        color: '#5c574f',
    },
    compareHint: {
        fontSize: '0.8rem',
        color: '#d4a574',
        fontWeight: 600,
    },
    noData: { textAlign: 'center', color: '#8a857c', fontSize: '0.9rem' },
    emptyState: {
        textAlign: 'center',
        padding: '60px 24px',
        backgroundColor: '#fff',
        borderRadius: '16px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
    },
    emptyText: { fontSize: '1rem', color: '#5c574f', margin: '0 0 8px' },
    emptyHint: { fontSize: '0.9rem', color: '#b8b2a8', margin: 0 },
    loadMoreButton: {
        marginTop: '16px',
        padding: '12px 20px',
        backgroundColor: 'transparent',
        border: '1px solid #d4a574',
        color: '#c4895a',
        borderRadius: '12px',
        cursor: 'pointer',
        fontWeight: 600,
        fontSize: '0.9rem',
        transition: 'all 0.2s',
    },
    noMoreText: {
        textAlign: 'center',
        color: '#8a857c',
        marginTop: '16px',
        fontSize: '0.9rem',
    },
};

export default SearchPage;
