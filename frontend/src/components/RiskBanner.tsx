import { AlertTriangle, CheckCircle } from "lucide-react";

interface Props {
  level: "none" | "high";
  onUnlock: () => void;
  locked: boolean;
}

export default function RiskBanner({ level, onUnlock, locked }: Props) {
  if (level === "none") return null;
  return (
    <div className="flex items-center justify-between bg-red-600 text-white p-3 rounded-xl animate-pulse">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-5 h-5" />
        <span className="font-semibold">High‑risk language detected</span>
      </div>
      {locked && (
        <button
          onClick={onUnlock}
          className="bg-white text-red-600 font-medium px-3 py-1 rounded-lg shadow"
        >
          Unlock
        </button>
      )}
      {!locked && (
        <CheckCircle className="w-5 h-5" />
      )}
    </div>
  );
}
