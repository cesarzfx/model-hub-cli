import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import Login from './pages/Login';
import Models from './pages/Models';
import ModelDetail from './pages/ModelDetail';
import SubmitModel from './pages/SubmitModel';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/models"
            element={
              <ProtectedRoute>
                <Models />
              </ProtectedRoute>
            }
          />
          <Route
            path="/models/:id"
            element={
              <ProtectedRoute>
                <ModelDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/submit"
            element={
              <ProtectedRoute>
                <SubmitModel />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/models" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
