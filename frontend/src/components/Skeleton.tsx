const shimmer = "animate-pulse bg-[#dce3e9] rounded-[inherit]";

export function ChartSkeleton() {
  return (
    <div className="min-h-[300px] rounded-[26px] border border-[color:var(--panel-border)] bg-[color:var(--panel)] p-4 shadow-[0_24px_60px_rgba(148,163,184,0.16),inset_0_1px_0_rgba(255,255,255,0.9)] md:min-h-[360px] md:p-6">
      <div className={`h-full w-full ${shimmer}`} />
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-[22px] border border-[color:var(--panel-border)] bg-[color:var(--panel-muted)] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
      <div className={`mb-3 h-3 w-20 ${shimmer}`} />
      <div className={`mb-2 h-7 w-28 ${shimmer}`} />
      <div className={`h-4 w-24 ${shimmer}`} />
    </div>
  );
}

export function SummarySkeleton() {
  return (
    <div className="rounded-[30px] border border-[color:var(--panel-border)] bg-[color:var(--panel)] p-5 shadow-[0_24px_60px_rgba(148,163,184,0.14),inset_0_1px_0_rgba(255,255,255,0.85)] md:p-6">
      <div className={`mb-5 h-3 w-16 ${shimmer}`} />
      <div className="space-y-4">
        <div className={`h-28 rounded-[20px] ${shimmer}`} />
        <div className="grid gap-4 sm:grid-cols-2">
          <div className={`h-20 rounded-[20px] ${shimmer}`} />
          <div className={`h-20 rounded-[20px] ${shimmer}`} />
        </div>
      </div>
    </div>
  );
}

export function HeatmapSkeleton() {
  return (
    <div className="rounded-[30px] border border-[color:var(--panel-border)] bg-[color:var(--panel)] p-5 shadow-[0_24px_60px_rgba(148,163,184,0.14),inset_0_1px_0_rgba(255,255,255,0.88)] md:p-6">
      <div className={`mb-3 h-3 w-24 ${shimmer}`} />
      <div className={`mb-2 h-8 w-72 ${shimmer}`} />
      <div className={`mb-4 h-5 w-56 ${shimmer}`} />
      <div className={`h-32 w-full rounded-[24px] ${shimmer}`} />
    </div>
  );
}
