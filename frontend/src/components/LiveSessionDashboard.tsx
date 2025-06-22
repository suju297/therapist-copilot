// src/components/LiveSessionDashboard.tsx
import React, { useState, useMemo } from 'react';
import { useWebSocket, WSMessage, TranscriptPayload, RiskPayload } from '../hooks/useWebSocket';
import { 
  Mic, 
  MicOff, 
  AlertTriangle, 
  Shield, 
  Clock, 
  Users, 
  Activity,
  CheckCircle,
  XCircle,
  Pause,
  Play,
  RefreshCw
} from 'lucide-react';

// Risk level styling helper
const getRiskStyling = (level: string) => {
  switch (level) {
    case 'high':
      return {
        bg: 'bg-red-50 border-red-200',
        text: 'text-red-800',
        icon: 'text-red-600',
        badge: 'bg-red-100 text-red-800'
      };
    case 'medium':
      return {
        bg: 'bg-yellow-50 border-yellow-200',
        text: 'text-yellow-800',
        icon: 'text-yellow-600',
        badge: 'bg-yellow-100 text-yellow-800'
      };
    case 'low':
      return {
        bg: 'bg-green-50 border-green-200',
        text: 'text-green-800',
        icon: 'text-green-600',
        badge: 'bg-green-100 text-green-800'
      };
    default:
      return {
        bg: 'bg-gray-50 border-gray-200',
        text: 'text-gray-800',
        icon: 'text-gray-600',
        badge: 'bg-gray-100 text-gray-800'
      };
  }
};

