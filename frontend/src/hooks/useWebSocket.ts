// src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { getErrorMessage, handleWebSocketError, handleMediaError } from "../lib/errorUtils";

export interface WSMessage {
  type: "connection_established" | "stt_ready" | "audio_received" | "transcription" | "risk_assessment" | "crisis_detected" | "session_summary" | "error" | "session_locked" | "stt_error";
  session_id: string;
  data: any;
  timestamp: string;
}

export interface TranscriptPayload {
  text: string;
  confidence: number;
  is_final: boolean;
  word_count: number;
  timestamp: string;
  provider: string;
  realtime: boolean;
}

export interface RiskPayload {
  risk_score: number;
  risk_level: "low" | "medium" | "high";
  explanation: string;
  recommendations: string[];
  transcript_analyzed: string;
}

export interface AudioConfig {
  sample_rate: number;
  chunk_ms: number;
  chunk_samples: number;
}

export interface STTState {
  state: "disconnected" | "connecting" | "ready" | "error";
  provider: string | null;
  lastPartial: string;
  error_message: string | null;
}

export function useWebSocket(sessionId?: string) {
  // Refs
  const ws = useRef<WebSocket | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioStream = useRef<MediaStream | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const audioProcessor = useRef<AudioNode | null>(null); // Fixed: Use AudioNode base type
  const reconnectTimeoutRef = useRef<number | null>(null);
  const connectionAttempts = useRef<number>(0);
  const isManuallyDisconnected = useRef<boolean>(false);
  const isRecordingActiveRef = useRef<boolean>(false); // Track if recording is active
  const hasReceivedTranscription = useRef<boolean>(false); // Track if we've received any transcriptions
  const hasInitialised = useRef<boolean>(false); // ADD THIS - Missing ref declaration
  
  // State
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [sttState, setSTTState] = useState<STTState>({
    state: "disconnected",
    provider: null,
    lastPartial: "",
    error_message: null,
  });
  const [isRecording, setIsRecording] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [audioConfig, setAudioConfig] = useState<AudioConfig | null>(null);
  const [isProcessingComplete, setIsProcessingComplete] = useState(false);

  // Generate stable session ID
  const currentSessionId = useMemo(() => {
    if (sessionId) {
      return sessionId;
    }
    
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    
    // Fallback UUID generation
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }, [sessionId]);

  // Connection function
  const connect = useCallback(() => {
    if (isManuallyDisconnected.current) {
      console.log("🚫 Connection attempt blocked - manually disconnected");
      return;
    }

    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log("⚠️ WebSocket already connected");
      return;
    }

    try {
      console.log(`📡 Connecting to WebSocket... (attempt ${connectionAttempts.current + 1})`);
      setConnectionError(null);
      
      // Fix #1: Use correct WebSocket URL endpoint pointing to backend port 8000
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${proto}://localhost:8000/api/v1/ws/audio/${currentSessionId}`;
      console.log(`🔗 Connecting to: ${wsUrl}`);
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log("✅ WebSocket connected successfully");
        setIsConnected(true);
        setConnectionError(null);
        connectionAttempts.current = 0;
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          console.log("📨 Received message:", message.type, message);
          
          setMessages(prev => [...prev, message]);

          // Handle specific message types with improved state machine
          switch (message.type) {
            case 'connection_established':
              console.log("✅ Connection established - checking STT state...");
              
              // Check if STT is already ready in the connection_established message
              if (message.data.stt_state === "ready") {
                console.log("✅ STT service ready immediately!");
                setSTTState(prev => ({
                  ...prev,
                  state: "ready",
                  provider: message.data.stt_provider,
                }));
              } else {
                console.log("⏳ STT connecting...");
                setSTTState(prev => ({ 
                  ...prev, 
                  state: "connecting",
                  provider: message.data.stt_provider,
                }));
              }
              
              if (message.data.audio_config) {
                setAudioConfig(message.data.audio_config);
              }
              break;
              
            case 'stt_ready':
              console.log("✅ STT service ready for recording (separate message)");
              setSTTState(prev => ({
                ...prev,
                state: "ready",
                provider: message.data.stt_provider,
              }));
              break;
            
            case 'transcription':
              hasReceivedTranscription.current = true;
              setSTTState(prev => ({
                ...prev,
                lastPartial: message.data.text,
              }));
              // Check if this is a final transcription
              if (message.data.is_final) {
                console.log("✅ Received final transcription:", message.data.text);
              }
              break;
            
            case 'audio_received':
              // Audio chunk acknowledgment - no UI impact
              break;

            case 'stt_error':
              console.error("❌ STT error:", message.data);
              setSTTState(prev => ({
                ...prev,
                state: "error",
                error_message: message.data.message,
              }));
              break;
            
            case 'session_summary':
            case 'crisis_detected':
              console.log("🏁 Session processing complete - safe to close");
              setIsProcessingComplete(true);
              // Auto-close after receiving session end signals
              setTimeout(() => {
                if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                  ws.current.close(1000, "Session processing complete");
                }
              }, 500);
              break;
            
            case 'error':
              console.error("❌ Server error:", message.data);
              const errorMsg = message.data.message || message.data.error || "Server error";
              setConnectionError(errorMsg);
              
              // Handle specific errors
              if (errorMsg.includes("concurrent") || errorMsg.includes("free tier")) {
                console.log("🚫 AssemblyAI free tier limit reached - stopping reconnection");
                isManuallyDisconnected.current = true;
                // Show user-friendly message
                setConnectionError("🚫 Free tier limit: Only one session allowed. Close other tabs or wait 15 seconds.");
              } else if (errorMsg.includes("limit")) {
                console.log("🚫 AssemblyAI session limit reached - stopping reconnection");
                isManuallyDisconnected.current = true;
              }
              break;

            default:
              // Other messages like audio_received - no UI impact
              break;
          }
        } catch (error) {
          console.error("❌ Failed to parse WebSocket message:", error);
        }
      };

      ws.current.onclose = (event) => {
        console.log("🔌 WebSocket closed:", event.code, event.reason);
        setIsConnected(false);
        setSTTState(prev => ({ ...prev, state: "disconnected" }));

        // Handle specific close codes
        if (event.code === 1008) {
          // AssemblyAI session limit reached
          console.log("🚫 Session limit reached - not reconnecting");
          setConnectionError("Only one concurrent realtime session allowed on free tier.");
          isManuallyDisconnected.current = true;
          return;
        }

        if (!isManuallyDisconnected.current && connectionAttempts.current < 5) {
          // Exponential backoff with jitter
          const baseDelay = Math.min(1000 * Math.pow(2, connectionAttempts.current), 30000);
          const jitter = Math.random() * 1000; // Add randomness to prevent thundering herd
          const delay = baseDelay + jitter;
          
          console.log(`🔄 Reconnecting in ${Math.round(delay)}ms... (attempt ${connectionAttempts.current + 1}/5)`);
          
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connectionAttempts.current++;
            connect();
          }, delay);
        } else if (connectionAttempts.current >= 5) {
          console.log("❌ Max reconnection attempts reached");
          setConnectionError("Connection failed after 5 attempts. Please refresh the page.");
        }
      };

      ws.current.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
        setConnectionError("WebSocket connection failed");
      };

    } catch (error) {
      console.error("❌ Failed to create WebSocket:", error);
      setConnectionError("Failed to create WebSocket connection");
    }
  }, [currentSessionId]);

  // Recording functions
  const startRecording = useCallback(async () => {
    if (isRecording) {
      console.log("⚠️ Already recording");
      return;
    }

    // Fix #4: Wait for STT to be ready before recording
    if (!isConnected || sttState.state !== "ready") {
      console.log("❌ Cannot start recording - STT not ready", { 
        connected: isConnected, 
        sttState: sttState.state 
      });
      setConnectionError("STT service not ready. Please wait for connection to establish.");
      return;
    }

    try {
      console.log("🎤 Starting AudioWorklet PCM capture with downsampling...");
      
      // Get microphone stream - let browser use native sample rate
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      audioStream.current = stream;
      isRecordingActiveRef.current = true;
      setIsRecording(true);

      // Create AudioContext with default sample rate (usually 48kHz)
      audioContext.current = new AudioContext();
      console.log(`📊 AudioContext sample rate: ${audioContext.current.sampleRate}Hz`);

      // Load AudioWorklet processor
      try {
        await audioContext.current.audioWorklet.addModule('/audio-processor-worklet.js');
        console.log("✅ AudioWorklet module loaded");
      } catch (error) {
        console.warn("❌ AudioWorklet not supported, falling back to ScriptProcessor");
        // Fall back to ScriptProcessor with manual downsampling
        return startRecordingFallback(stream);
      }

      const source = audioContext.current.createMediaStreamSource(stream);
      
      // Create AudioWorklet node
      const workletNode = new AudioWorkletNode(audioContext.current, 'audio-processor-worklet');
      
      // Listen for processed audio data
      workletNode.port.onmessage = (event) => {
        if (!isRecordingActiveRef.current || !ws.current || ws.current.readyState !== WebSocket.OPEN) {
          return;
        }

        const { type, data, samples, sampleRate, durationMs } = event.data;
        
        if (type === 'audioData') {
          console.log(`📡 Sending downsampled PCM: ${data.byteLength} bytes (${samples} samples @ ${sampleRate}Hz, ${durationMs.toFixed(1)}ms)`);
          ws.current.send(data);
        }
      };

      // Connect the audio graph
      source.connect(workletNode);
      // Note: AudioWorklet doesn't need to be connected to destination
      
      // Store references for cleanup
      audioProcessor.current = workletNode;

      console.log("✅ AudioWorklet PCM recording started with proper 48kHz→16kHz downsampling");

    } catch (error) {
      console.error("❌ Failed to start recording:", error);
      setConnectionError(`Recording failed: ${error}`);
      isRecordingActiveRef.current = false;
      setIsRecording(false);
    }
  }, [isConnected, sttState.state, isRecording]);

  // Fallback method using ScriptProcessor with manual downsampling and proper buffering
  const startRecordingFallback = async (stream: MediaStream) => {
    console.log("🔄 Using ScriptProcessor fallback with downsampling and buffering...");
    
    const source = audioContext.current!.createMediaStreamSource(stream);
    
    // Use larger buffer for ScriptProcessor to ensure we meet 50ms minimum
    const processor = audioContext.current!.createScriptProcessor(4096, 1, 1);
    let pcmBuffer: Int16Array[] = [];
    let sampleCounter = 0;
    const downsampleRatio = Math.round(audioContext.current!.sampleRate / 16000); // e.g., 48000/16000 = 3
    const minSamples = 800; // 50ms at 16kHz - AssemblyAI minimum
    
    console.log(`📊 ScriptProcessor: ${audioContext.current!.sampleRate}Hz → 16kHz (ratio: ${downsampleRatio})`);
    
    processor.onaudioprocess = (event) => {
      if (!isRecordingActiveRef.current || !ws.current || ws.current.readyState !== WebSocket.OPEN) {
        return;
      }

      const inputBuffer = event.inputBuffer;
      const inputData = inputBuffer.getChannelData(0);
      const chunk: number[] = [];
      
      // Downsample and convert to Int16
      for (let i = 0; i < inputData.length; i++) {
        if (sampleCounter % downsampleRatio === 0) {
          const sample = Math.max(-1, Math.min(1, inputData[i]));
          const int16Sample = Math.round(sample * 32767);
          chunk.push(int16Sample);
        }
        sampleCounter++;
      }
      
      if (chunk.length > 0) {
        pcmBuffer.push(new Int16Array(chunk));
        
        // Calculate total buffered samples
        const totalSamples = pcmBuffer.reduce((sum, buffer) => sum + buffer.length, 0);
        
        // Send when we have enough samples (≥50ms at 16kHz)
        if (totalSamples >= minSamples) {
          // Merge all chunks into single buffer
          const merged = new Int16Array(totalSamples);
          let offset = 0;
          pcmBuffer.forEach(buffer => {
            merged.set(buffer, offset);
            offset += buffer.length;
          });
          
          const durationMs = (totalSamples / 16000) * 1000;
          console.log(`📡 Sending buffered PCM (fallback): ${merged.byteLength} bytes (${totalSamples} samples @ 16kHz, ${durationMs.toFixed(1)}ms)`);
          ws.current.send(merged.buffer);
          
          // Reset buffer
          pcmBuffer = [];
        }
      }
    };

    // Connect the audio graph
    source.connect(processor);
    processor.connect(audioContext.current!.destination);
    
    audioProcessor.current = processor;
    console.log("✅ ScriptProcessor fallback started with buffering for 50ms+ chunks");
  };

  const stopRecording = useCallback(() => {
    console.log("🛑 Stopping PCM recording...");
    
    isRecordingActiveRef.current = false;
    setIsRecording(false);

    // Stop AudioContext and ScriptProcessor
    if (audioProcessor.current) {
      audioProcessor.current.disconnect();
      audioProcessor.current = null;
    }

    if (audioContext.current) {
      audioContext.current.close();
      audioContext.current = null;
    }

    // Stop MediaRecorder if it exists (fallback)
    if (mediaRecorder.current && mediaRecorder.current.state === "recording") {
      mediaRecorder.current.stop();
      mediaRecorder.current = null;
    }

    if (audioStream.current) {
      audioStream.current.getTracks().forEach(track => track.stop());
      audioStream.current = null;
    }

    // DON'T close socket here - wait for server to indicate processing is complete
    console.log("✅ PCM recording stopped - keeping socket open for final transcriptions");
  }, []);

  // Connection management
  const disconnect = useCallback(() => {
    console.log("🔌 Manually disconnecting...");
    isManuallyDisconnected.current = true;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    stopRecording();
    
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.close(1000, "Manual disconnect");
    }
  }, [stopRecording]);

  const reconnect = useCallback(() => {
    console.log("🔄 Manual reconnection requested...");
    isManuallyDisconnected.current = false;
    connectionAttempts.current = 0;
    connect();
  }, [connect]);

  // Utility functions
  const resetSession = useCallback(() => {
    console.log("🔄 Resetting session state");
    setMessages([]);
    hasReceivedTranscription.current = false;
    connectionAttempts.current = 0;
    setConnectionError(null);
    setIsProcessingComplete(false);
    isManuallyDisconnected.current = false;
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const forceReconnect = useCallback(() => {
    console.log("🔄 Force reconnection requested - resetting state");
    isManuallyDisconnected.current = false;
    connectionAttempts.current = 0;
    setConnectionError(null);
    connect();
  }, [connect]);

  const getSessionSummary = useCallback(() => {
    const transcripts = messages.filter(m => m.type === 'transcription');
    const riskAssessments = messages.filter(m => m.type === 'risk_assessment');
    
    return {
      totalMessages: messages.length,
      transcripts: transcripts.length,
      riskAssessments: riskAssessments.length,
      sessionDuration: Date.now() - (messages[0]?.timestamp ? new Date(messages[0].timestamp).getTime() : Date.now())
    };
  }, [messages]);

  // Auto-reconnect after delay
  const autoReconnect = useCallback(() => {
    if (connectionAttempts.current >= 5) {
      console.log("❌ Max reconnection attempts reached");
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, connectionAttempts.current), 30000);
    console.log(`🔄 Auto-reconnecting in ${delay}ms... (attempt ${connectionAttempts.current + 1})`);
    
    reconnectTimeoutRef.current = window.setTimeout(() => {
      connectionAttempts.current++;
      connect();
    }, delay);
  }, [connect]);

  // Effect for initial connection - GUARDS AGAINST REACT STRICT MODE (Fix #1)
  useEffect(() => {
    // Fix #1: Guard against React Strict Mode double mounting
    // StrictMode intentionally mounts components twice in development
    if (hasInitialised.current) {
      console.log("🚫 Skipping duplicate mount (React Strict Mode)");
      return;
    }
    
    console.log("📡 Component mounting - initiating WebSocket connection");
    hasInitialised.current = true;
    isManuallyDisconnected.current = false;
    connectionAttempts.current = 0;
    setIsProcessingComplete(false);
    connect();

    return () => {
      console.log("🧹 Component unmounting - checking if cleanup is safe...");
      
      // ENHANCED GUARD: Only cleanup if this is a REAL unmount, not StrictMode
      // In StrictMode, hasInitialised stays true even during cleanup
      if (!hasInitialised.current) {
        console.log("⚠️ Skipping cleanup - looks like StrictMode double-mount");
        return;
      }
      
      // Only reset hasInitialised on real unmount
      const isRealUnmount = !document.contains(document.querySelector('[data-reactroot]')) ||
                           isManuallyDisconnected.current ||
                           (!isRecordingActiveRef.current && !hasReceivedTranscription.current);
      
      if (isRealUnmount) {
        console.log("✅ Real unmount detected - cleaning up WebSocket");
        hasInitialised.current = false; // Reset for next real mount
        isManuallyDisconnected.current = true;
        
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        
        // Clean up audio resources
        if (audioWorkletNode.current) {
          audioWorkletNode.current.disconnect();
          audioWorkletNode.current = null;
        }
        
        if (audioContext.current) {
          audioContext.current.close();
          audioContext.current = null;
        }
        
        if (mediaRecorder.current && mediaRecorder.current.state === "recording") {
          mediaRecorder.current.stop();
        }
        
        if (audioStream.current) {
          audioStream.current.getTracks().forEach(track => track.stop());
          audioStream.current = null;
        }
        
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.close(1000, "Component unmounting");
        }
      } else {
        console.log("⚠️ Ignoring cleanup - StrictMode or partial unmount detected");
      }
    };
  }, []); // Empty dependency array - only run on mount/unmount

  // End session properly (wait for server confirmation)
  const endSession = useCallback(async () => {
    console.log("🏁 Ending session properly...");
    
    // Stop recording first
    if (isRecording) {
      stopRecording();
    }
    
    // Send end session command and wait for server response
    return new Promise<void>((resolve) => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        try {
          ws.current.send(JSON.stringify({ command: "end_session" }));
          console.log("📤 Sent end_session command - waiting for server response");
        } catch (error) {
          console.log("Failed to send end_session command:", error);
        }
      }
      
      // Set up timeout fallback in case server doesn't respond
      const fallbackTimeout = setTimeout(() => {
        console.log("⏰ Timeout waiting for session end - closing anyway");
        isManuallyDisconnected.current = true;
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.close(1000, "Session ended (timeout)");
        }
        resolve();
      }, 5000); // 5 second fallback
      
      // Listen for processing complete signal
      const checkComplete = () => {
        if (isProcessingComplete) {
          clearTimeout(fallbackTimeout);
          isManuallyDisconnected.current = true;
          console.log("✅ Session ended gracefully after server confirmation");
          resolve();
        } else {
          // Check again in 100ms
          setTimeout(checkComplete, 100);
        }
      };
      
      checkComplete();
    });
  }, [isRecording, stopRecording, isProcessingComplete]);

  return { 
    messages, 
    isConnected, 
    sttState,
    isRecording,
    connectionError,
    audioConfig,
    isProcessingComplete, // New state to track STT completion
    sessionId: currentSessionId,
    // Expose live transcription text for UI
    lastPartial: sttState.lastPartial,
    startRecording,
    stopRecording,
    disconnect,
    reconnect,
    forceReconnect, // Force reconnect after hitting limits
    endSession, // Proper session ending function
    getSessionSummary,
    resetSession,
    clearMessages
  };
}