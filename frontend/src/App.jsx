import { useState } from 'react'
import axios from 'axios'

function App() {
    const [keyword, setKeyword] = useState('');
    const [foods, setFoods] = useState([]);

    const handleSearch = async () => {
        try {
            // 스프링 부트 API 호출
            const response = await axios.get(`http://localhost:8080/api/food/search`, {
                params: { name: keyword }
            });
            setFoods(response.data); // 받아온 데이터를 상태에 저장
        } catch (error) {
            console.error("데이터를 가져오는데 실패했습니다:", error);
            alert("백엔드 서버가 켜져 있는지 확인하세요!");
        }
    };

    return (
        <div style={{ padding: '20px' }}>
            <h1>식품 영양 성분 검색</h1>
            <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="식품 이름을 입력하세요"
            />
            <button onClick={handleSearch}>검색</button>

            <hr />

            <ul>
                {foods.map((food) => (
                    <li key={food.id}>
                        <strong>{food.foodNm}</strong> - 에너기: {food.energies}kcal, 단백질: {food.protein}g
                    </li>
                ))}
            </ul>
            {foods.length === 0 && <p>검색 결과가 없습니다.</p>}
        </div>
    )
}

export default App