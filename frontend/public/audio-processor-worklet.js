// public/audio-processor-worklet.js
// Place this file in your public/ directory so Vite can serve it

class AudioProcessorWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.downsampleRatio = 3; // 48kHz → 16kHz (48000 / 16000 = 3)
    this.sampleCounter = 0;
    this.targetSamples = 800; // 50ms at 16kHz (800/16000 = 0.05s) - AssemblyAI minimum
    
    console.log('🔧 AudioWorklet initialized - 48kHz→16kHz, ≥50ms chunks for AssemblyAI');
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    
    if (input.length > 0) {
      const inputChannel = input[0]; // Get first (mono) channel
      
      // Downsample: Take every 3rd sample to convert 48kHz → 16kHz
      for (let i = 0; i < inputChannel.length; i++) {
        if (this.sampleCounter % this.downsampleRatio === 0) {
          // Convert Float32 (-1.0 to 1.0) to Int16 (-32768 to 32767)
          const sample = Math.max(-1, Math.min(1, inputChannel[i]));
          const int16Sample = Math.round(sample * 32767);
          
          this.buffer.push(int16Sample);
          
          // Send chunk when we have enough samples (≥50ms worth at 16kHz)
          if (this.buffer.length >= this.targetSamples) {
            const chunk = new Int16Array(this.buffer);
            
            // Post the PCM data to main thread
            this.port.postMessage({
              type: 'audioData',
              data: chunk.buffer, // ArrayBuffer
              samples: chunk.length,
              sampleRate: 16000,
              durationMs: (chunk.length / 16000) * 1000
            });
            
            this.buffer = []; // Reset buffer
          }
        }
        this.sampleCounter++;
      }
    }
    
    // Keep the processor alive
    return true;
  }
}

registerProcessor('audio-processor-worklet', AudioProcessorWorklet);