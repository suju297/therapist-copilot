// --- src/components/SoapEditor.tsx ---
import { useState } from "react";

export interface SoapData {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  draft: boolean;
}

interface Props {
  data: SoapData;
  onChange: (d: SoapData) => void;
}

export default function SoapEditor({ data, onChange }: Props) {
  const [local, setLocal] = useState<SoapData>(data);

  const update = (field: keyof SoapData, value: string) => {
    const next = { ...local, [field]: value };
    setLocal(next);
    onChange(next);
  };

  return (
    <div className="bg-white rounded-2xl shadow p-4 relative">
      {local.draft && (
        <span className="absolute top-2 right-3 text-xs text-gray-500">AI DRAFT – review required</span>
      )}
      {(["subjective", "objective", "assessment", "plan"] as const).map((field) => (
        <div key={field} className="mb-3">
          <label className="block text-sm font-medium capitalize mb-1">{field}</label>
          <textarea
            className="w-full border rounded-lg p-2 text-sm"
            rows={field === "plan" ? 4 : 2}
            value={local[field]}
            onChange={(e) => update(field, e.target.value)}
          />
        </div>
      ))}
    </div>
  );
}
