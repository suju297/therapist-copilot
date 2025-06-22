// src/App.tsx - With session lifecycle demo
import React, { useState } from 'react';
import LiveSessionDashboard from './components/LiveSessionDashboard';
import SimpleSessionTest from './components/SimpleSessionTest';
import ConnectionTroubleshooter from './components/ConnectionTroubleshooter';
import SessionLifecycleDemo from './components/SessionLifecycleDemo';
// Removed: import './App.css'; - This file doesn't exist and isn't needed

type Page = 'lifecycle' | 'troubleshooter' | 'test' | 'dashboard';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('lifecycle'); // Start with lifecycle demo

  return (
    <div className="App min-h-screen bg-gray-50">
      {/* Simple Navigation */}
      <nav className="bg-white shadow-sm border-b p-4">
        <div className="max-w-7xl mx-auto flex gap-4 flex-wrap">
          <button
            onClick={() => setCurrentPage('lifecycle')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              currentPage === 'lifecycle' 
                ? 'bg-purple-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            🔄 Session Lifecycle
          </button>
          <button
            onClick={() => setCurrentPage('troubleshooter')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              currentPage === 'troubleshooter' 
                ? 'bg-red-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            🔧 Troubleshooter
          </button>
          <button
            onClick={() => setCurrentPage('test')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              currentPage === 'test' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            🧪 Simple Test
          </button>
          <button
            onClick={() => setCurrentPage('dashboard')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              currentPage === 'dashboard' 
                ? 'bg-green-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            📊 Full Dashboard
          </button>
        </div>
      </nav>

      {/* Page Content */}
      <main>
        {currentPage === 'lifecycle' && <SessionLifecycleDemo />}
        {currentPage === 'troubleshooter' && <ConnectionTroubleshooter />}
        {currentPage === 'test' && <SimpleSessionTest />}
        {currentPage === 'dashboard' && <LiveSessionDashboard />}
      </main>
    </div>
  );
}

export default App;