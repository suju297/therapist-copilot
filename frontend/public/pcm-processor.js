// public/pcm-processor.js
// AudioWorklet processor for 16kHz PCM conversion

class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 1024; // Process in chunks
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    
    if (input.length > 0) {
      const inputChannel = input[0]; // First channel only (mono)
      
      for (let i = 0; i < inputChannel.length; i++) {
        // Add sample to buffer
        this.buffer[this.bufferIndex] = inputChannel[i];
        this.bufferIndex++;
        
        // When buffer is full, convert and send
        if (this.bufferIndex >= this.bufferSize) {
          this.sendPCMData();
          this.bufferIndex = 0;
        }
      }
    }
    
    return true; // Keep processor alive
  }
  
  sendPCMData() {
    // Convert Float32 samples to Int16 PCM
    const pcm16 = new Int16Array(this.bufferSize);
    
    for (let i = 0; i < this.bufferSize; i++) {
      // Clamp to [-1, 1] and convert to 16-bit integer
      const sample = Math.max(-1, Math.min(1, this.buffer[i]));
      pcm16[i] = Math.round(sample * 32767);
    }
    
    // Send the raw PCM data
    this.port.postMessage(pcm16.buffer);
  }
}

registerProcessor('pcm-processor', PCMProcessor);