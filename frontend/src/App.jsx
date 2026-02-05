import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SearchPage from './pages/SearchPage.jsx';
import ComparePage from './pages/ComparePage.jsx';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<SearchPage />} />
                <Route path="/compare/:id" element={<ComparePage />} />
            </Routes>
        </Router>
    );
}

export default App;