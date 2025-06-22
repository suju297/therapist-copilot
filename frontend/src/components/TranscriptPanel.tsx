
import { useEffect, useRef } from "react";
import { WSMessage } from "../hooks/useWebSocket";

interface Props {
  stream: WSMessage[];
}

export default function TranscriptPanel({ stream }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [stream]);

  return (
    <div className="flex-1 overflow-y-auto bg-white rounded-2xl shadow p-4">
      {stream
        .filter((m) => m.type === "transcript")
        .map((m, idx) => (
          <p key={idx} className="text-sm">
            {m.payload.speaker}: {m.payload.text}
          </p>
        ))}
      <div ref={bottomRef} />
    </div>
  );
}
