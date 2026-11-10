import { BrowserRouter as Router, Link, Routes, Route } from 'react-router-dom';
import SearchPage from './pages/SearchPage.jsx';
import ComparePage from './pages/ComparePage.jsx';
import RelationReview from './pages/RelationReview.jsx';
import NutritionAnswers from './pages/NutritionAnswers.jsx';
import WeightPage from './pages/WeightPage.jsx';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<><nav style={{padding:'0.75rem 1rem',display:'flex',gap:'1rem',flexWrap:'wrap'}}><Link to="/nutrition">원문으로 영양 질문하기</Link><Link to="/weight">조리 후 중량 계산</Link></nav><SearchPage /></>} />
                <Route path="/weight" element={<WeightPage />} />
                <Route path="/compare/:id" element={<ComparePage />} />
                <Route path="/nutrition/review" element={<RelationReview />} />
                <Route path="/nutrition" element={<NutritionAnswers />} />
            </Routes>
        </Router>
    );
}

export default App;
