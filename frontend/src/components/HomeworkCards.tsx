// --- src/components/HomeworkCards.tsx ---
interface HW {
    id: string;
    title: string;
    body: string;
    done: boolean;
  }
  interface Props {
    items: HW[];
    locked: boolean;
    onToggle: (id: string) => void;
    onSend: () => void;
  }
  export default function HomeworkCards({ items, locked, onToggle, onSend }: Props) {
    return (
      <div className="bg-white rounded-2xl shadow p-4">
        <h2 className="font-semibold mb-2">Homework</h2>
        <div className="space-y-2 max-h-60 overflow-y-auto">
          {items.map((hw) => (
            <label
              key={hw.id}
              className="flex items-start gap-2 bg-gray-50 p-2 rounded-lg border"
            >
              <input
                type="checkbox"
                checked={hw.done}
                onChange={() => onToggle(hw.id)}
                disabled={locked}
                className="mt-1"
              />
              <span>
                <strong>{hw.title}</strong>
                <br />
                <span className="text-sm text-gray-600 whitespace-pre-line">{hw.body}</span>
              </span>
            </label>
          ))}
        </div>
        <button
          onClick={onSend}
          disabled={locked}
          className="mt-3 bg-blue-600 text-white px-4 py-1.5 rounded-lg disabled:opacity-50"
        >
          Send Homework
        </button>
      </div>
    );
  }
