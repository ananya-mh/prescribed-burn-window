// Tailwind scans source files for complete class strings, so every class name
// here is written out in full. Building them by interpolation (`bg-${x}-100`)
// would compile to no CSS at all.
const BADGE_STYLES = {
  "GO": "bg-green-100 text-green-800 ring-green-600/30",
  "MARGINAL": "bg-yellow-100 text-yellow-800 ring-yellow-600/30",
  "NO-GO": "bg-red-100 text-red-800 ring-red-600/30",
};

const FALLBACK_STYLE = "bg-slate-100 text-slate-700 ring-slate-500/30";

export default function StatusBadge({ status }) {
  const style = BADGE_STYLES[status] || FALLBACK_STYLE;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold tracking-wide ring-1 ring-inset ${style}`}
    >
      {status}
    </span>
  );
}