// Format session duration
const formatDuration = (start: number) => {
  const elapsed = Math.floor((Date.now() - start) / 1000);
  const hours = Math.floor(elapsed / 3600);
  const minutes = Math.floor((elapsed % 3600) / 60);
  const seconds = elapsed % 60;
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

interface ConversationPanelProps {
  messages: WSMessage[];
  sttState: any;
  isConnected: boolean;
}

const ConversationPanel: React.FC<ConversationPanelProps> = ({ messages, sttState, isConnected }) => {
  const transcriptMessages = messages.filter(m => m.type === 'transcription') as (WSMessage & { data: TranscriptPayload })[];
  
  if (transcriptMessages.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 h-96">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Users className="h-5 w-5" />
          Live Conversation
        </h3>
        <div className="text-center py-8 text-gray-500">
          {!isConnected ? (
            <>
              <XCircle className="h-8 w-8 mx-auto mb-3 text-red-300" />
              <p>WebSocket disconnected</p>
              <p className="text-sm">Attempting to reconnect...</p>
            </>
          ) : sttState.state === 'connecting' ? (
            <>
              <Activity className="h-8 w-8 mx-auto mb-3 text-blue-300 animate-pulse" />
              <p>Connecting to speech service...</p>
              <p className="text-sm">Please wait while we establish the connection</p>
            </>
          ) : sttState.state === 'ready' ? (
            <>
              <Mic className="h-8 w-8 mx-auto mb-3 text-gray-300" />
              <p>Ready for audio input</p>
              <p className="text-sm">Click "Start Recording" to begin transcription</p>
            </>
          ) : sttState.state === 'error' ? (
            <>
              <XCircle className="h-8 w-8 mx-auto mb-3 text-red-300" />
              <p>Speech service error</p>
              <p className="text-sm">{sttState.error_message || 'Connection failed'}</p>
            </>
          ) : (
            <>
              <Mic className="h-8 w-8 mx-auto mb-3 text-gray-300" />
              <p>Waiting for connection...</p>
              <p className="text-sm">Setting up audio processing</p>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 h-96">
      <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <Users className="h-5 w-5" />
        Live Conversation
      </h3>
      <div className="space-y-3 h-80 overflow-y-auto">
        {transcriptMessages.map((msg, index: number) => (
          <div 
            key={index}
            className={`p-3 rounded-lg max-w-xs ${
              msg.data.realtime 
                ? 'bg-blue-50 border-l-4 border-blue-400 ml-auto text-right' 
                : 'bg-gray-50 border-l-4 border-gray-400'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-600">
                  Audio Input
                </span>
                {msg.data.is_final ? (
                  <CheckCircle className="h-3 w-3 text-green-500" />
                ) : (
                  <Activity className="h-3 w-3 text-blue-500 animate-pulse" />
                )}
              </div>
              <span className="text-xs text-gray-500">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-sm text-gray-900">{msg.data.text}</p>
            <div className="text-xs text-gray-500 mt-1">
              Confidence: {Math.round(msg.data.confidence * 100)}%
              {!msg.data.is_final && <span className="ml-2 italic">Processing...</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface RiskMonitorProps {
  messages: WSMessage[];
}

const RiskMonitor: React.FC<RiskMonitorProps> = ({ messages }) => {
  const riskMessages = messages.filter(m => m.type === 'risk_assessment' || m.type === 'crisis_detected') as (WSMessage & { data: RiskPayload })[];
  const latestRisk = riskMessages[riskMessages.length - 1];
  const crisisDetected = messages.some(m => m.type === 'crisis_detected');
  
  const currentRiskLevel = latestRisk?.data?.risk_level || 'low';
  const riskScore = latestRisk?.data?.risk_score || 0;
  const styling = getRiskStyling(currentRiskLevel);

  return (
    <div className={`rounded-lg border p-6 ${styling.bg} ${styling.text}`}>
      <h3 className="font-semibold mb-4 flex items-center gap-2">
        <Shield className={`h-5 w-5 ${styling.icon}`} />
        Risk Assessment
        {crisisDetected && (
          <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded-full animate-pulse">
            CRISIS DETECTED
          </span>
        )}
      </h3>
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Current Level:</span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${styling.badge}`}>
            {currentRiskLevel.toUpperCase()}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Risk Score:</span>
          <span className="text-sm">{(riskScore * 100).toFixed(1)}%</span>
        </div>

        {latestRisk && (
          <>
            <div className="text-sm">
              <strong>Analysis:</strong>
              <p className="mt-1 text-xs">{latestRisk.data.explanation}</p>
            </div>
            
            {latestRisk.data.recommendations && latestRisk.data.recommendations.length > 0 && (
              <div className="text-sm">
                <strong>Recommendations:</strong>
                <ul className="mt-1 text-xs space-y-1">
                  {latestRisk.data.recommendations.map((rec: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-1">
                      <span>•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {crisisDetected && (
          <div className="bg-red-100 border border-red-300 rounded p-3 mt-4">
            <div className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="h-4 w-4" />
              <span className="font-medium">Immediate Action Required</span>
            </div>
            <p className="text-xs text-red-700 mt-1">
              Crisis intervention protocols may need to be activated. Consider contacting emergency services if necessary.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default function LiveSessionDashboard() {
  const [sessionStart] = useState(Date.now());
  const [manualSessionId] = useState<string | undefined>(undefined); // Let hook generate ID automatically
  
  const { 
    messages, 
    isConnected, 
    sttState,
    isRecording, 
    connectionError, 
    audioConfig,
    sessionId,
    startRecording, 
    stopRecording,
    disconnect,
    reconnect,
    endSession,
    getSessionSummary,
    resetSession,
    clearMessages
  } = useWebSocket(manualSessionId);

  // Calculate session stats
  const transcriptMessages = messages.filter(m => m.type === 'transcription');
  const audioReceivedCount = messages.filter(m => m.type === 'audio_received').length;
  const sessionDuration = formatDuration(sessionStart);

  const handleRecordingToggle = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Live Session Dashboard</h1>
              <p className="text-gray-600">Real-time audio monitoring and AI assistance</p>
              <p className="text-sm text-gray-500 mt-1">Session ID: {sessionId}</p>
            </div>
            <div className="flex items-center gap-4">
              {/* WebSocket Connection Status */}
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                <span className="text-sm font-medium">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>

              {/* STT Connection Status */}
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                sttState.state === 'ready' ? 'bg-blue-100 text-blue-800' :
                sttState.state === 'connecting' ? 'bg-yellow-100 text-yellow-800' :
                sttState.state === 'error' ? 'bg-red-100 text-red-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {sttState.state === 'connecting' && (
                  <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></div>
                )}
                {sttState.state === 'ready' && (
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                )}
                {sttState.state === 'error' && (
                  <div className="w-2 h-2 rounded-full bg-red-500"></div>
                )}
                {sttState.state === 'disconnected' && (
                  <div className="w-2 h-2 rounded-full bg-gray-500"></div>
                )}
                <span className="text-sm font-medium">
                  STT: {sttState.state === 'connecting' ? 'Connecting...' : 
                        sttState.state === 'ready' ? `Ready (${sttState.provider})` :
                        sttState.state === 'error' ? 'Error' : 'Disconnected'}
                </span>
              </div>
              
              <button
                onClick={handleRecordingToggle}
                disabled={!isConnected || sttState.state !== 'ready'}
                className={`p-3 rounded-lg transition-colors flex items-center gap-2 ${
                  isRecording 
                    ? 'bg-red-100 text-red-800 hover:bg-red-200' 
                    : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                } ${(!isConnected || sttState.state !== 'ready') ? 'opacity-50 cursor-not-allowed' : ''}`}
                title={sttState.state !== 'ready' ? `Cannot record: STT is ${sttState.state}` : ''}
              >
                {isRecording ? (
                  <>
                    <MicOff className="h-5 w-5" />
                    <span>Stop Recording</span>
                  </>
                ) : (
                  <>
                    <Mic className="h-5 w-5" />
                    <span>Start Recording</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Connection Error & STT Status */}
          {(connectionError || sttState.error_message) && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-red-800">
                <XCircle className="h-4 w-4" />
                <span className="font-medium">Connection Issue</span>
              </div>
              {connectionError && (
                <p className="text-sm text-red-700 mt-1">{connectionError}</p>
              )}
              {sttState.error_message && (
                <p className="text-sm text-red-700 mt-1">STT: {sttState.error_message}</p>
              )}
              {sttState.error_message?.includes("Only one realtime session") && (
                <p className="text-xs text-red-600 mt-2">
                  💡 Tip: Close any other browser tabs with this app open, or wait 15 seconds for the session to expire.
                </p>
              )}
            </div>
          )}

          {/* STT Connection Progress */}
          {isConnected && sttState.state === 'connecting' && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-blue-800">
                <Activity className="h-4 w-4 animate-pulse" />
                <span className="font-medium">Connecting to Speech-to-Text Service...</span>
              </div>
              <p className="text-sm text-blue-700 mt-1">
                Establishing connection to {sttState.provider || 'STT provider'}. This usually takes a few seconds.
              </p>
            </div>
          )}

          {/* Session Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Session Duration</p>
                  <p className="text-2xl font-bold text-gray-900">{sessionDuration}</p>
                </div>
                <Clock className="h-8 w-8 text-blue-500" />
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Transcripts</p>
                  <p className="text-2xl font-bold text-gray-900">{transcriptMessages.length}</p>
                </div>
                <Users className="h-8 w-8 text-green-500" />
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Audio Chunks</p>
                  <p className="text-2xl font-bold text-gray-900">{audioReceivedCount}</p>
                </div>
                <Activity className="h-8 w-8 text-purple-500" />
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Recording Status</p>
                  <p className={`text-sm font-medium ${isRecording ? 'text-red-600' : 'text-gray-600'}`}>
                    {isRecording ? 'LIVE' : 'STOPPED'}
                  </p>
                </div>
                {isRecording ? (
                  <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                ) : (
                  <Pause className="h-8 w-8 text-gray-400" />
                )}
              </div>
            </div>
          </div>

          {/* Audio Configuration Info */}
          {audioConfig && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <h4 className="font-medium text-blue-900 mb-2">Audio Configuration</h4>
              <div className="grid grid-cols-3 gap-4 text-sm text-blue-800">
                <div>
                  <span className="font-medium">Sample Rate:</span> {audioConfig.sample_rate} Hz
                </div>
                <div>
                  <span className="font-medium">Chunk Duration:</span> {audioConfig.chunk_ms}ms
                </div>
                <div>
                  <span className="font-medium">Chunk Samples:</span> {audioConfig.chunk_samples}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <ConversationPanel messages={messages} sttState={sttState} isConnected={isConnected} />
          <RiskMonitor messages={messages} />
        </div>

        {/* Session Controls */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Session Controls</h3>
          <div className="flex gap-4 flex-wrap">
            <button
              onClick={getSessionSummary}
              disabled={!isConnected}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Get Session Summary
            </button>
            <button
              onClick={clearMessages}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              Clear Messages
            </button>
            <button
              onClick={resetSession}
              disabled={!isConnected}
              className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Reset Session
            </button>
            <button
              onClick={endSession}
              disabled={!isConnected}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              End Session Properly
            </button>
            <button
              onClick={reconnect}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Reconnect
            </button>
            <button
              onClick={disconnect}
              disabled={!isConnected}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Force Disconnect
            </button>
          </div>
          
          {/* Connection Info */}
          <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
            <strong>Connection Status:</strong> WebSocket {isConnected ? '✅' : '❌'} | 
            STT {sttState.state === 'ready' ? '✅' : sttState.state === 'connecting' ? '🔄' : '❌'} |
            Recording {isRecording ? '🎙️' : '⏸️'}
            {sttState.provider && <span> | Provider: {sttState.provider}</span>}
          </div>
        </div>

        {/* Debug Messages (Development Only) */}
        {import.meta.env.DEV && (
          <div className="mt-6 bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-xs">
            <h4 className="text-white mb-2">Debug Messages ({messages.length})</h4>
            <div className="max-h-40 overflow-y-auto space-y-1">
              {messages.slice(-10).map((msg, idx: number) => (
                <div key={idx}>
                  <span className="text-yellow-400">[{new Date(msg.timestamp).toLocaleTimeString()}]</span>
                  <span className="text-blue-400"> {msg.type}:</span>
                  <span> {JSON.stringify(msg.data, null, 0)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}