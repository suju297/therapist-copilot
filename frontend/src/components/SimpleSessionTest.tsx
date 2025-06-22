// src/components/SimpleSessionTest.tsx
import React from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { Mic, MicOff } from 'lucide-react';

export default function SimpleSessionTest() {
  const { 
    messages, 
    isConnected, 
    isRecording, 
    sessionId,
    sttState,
    startRecording, 
    stopRecording 
  } = useWebSocket(); // Auto-generates session ID

  // Filter messages by type
  const transcriptions = messages.filter(m => m.type === 'transcription');
  const riskAssessments = messages.filter(m => m.type === 'risk_assessment');
  const crises = messages.filter(m => m.type === 'crisis_detected');

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold">WebSocket Integration Test</h1>
        <p className="text-gray-600">Session: {sessionId}</p>
        <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
          isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
        
        {/* STT Status */}
        <div className={`mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
          sttState.state === 'ready' ? 'bg-blue-100 text-blue-800' :
          sttState.state === 'connecting' ? 'bg-yellow-100 text-yellow-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          STT: {sttState.state === 'connecting' ? 'Connecting...' : 
                sttState.state === 'ready' ? 'Ready' :
                sttState.state === 'error' ? 'Error' : 'Disconnected'}
        </div>
      </div>

      {/* Recording Control */}
      <div className="text-center">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={!isConnected || sttState.state !== 'ready'}
          className={`inline-flex items-center gap-2 px-6 py-3 rounded-lg font-medium ${
            isRecording 
              ? 'bg-red-600 text-white hover:bg-red-700' 
              : 'bg-blue-600 text-white hover:bg-blue-700'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          {isRecording ? 'Stop Recording' : 'Start Recording'}
        </button>
        {isRecording && (
          <div className="text-center mt-2">
            <p className="text-sm text-red-600 animate-pulse">
              🔴 Recording with AudioWorklet (16kHz PCM)
            </p>
            <p className="text-xs text-gray-500">
              Speak into your microphone - live transcriptions should appear below
            </p>
          </div>
        )}
        {!isConnected && (
          <p className="text-sm text-gray-500 mt-2">
            Waiting for connection...
          </p>
        )}
        {isConnected && sttState.state !== 'ready' && (
          <p className="text-sm text-yellow-600 mt-2">
            Waiting for speech service to be ready...
          </p>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 text-center">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">{transcriptions.length}</div>
          <div className="text-sm text-blue-800">Transcriptions</div>
        </div>
        <div className="bg-yellow-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600">{riskAssessments.length}</div>
          <div className="text-sm text-yellow-800">Risk Assessments</div>
        </div>
        <div className="bg-red-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-red-600">{crises.length}</div>
          <div className="text-sm text-red-800">Crisis Alerts</div>
        </div>
      </div>

      {/* Crisis Alerts */}
      {crises.length > 0 && (
        <div className="bg-red-100 border border-red-300 rounded-lg p-4">
          <h3 className="font-bold text-red-800 mb-2">🚨 CRISIS DETECTED</h3>
          {crises.map((crisis, idx: number) => (
            <div key={idx} className="text-sm text-red-700">
              <strong>Risk Score:</strong> {(crisis.data.risk_score * 100).toFixed(1)}% <br />
              <strong>Explanation:</strong> {crisis.data.explanation}
            </div>
          ))}
        </div>
      )}

      {/* Latest Risk Assessment */}
      {riskAssessments.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="font-bold text-yellow-800 mb-2">Latest Risk Assessment</h3>
          {(() => {
            const latest = riskAssessments[riskAssessments.length - 1];
            return (
              <div className="text-sm text-yellow-700">
                <strong>Level:</strong> {latest.data.risk_level.toUpperCase()} 
                ({(latest.data.risk_score * 100).toFixed(1)}%) <br />
                <strong>Analysis:</strong> {latest.data.explanation}
              </div>
            );
          })()}
        </div>
      )}

      {/* Transcriptions */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="font-bold text-gray-800 mb-4">Live Transcriptions</h3>
        {transcriptions.length === 0 ? (
          <p className="text-gray-500 italic">No transcriptions yet. Start recording and speak...</p>
        ) : (
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {transcriptions.map((msg, idx: number) => (
              <div key={idx} className={`p-3 rounded-lg ${
                msg.data.is_final ? 'bg-green-50 border-l-4 border-green-400' : 'bg-blue-50 border-l-4 border-blue-400'
              }`}>
                <div className="flex justify-between items-start mb-1">
                  <span className={`text-xs font-medium ${
                    msg.data.is_final ? 'text-green-600' : 'text-blue-600'
                  }`}>
                    {msg.data.is_final ? '✓ Final' : '⟳ Processing'} 
                    ({Math.round(msg.data.confidence * 100)}% confidence)
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm text-gray-900">{msg.data.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Raw Messages (Debug) */}
      <details className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <summary className="font-bold text-gray-800 cursor-pointer">
          Debug: Raw Messages ({messages.length})
        </summary>
        <div className="mt-4 max-h-40 overflow-y-auto">
          <pre className="text-xs text-gray-600">
            {JSON.stringify(messages.slice(-5), null, 2)}
          </pre>
        </div>
      </details>
    </div>
  );
}