// src/components/SessionLifecycleDemo.tsx
import React, { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { Mic, MicOff, Play, Square, CheckCircle } from 'lucide-react';

export default function SessionLifecycleDemo() {
  const [sessionPhase, setSessionPhase] = useState<'waiting' | 'recording' | 'ending' | 'ended'>('waiting');
  
  const { 
    messages, 
    isConnected, 
    sttState,
    isRecording, 
    sessionId,
    startRecording, 
    stopRecording,
    endSession
  } = useWebSocket();

  // Filter messages
  const transcriptions = messages.filter(m => m.type === 'transcription');
  const finalTranscriptions = transcriptions.filter(t => t.data.is_final);
  const latestTranscription = transcriptions[transcriptions.length - 1];

  const handleStartSession = async () => {
    if (sttState.state === 'ready') {
      setSessionPhase('recording');
      await startRecording();
    }
  };

  const handleEndSession = async () => {
    setSessionPhase('ending');
    await endSession();
    setSessionPhase('ended');
  };

  const getPhaseColor = () => {
    switch (sessionPhase) {
      case 'waiting': return 'bg-gray-100 text-gray-800';
      case 'recording': return 'bg-green-100 text-green-800';
      case 'ending': return 'bg-yellow-100 text-yellow-800';
      case 'ended': return 'bg-blue-100 text-blue-800';
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold">Session Lifecycle Demo</h1>
        <p className="text-gray-600">Proper WebSocket session management</p>
        <div className="mt-2 space-y-2">
          <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getPhaseColor()}`}>
            Phase: {sessionPhase.toUpperCase()}
          </div>
          <div className="text-sm text-gray-500">
            Session: {sessionId}
          </div>
        </div>
      </div>

      {/* Connection Status */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="font-semibold mb-2">Connection Status</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className={`flex items-center gap-2 p-2 rounded ${
            isConnected ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            WebSocket: {isConnected ? 'Connected' : 'Disconnected'}
          </div>
          <div className={`flex items-center gap-2 p-2 rounded ${
            sttState.state === 'ready' ? 'bg-green-50 text-green-800' :
            sttState.state === 'connecting' ? 'bg-yellow-50 text-yellow-800' :
            'bg-red-50 text-red-800'
          }`}>
            STT: {sttState.state} {sttState.provider && `(${sttState.provider})`}
          </div>
        </div>
      </div>

      {/* Session Controls */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="font-semibold mb-4">Session Controls</h3>
        <div className="flex gap-4 justify-center">
          {sessionPhase === 'waiting' && (
            <button
              onClick={handleStartSession}
              disabled={!isConnected || sttState.state !== 'ready'}
              className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-5 h-5" />
              Start Session
            </button>
          )}
          
          {sessionPhase === 'recording' && (
            <button
              onClick={handleEndSession}
              className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              <Square className="w-5 h-5" />
              End Session
            </button>
          )}
          
          {sessionPhase === 'ending' && (
            <div className="flex items-center gap-2 px-6 py-3 bg-yellow-200 text-yellow-800 rounded-lg">
              <div className="w-5 h-5 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin"></div>
              Ending Session...
            </div>
          )}
          
          {sessionPhase === 'ended' && (
            <div className="flex items-center gap-2 px-6 py-3 bg-blue-200 text-blue-800 rounded-lg">
              <CheckCircle className="w-5 h-5" />
              Session Ended
            </div>
          )}
        </div>
        
        {sessionPhase === 'recording' && (
          <div className="mt-4 text-center">
            <div className="flex items-center justify-center gap-2 text-red-600">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              <span className="font-medium">RECORDING - Speak into your microphone</span>
            </div>
          </div>
        )}
      </div>

      {/* Live Transcription */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="font-semibold mb-4">Live Transcription</h3>
        {latestTranscription ? (
          <div className={`p-4 rounded-lg ${
            latestTranscription.data.is_final ? 'bg-green-50 border-l-4 border-green-400' : 'bg-blue-50 border-l-4 border-blue-400'
          }`}>
            <div className="flex justify-between items-start mb-2">
              <span className={`text-xs font-medium ${
                latestTranscription.data.is_final ? 'text-green-600' : 'text-blue-600'
              }`}>
                {latestTranscription.data.is_final ? '✓ Final' : '⟳ Processing'} 
                ({Math.round(latestTranscription.data.confidence * 100)}% confidence)
              </span>
              <span className="text-xs text-gray-500">
                {new Date(latestTranscription.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-lg">{latestTranscription.data.text}</p>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Mic className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No transcriptions yet</p>
            <p className="text-sm">Start session and speak to see live transcription</p>
          </div>
        )}
      </div>

      {/* Session Summary */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="font-semibold mb-4">Session Summary</h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-2xl font-bold text-gray-700">{transcriptions.length}</div>
            <div className="text-sm text-gray-600">Total Transcriptions</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-2xl font-bold text-gray-700">{finalTranscriptions.length}</div>
            <div className="text-sm text-gray-600">Final Transcriptions</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-2xl font-bold text-gray-700">
              {finalTranscriptions.reduce((acc, t) => acc + t.data.text.split(' ').length, 0)}
            </div>
            <div className="text-sm text-gray-600">Total Words</div>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 className="font-semibold text-yellow-800 mb-2">How This Demo Works</h3>
        <ol className="text-sm text-yellow-700 space-y-1 list-decimal list-inside">
          <li>WebSocket connects and waits for STT to be ready</li>
          <li>Click "Start Session" to begin recording</li>
          <li>Speak into your microphone to see live transcriptions</li>
          <li>Click "End Session" to properly close (waits for final transcriptions)</li>
          <li>Socket stays alive until all transcriptions are received</li>
        </ol>
        <div className="mt-3 p-2 bg-yellow-100 rounded text-xs">
          <strong>Key Fix:</strong> The socket won't close prematurely - it waits for final transcriptions before cleanup.
        </div>
      </div>
    </div>
  );
}