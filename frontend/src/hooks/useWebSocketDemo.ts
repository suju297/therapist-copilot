// src/hooks/useWebSocketDemo.ts
import { useState, useEffect } from 'react';

interface WSMessage {
  type: "transcript" | "risk" | "unlock";
  payload: any;
  timestamp?: number;
}

export const useWebSocketDemo = (url: string) => {
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  
  useEffect(() => {
    // Simulate connection
    setIsConnected(true);
    
    // Simulate incoming transcript and risk data
    const transcriptMessages: WSMessage[] = [
      { 
        type: 'transcript', 
        payload: { 
          speaker: 'Patient', 
          text: "I've been feeling really overwhelmed lately with everything going on at work." 
        }
      },
      { 
        type: 'transcript', 
        payload: { 
          speaker: 'Therapist', 
          text: "Can you tell me more about what specifically is making you feel overwhelmed?" 
        }
      },
      { 
        type: 'transcript', 
        payload: { 
          speaker: 'Patient', 
          text: "It's just... sometimes I wonder if it would be easier if I wasn't here anymore." 
        }
      },
      { 
        type: 'risk', 
        payload: { 
          level: 'high', 
          confidence: 0.85, 
          indicators: ['suicidal ideation', 'hopelessness'] 
        }
      },
      { 
        type: 'transcript', 
        payload: { 
          speaker: 'Therapist', 
          text: "I'm concerned about what you just shared. Can we talk about those thoughts?" 
        }
      },
      { 
        type: 'transcript', 
        payload: { 
          speaker: 'Patient', 
          text: "I don't really have a plan or anything. I just feel so tired all the time." 
        }
      },
      { 
        type: 'risk', 
        payload: { 
          level: 'medium', 
          confidence: 0.72, 
          indicators: ['fatigue', 'emotional exhaustion'] 
        }
      },
      { 
        type: 'transcript', 
        payload: { 
          speaker: 'Patient', 
          text: "Work has been really stressful. My boss keeps piling on more projects." 
        }
      },
      { 
        type: 'transcript', 
        payload: { 
          speaker: 'Therapist', 
          text: "That sounds really challenging. How are you coping with the stress?" 
        }
      },
      { 
        type: 'transcript', 
        payload: { 
          speaker: 'Patient', 
          text: "I've been trying the breathing exercises we talked about. They help sometimes." 
        }
      },
      { 
        type: 'risk', 
        payload: { 
          level: 'low', 
          confidence: 0.45, 
          indicators: ['positive coping'] 
        }
      },
    ];
    
    let messageIndex = 0;
    const interval = setInterval(() => {
      if (messageIndex < transcriptMessages.length) {
        const message = transcriptMessages[messageIndex];
        setMessages(prev => [...prev, { ...message, timestamp: Date.now() }]);
        messageIndex++;
      } else {
        // Loop back to beginning for demo
        messageIndex = 0;
        setMessages([]); // Clear messages before starting over
      }
    }, 4000);
    
    return () => clearInterval(interval);
  }, [url]);
  
  return { messages, isConnected };
};
