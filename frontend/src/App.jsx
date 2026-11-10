import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SearchPage from './pages/SearchPage.jsx';
import ComparePage from './pages/ComparePage.jsx';
import RelationReview from './pages/RelationReview.jsx';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<SearchPage />} />
                <Route path="/compare/:id" element={<ComparePage />} />
                <Route path="/nutrition/review" element={<RelationReview />} />
            </Routes>
        </Router>
    );
}

export default App;
