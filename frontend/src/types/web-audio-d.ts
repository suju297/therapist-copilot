// src/types/web-audio.d.ts
// TypeScript declarations for Web Audio API features

// Extend the existing AudioContext interface if needed
interface AudioContext {
  audioWorklet: AudioWorklet;
}

// AudioWorklet and AudioWorkletNode types (if not available)
interface AudioWorklet {
  addModule(moduleURL: string): Promise<void>;
}

interface AudioWorkletNode extends AudioNode {
  port: MessagePort;
}

interface AudioWorkletNodeOptions extends AudioNodeOptions {
  numberOfInputs?: number;
  numberOfOutputs?: number;
  outputChannelCount?: number[];
  parameterData?: Record<string, number>;
  processorOptions?: any;
}

// Constructor for AudioWorkletNode
declare var AudioWorkletNode: {
  prototype: AudioWorkletNode;
  new(context: BaseAudioContext, name: string, options?: AudioWorkletNodeOptions): AudioWorkletNode;
};

// MessagePort interface (should be available but just in case)
interface MessagePort {
  onmessage: ((this: MessagePort, ev: MessageEvent) => any) | null;
  postMessage(message: any): void;
  start(): void;
  close(): void;
}