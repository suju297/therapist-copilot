// src/App.tsx - Live Session Dashboard Only
import React from 'react';
import LiveSessionDashboard from './components/LiveSessionDashboard';

function App() {
  return (
    <div className="App min-h-screen bg-gray-50">
      {/* Optional: Simple header if you want to keep branding */}
      <header className="bg-white shadow-sm border-b p-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-xl font-semibold text-gray-900">
            Therapist Copilot - Live Session
          </h1>
          <p className="text-sm text-gray-600">
            Real-time transcription & mental state assessment
          </p>
        </div>
      </header>

      {/* Main Content - Only Live Session Dashboard */}
      <main>
        <LiveSessionDashboard />
      </main>
    </div>
  );
}

export default App;