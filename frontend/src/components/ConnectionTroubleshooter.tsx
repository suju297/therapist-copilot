// src/components/ConnectionTroubleshooter.tsx - Updated for proper WebSocket flow
import React, { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle,
  XCircle,
  Clock,
  Server,
  Mic,
  MicOff,
  Play,
  Square
} from 'lucide-react';

export default function ConnectionTroubleshooter() {
  const [sessionId] = useState<string>(() => {
    // Generate a single stable session ID for this test
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    // Fallback UUID generation
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  });

  const { 
    messages, 
    isConnected, 
    sttState,
    isRecording, 
    connectionError,
    audioConfig,
    lastPartial, // New: live transcription text
    startRecording, 
    stopRecording,
    disconnect,
    reconnect,
    forceReconnect,
    resetSession,
    clearMessages
  } = useWebSocket(sessionId);

  // Helper functions
  const getConnectionIcon = () => {
    if (isConnected) return <CheckCircle className="h-5 w-5 text-green-600" />;
    if (connectionError) return <XCircle className="h-5 w-5 text-red-600" />;
    return <Clock className="h-5 w-5 text-yellow-600" />;
  };

  const getSTTIcon = () => {
    switch (sttState.state) {
      case 'ready': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'connecting': return <Clock className="h-5 w-5 text-yellow-600" />;
      case 'error': return <XCircle className="h-5 w-5 text-red-600" />;
      case 'disconnected': return <Server className="h-5 w-5 text-gray-400" />;
      default: return <Server className="h-5 w-5 text-gray-400" />;
    }
  };

  const canStartRecording = isConnected && sttState.state === 'ready' && !isRecording;

  // Filter and format messages
  const transcriptions = messages.filter(m => m.type === 'transcription');
  const recentMessages = messages.slice(-10); // Show last 10 messages

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">WebSocket Connection Troubleshooter</h1>
        <p className="text-gray-600">Test and debug real-time audio streaming</p>
        <div className="mt-2 text-sm text-gray-500">Session: {sessionId}</div>
      </div>

      {/* Connection Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* WebSocket Status */}
        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            {getConnectionIcon()}
            <h3 className="font-semibold">WebSocket</h3>
          </div>
          <div className="text-sm text-gray-600">
            Status: <span className={`font-medium ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Endpoint: {location.protocol === 'https:' ? 'wss' : 'ws'}://localhost:8000/api/v1/ws/audio/{sessionId}
          </div>
        </div>

        {/* STT Status */}
        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            {getSTTIcon()}
            <h3 className="font-semibold">STT Service</h3>
          </div>
          <div className="text-sm text-gray-600">
            Status: <span className={`font-medium ${
              sttState.state === 'ready' ? 'text-green-600' : 
              sttState.state === 'connecting' ? 'text-yellow-600' : 
              sttState.state === 'error' ? 'text-red-600' : 
              sttState.state === 'disconnected' ? 'text-gray-600' : 'text-gray-600'
            }`}>
              {sttState.state === 'disconnected' ? 'Disconnected' : 
               sttState.state.charAt(0).toUpperCase() + sttState.state.slice(1)}
            </span>
          </div>
          {sttState.provider && (
            <div className="text-xs text-gray-500 mt-1">
              Provider: {sttState.provider}
            </div>
          )}
          {sttState.error_message && (
            <div className="text-xs text-red-600 mt-1">
              Error: {sttState.error_message}
            </div>
          )}
        </div>

        {/* Recording Status */}
        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            {isRecording ? 
              <Mic className="h-5 w-5 text-red-600 animate-pulse" /> : 
              <MicOff className="h-5 w-5 text-gray-400" />
            }
            <h3 className="font-semibold">Recording (PCM)</h3>
          </div>
          <div className="text-sm text-gray-600">
            Status: <span className={`font-medium ${isRecording ? 'text-red-600' : 'text-gray-600'}`}>
              {isRecording ? 'Recording Raw PCM' : 'Stopped'}
            </span>
          </div>
          {audioConfig && (
            <div className="text-xs text-gray-500 mt-1">
              {audioConfig.sample_rate}Hz, 16-bit PCM, {audioConfig.chunk_ms}ms chunks
            </div>
          )}
          {isRecording && (
            <div className="text-xs text-blue-600 mt-1">
              📡 Sending raw Int16 PCM data to AssemblyAI
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {connectionError && (
        <div className="bg-red-50 border border-red-300 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
            <div>
              <div className="font-medium text-red-800">Connection Error</div>
              <div className="text-sm text-red-700 mt-1">{connectionError}</div>
              
              {connectionError.includes("free tier") && (
                <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
                  <div className="text-sm text-yellow-800">
                    <strong>🎯 Quick Fix:</strong>
                    <ol className="mt-1 ml-4 list-decimal space-y-1">
                      <li>Close all other browser tabs with this app</li>
                      <li>Wait 15 seconds for AssemblyAI cleanup</li>
                      <li>Click "Force Reconnect" below</li>
                    </ol>
                  </div>
                  <div className="mt-2">
                    <button
                      onClick={forceReconnect}
                      className="bg-yellow-600 text-white px-3 py-1 rounded text-sm hover:bg-yellow-700"
                    >
                      🔄 Force Reconnect
                    </button>
                  </div>
                  <div className="text-xs text-yellow-700 mt-2">
                    💡 <strong>Why this happens:</strong> AssemblyAI's free tier allows only 1 concurrent session. 
                    The connection is working perfectly - just need to clear previous sessions.
                  </div>
                </div>
              )}

              {connectionError.includes("concurrent") && !connectionError.includes("free tier") && (
                <div className="mt-3">
                  <button
                    onClick={forceReconnect}
                    className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
                  >
                    Try Again
                  </button>
                  <div className="text-xs text-red-600 mt-1">
                    Close other tabs with active sessions first
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="font-semibold mb-4">Controls</h3>
        <div className="flex flex-wrap gap-3">
          {/* Recording Controls */}
          <button
            onClick={canStartRecording ? startRecording : undefined}
            disabled={!canStartRecording}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              canStartRecording
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Play className="h-4 w-4" />
            Start Recording
          </button>

          <button
            onClick={stopRecording}
            disabled={!isRecording}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              isRecording
                ? 'bg-gray-700 text-white hover:bg-gray-800'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Square className="h-4 w-4" />
            Stop Recording
          </button>

          {/* Connection Controls */}
          <button
            onClick={reconnect}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
          >
            <RefreshCw className="h-4 w-4" />
            Reconnect
          </button>

          <button
            onClick={disconnect}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg font-medium hover:bg-gray-700"
          >
            <WifiOff className="h-4 w-4" />
            Disconnect
          </button>

          {/* Utility Controls */}
          <button
            onClick={resetSession}
            className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg font-medium hover:bg-yellow-700"
          >
            <RefreshCw className="h-4 w-4" />
            Reset Session
          </button>

          <button
            onClick={clearMessages}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg font-medium hover:bg-gray-600"
          >
            Clear Messages
          </button>
        </div>
      </div>

      {/* Audio Pipeline Debug */}
      {isRecording && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold mb-4 flex items-center gap-2 text-blue-800">
            <Mic className="h-5 w-5" />
            Audio Pipeline Status (AssemblyAI Compliant)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <div className="bg-white rounded p-3">
              <div className="font-medium text-blue-700">🎤 Capture</div>
              <div className="text-xs text-gray-600 mt-1">
                Browser microphone<br/>
                48kHz (native)<br/>
                Float32 samples
              </div>
            </div>
            <div className="bg-white rounded p-3">
              <div className="font-medium text-blue-700">⬇️ Downsample</div>
              <div className="text-xs text-gray-600 mt-1">
                AudioWorklet<br/>
                48kHz → 16kHz<br/>
                Every 3rd sample<br/>
                Float32 → Int16
              </div>
            </div>
            <div className="bg-white rounded p-3">
              <div className="font-medium text-blue-700">📦 Buffer</div>
              <div className="text-xs text-gray-600 mt-1">
                ≥800 samples<br/>
                ≥50ms duration<br/>
                AssemblyAI minimum<br/>
                ~1.6KB chunks
              </div>
            </div>
            <div className="bg-white rounded p-3">
              <div className="font-medium text-blue-700">🤖 AssemblyAI</div>
              <div className="text-xs text-gray-600 mt-1">
                Real-time STT<br/>
                16kHz PCM input<br/>
                50-1000ms chunks<br/>
                ✅ Accepts chunks!
              </div>
            </div>
          </div>
          <div className="mt-3 p-2 bg-green-100 border border-green-300 rounded text-xs text-green-800">
            ✅ <strong>AssemblyAI Compliant:</strong> Now sending ≥50ms chunks (was 32ms). 
            Fixed "Input duration violation" error. Chunks are 800+ samples = 50ms+ duration.
          </div>
        </div>
      )}

      {/* Live Transcription Display */}
      {(isRecording || lastPartial) && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            {isRecording ? (
              <Mic className="h-5 w-5 text-red-600 animate-pulse" />
            ) : (
              <MicOff className="h-5 w-5 text-gray-400" />
            )}
            Live Transcription
          </h3>
          <div className="bg-gray-50 rounded-lg p-4 min-h-16">
            {lastPartial ? (
              <div className="text-lg">
                <span className="text-blue-600">🔹 </span>
                <span className="text-gray-800">{lastPartial}</span>
              </div>
            ) : (
              <div className="text-gray-500 italic">
                {isRecording ? "Listening... speak into your microphone" : "No transcription yet"}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Real-time Messages */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="font-semibold mb-4">
          Real-time Messages ({messages.length} total)
        </h3>
        
        {/* Message Type Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4 text-xs">
          <div className="bg-blue-50 p-2 rounded">
            <div className="font-medium text-blue-800">Audio Chunks</div>
            <div className="text-blue-600">{messages.filter(m => m.type === 'audio_received').length}</div>
          </div>
          <div className="bg-green-50 p-2 rounded">
            <div className="font-medium text-green-800">Transcriptions</div>
            <div className="text-green-600">{transcriptions.length}</div>
          </div>
          <div className="bg-purple-50 p-2 rounded">
            <div className="font-medium text-purple-800">Final Transcripts</div>
            <div className="text-purple-600">{transcriptions.filter(t => t.data.is_final).length}</div>
          </div>
          <div className="bg-yellow-50 p-2 rounded">
            <div className="font-medium text-yellow-800">Errors</div>
            <div className="text-yellow-600">{messages.filter(m => m.type === 'error').length}</div>
          </div>
        </div>

        <div className="space-y-2 max-h-64 overflow-y-auto">
          {recentMessages.length === 0 ? (
            <div className="text-gray-500 text-sm">No messages yet...</div>
          ) : (
            recentMessages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`text-sm p-2 rounded border-l-4 ${
                  msg.type === 'transcription' ? 'border-blue-400 bg-blue-50' :
                  msg.type === 'connection_established' ? 'border-green-400 bg-green-50' :
                  msg.type === 'stt_ready' ? 'border-green-400 bg-green-50' :
                  msg.type === 'audio_received' ? 'border-gray-400 bg-gray-50' :
                  msg.type === 'error' ? 'border-red-400 bg-red-50' :
                  'border-gray-400 bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium text-xs uppercase text-gray-600">
                    {msg.type}
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                </div>
                <div className="mt-1">
                  {msg.type === 'transcription' && msg.data?.text ? (
                    <span>
                      {msg.data.is_final ? '🔸 FINAL: ' : '🔹 PARTIAL: '}
                      "{msg.data.text}"
                      <span className="text-xs text-gray-500 ml-2">
                        (confidence: {(msg.data.confidence * 100).toFixed(1)}%)
                      </span>
                    </span>
                  ) : msg.type === 'audio_received' ? (
                    <span className="text-xs text-gray-600">
                      📡 Chunk {msg.data.chunk_number}: {msg.data.total_samples} samples 
                      ({msg.data.duration_seconds?.toFixed(3)}s)
                    </span>
                  ) : (
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                      {JSON.stringify(msg.data, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Transcription Summary */}
      {transcriptions.length > 0 && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold mb-4">
            Transcriptions ({transcriptions.length} received)
          </h3>
          <div className="space-y-2">
            {transcriptions.filter(t => t.data.is_final).map((t, idx) => (
              <div key={idx} className="text-sm">
                <span className="text-gray-500">[{new Date(t.timestamp).toLocaleTimeString()}]</span>
                <span className="ml-2">"{t.data.text}"</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}