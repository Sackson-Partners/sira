import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Unauthorized: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="text-center">
        <div className="text-6xl text-red-500 font-bold mb-4">403</div>
        <h1 className="text-white text-2xl font-bold mb-2">Access Denied</h1>
        <p className="text-gray-400 mb-2">You don&apos;t have permission to view this page.</p>
        {user && (
          <p className="text-gray-500 text-sm mb-6">
            Your role: <span className="text-gray-300 font-medium">{user.role}</span>
          </p>
        )}
        <button
          onClick={() => navigate('/dashboard')}
          className="bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-6 rounded-lg text-sm"
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  );
};

export default Unauthorized;
