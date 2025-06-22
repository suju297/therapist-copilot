// --- src/components/QrModal.tsx ---
import { X } from "lucide-react";
interface Props {
  open: boolean;
  pngPath?: string;
  onClose: () => void;
}
export default function QrModal({ open, pngPath, onClose }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
      <div className="bg-white p-4 rounded-2xl shadow-xl relative">
        <button onClick={onClose} className="absolute top-2 right-2">
          <X className="w-5 h-5" />
        </button>
        <img src={pngPath} alt="Homework QR" className="w-60 h-60 object-contain" />
      </div>
    </div>
  );
}
