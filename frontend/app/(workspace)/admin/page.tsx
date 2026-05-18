"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { AdminSkeleton } from "./_components/AdminSkeleton";
import { SourceLibrary } from "./_components/SourceLibrary";

type IngestionRun = {
  id: number;
  status: string;
  dry_run: boolean;
  started_at?: string;
  finished_at?: string | null;
  discovered_count: number;
  fetched_count: number;
  indexed_count: number;
  skipped_count: number;
  failed_count: number;
};

type IngestionEvent = {
  id: number;
  ingestion_run_id: number;
  event_type: string;
  stage: string;
  message: string;
  url?: string | null;
  error_type?: string | null;
  counts?: Record<string, unknown> | null;
  created_at: string;
};

type PineconePreflight = {
  status: string;
  message: string;
  index_name?: string | null;
  embedding_model?: string | null;
  embedding_dimension?: number | null;
  index_dimension?: number | null;
  error_type?: string | null;
};

type CorpusStats = {
  documents: number;
  indexed_documents: number;
  chunks: number;
  failed_runs: number;
  latest_run?: IngestionRun | null;
  preflight?: PineconePreflight | null;
};

const emptyStats: CorpusStats = {
  documents: 0,
  indexed_documents: 0,
  chunks: 0,
  failed_runs: 0,
  latest_run: null,
  preflight: null,
};

const steps = [
  { key: "discover", label: "Discover", icon: "fa-magnifying-glass" },
  { key: "fetch", label: "Fetch", icon: "fa-cloud-arrow-down" },
  { key: "filter", label: "Filter", icon: "fa-filter" },
  { key: "store", label: "Store", icon: "fa-file-lines" },
  { key: "index", label: "Index", icon: "fa-database" },
  { key: "verify", label: "Verify", icon: "fa-circle-check" },
];

const stageOrder = steps.map((step) => step.key);
const terminalEvents = new Set(["completed", "failed"]);

export default function AdminScreen() {
  const [stats, setStats] = useState<CorpusStats>(emptyStats);
  const [events, setEvents] = useState<IngestionEvent[]>([]);
  const [activeRun, setActiveRun] = useState<IngestionRun | null>(null);
  const [activeView, setActiveView] = useState<"runs" | "library">("runs");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [connection, setConnection] = useState<"idle" | "connecting" | "live" | "reconnecting" | "closed">("idle");
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const streamRunIdRef = useRef<number | null>(null);
  const loadStatsRef = useRef<(options?: { connectLatest?: boolean }) => Promise<void>>(async () => {});

  const latestEvent = events.at(-1) ?? null;
  const newestEvents = useMemo(() => [...events].reverse(), [events]);
  const preflight = stats.preflight;
  const canFullSync = preflight?.status === "passed";
  const runIsActive = activeRun?.status === "running";
  const dimensionMismatch =
    preflight?.error_type === "pinecone_dimension_mismatch" ||
    newestEvents.some((event) => event.error_type === "pinecone_dimension_mismatch");

  const closeStream = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    streamRunIdRef.current = null;
  }, []);

  const connectToRun = useCallback((runId: number) => {
    if (eventSourceRef.current && streamRunIdRef.current === runId) return;
    closeStream();
    setConnection("connecting");
    streamRunIdRef.current = runId;
    const source = new EventSource(`${API_BASE_URL}admin/kenyalaw/ingestion-runs/${runId}/events`);
    eventSourceRef.current = source;

    source.onopen = () => setConnection("live");
    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as IngestionEvent;
      setEvents((current) => {
        const withoutDuplicate = current.filter((item) => item.id !== event.id);
        return [...withoutDuplicate, event].sort((a, b) => a.id - b.id);
      });
      setActiveRun((current) => updateRunFromEvent(current, event));
      if (terminalEvents.has(event.event_type)) {
        setConnection("closed");
        closeStream();
        void loadStatsRef.current({ connectLatest: false });
      }
    };
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) {
        setConnection("closed");
        return;
      }
      setConnection("reconnecting");
    };
  }, [closeStream]);

  const loadStats = useCallback(async (options: { connectLatest?: boolean } = {}) => {
    const connectLatest = options.connectLatest ?? true;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}admin/kenyalaw/corpus-stats`);
      if (!res.ok) throw new Error("Failed to load Kenya Law corpus stats");
      const nextStats: CorpusStats = await res.json();
      setStats(nextStats);
      if (nextStats.latest_run) {
        setActiveRun((current) => current ?? nextStats.latest_run ?? null);
        if (connectLatest && streamRunIdRef.current !== nextStats.latest_run.id) {
          setEvents([]);
          connectToRun(nextStats.latest_run.id);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load corpus stats");
    } finally {
      setLoading(false);
    }
  }, [connectToRun]);

  async function startIngestion(dryRun: boolean) {
    setStarting(true);
    setError(null);
    setEvents([]);
    try {
      const res = await fetch(`${API_BASE_URL}admin/kenyalaw/ingestion-runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dry_run: dryRun,
          max_pages: 1,
          max_documents: 25,
          start_url: "https://new.kenyalaw.org/judgments/KEELC/",
        }),
      });
      if (!res.ok) throw new Error("Unable to start Kenya Law ingestion");
      const run: IngestionRun = await res.json();
      setActiveRun(run);
      setStats((current) => ({ ...current, latest_run: run }));
      connectToRun(run.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start ingestion");
    } finally {
      setStarting(false);
    }
  }

  useEffect(() => {
    loadStatsRef.current = loadStats;
  }, [loadStats]);

  useEffect(() => {
    void loadStats();
    return closeStream;
  }, [closeStream, loadStats]);

  return (
    <section className="ld-page">
      <div className="ld-page-inner">
        <div className="ld-page-header">
          <div>
            <p className="ld-eyebrow">Ingestion Console</p>
            <h2 className="ld-title">Kenya Law ELC corpus operations.</h2>
            <p className="ld-subtitle">
              Track discovery, filtering, Pinecone indexing, and failures as each run writes operational events.
            </p>
          </div>
          <button className="ld-secondary-action" onClick={() => loadStats()} disabled={loading}>
            <i className="fas fa-rotate" aria-hidden="true"></i> Refresh
          </button>
        </div>

        {loading ? (
          <AdminSkeleton />
        ) : (
          <>
            <div className="mb-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <MetricTile label="Indexed documents" value={stats.indexed_documents} accent="green" icon="fa-scale-balanced" />
              <MetricTile label="Known documents" value={stats.documents} accent="blue" icon="fa-file-lines" />
              <MetricTile label="Vector chunks" value={stats.chunks} accent="slate" icon="fa-layer-group" />
              <MetricTile label="Failed runs" value={stats.failed_runs} accent={stats.failed_runs ? "red" : "green"} icon="fa-triangle-exclamation" />
            </div>

            <div className="mb-5 inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
              <ViewTab active={activeView === "runs"} icon="fa-terminal" label="Runs" onClick={() => setActiveView("runs")} />
              <ViewTab active={activeView === "library"} icon="fa-folder-open" label="Source Library" onClick={() => setActiveView("library")} />
            </div>

            {activeView === "library" ? (
              <SourceLibrary />
            ) : (
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
              <main className="space-y-5">
                <div className="ld-card overflow-hidden">
                  <div className="border-b border-slate-200 bg-white px-5 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="ld-card-label">Run timeline</p>
                        <h3 className="mt-1 text-lg font-extrabold text-slate-900">
                          {activeRun ? `Run #${activeRun.id}` : "No ingestion run selected"}
                        </h3>
                      </div>
                      <StatusPill status={activeRun?.status ?? "idle"} />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 border-b border-slate-200 bg-slate-50 sm:grid-cols-6">
                    {steps.map((step) => {
                      const state = stepState(step.key, latestEvent, activeRun);
                      return (
                        <div key={step.key} className={`min-h-24 border-slate-200 p-4 sm:border-r sm:last:border-r-0 ${stateClasses(state)}`}>
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-mono text-[10px] font-extrabold uppercase tracking-[0.12em]">{step.label}</span>
                            <i className={`fas ${step.icon}`} aria-hidden="true"></i>
                          </div>
                          <p className="mt-3 text-xs font-semibold capitalize">{state}</p>
                        </div>
                      );
                    })}
                  </div>

                  <div className="grid grid-cols-2 gap-0 border-b border-slate-200 bg-white md:grid-cols-5">
                    <Counter label="Discovered" value={activeRun?.discovered_count ?? 0} />
                    <Counter label="Fetched" value={activeRun?.fetched_count ?? 0} />
                    <Counter label="Indexed" value={activeRun?.indexed_count ?? 0} />
                    <Counter label="Skipped" value={activeRun?.skipped_count ?? 0} />
                    <Counter label="Failed" value={activeRun?.failed_count ?? 0} tone="red" />
                  </div>

                  <div className="max-h-[520px] overflow-auto bg-white">
                    {newestEvents.length ? (
                      <div className="divide-y divide-slate-100">
                        {newestEvents.map((event) => (
                          <EventRow key={event.id} event={event} />
                        ))}
                      </div>
                    ) : (
                      <div className="grid min-h-64 place-items-center px-6 py-12 text-center">
                        <div>
                          <div className="mx-auto grid h-11 w-11 place-items-center rounded-lg bg-slate-100 text-slate-500">
                            <i className="fas fa-terminal" aria-hidden="true"></i>
                          </div>
                          <p className="mt-3 text-sm font-bold text-slate-700">No ingestion events yet</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </main>

              <aside className="space-y-5">
                <div className="ld-card p-5">
                  <div className="mb-4 flex items-center justify-between">
                    <div>
                      <p className="ld-card-label">Controls</p>
                      <p className="mt-1 text-sm font-bold text-slate-900">
                        {runIsActive ? "Run in progress" : "Start a corpus run"}
                      </p>
                    </div>
                    <ConnectionPill connection={connection} />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <button
                      className="rounded-md border border-slate-200 px-3 py-3 text-xs font-extrabold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                      onClick={() => startIngestion(true)}
                      disabled={starting || runIsActive}
                    >
                      <i className="fas fa-vial mr-2" aria-hidden="true"></i>Dry-run
                    </button>
                    <button
                      className="rounded-md bg-slate-950 px-3 py-3 text-xs font-extrabold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                      onClick={() => startIngestion(false)}
                      disabled={starting || runIsActive || !canFullSync}
                    >
                      <i className="fas fa-cloud-arrow-up mr-2" aria-hidden="true"></i>Sync 25 cases
                    </button>
                  </div>
                  {!canFullSync ? (
                    <p className="mt-3 text-xs font-semibold leading-5 text-amber-700">
                      Full sync is locked until the Pinecone preflight passes. Dry-run remains available.
                    </p>
                  ) : null}
                  {error ? <p className="mt-3 text-xs font-bold text-red-600">{error}</p> : null}
                </div>

                {dimensionMismatch ? (
                  <RepairCard preflight={preflight} />
                ) : (
                  <PreflightCard preflight={preflight} />
                )}

                <div className="ld-card p-5">
                  <div className="mb-4 flex items-center gap-2 text-slate-700">
                    <i className="fas fa-clock-rotate-left" aria-hidden="true"></i>
                    <p className="ld-card-label">Latest run</p>
                  </div>
                  <div className="space-y-3 text-xs">
                    <SummaryRow label="Status" value={stats.latest_run?.status ?? "No runs"} />
                    <SummaryRow label="Mode" value={stats.latest_run?.dry_run ? "Dry-run" : "Full sync"} />
                    <SummaryRow label="Discovered" value={stats.latest_run?.discovered_count ?? 0} />
                    <SummaryRow label="Indexed" value={stats.latest_run?.indexed_count ?? 0} />
                    <SummaryRow label="Failures" value={stats.latest_run?.failed_count ?? 0} tone="red" />
                  </div>
                </div>
              </aside>
            </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function updateRunFromEvent(current: IngestionRun | null, event: IngestionEvent): IngestionRun | null {
  if (!current || current.id !== event.ingestion_run_id) return current;
  const counts = event.counts ?? {};
  return {
    ...current,
    status: event.event_type === "failed" || event.event_type === "completed" ? event.event_type : current.status,
    discovered_count: countValue(counts.discovered, current.discovered_count),
    fetched_count: countValue(counts.fetched, current.fetched_count),
    indexed_count: countValue(counts.indexed, current.indexed_count),
    skipped_count: countValue(counts.skipped, current.skipped_count),
    failed_count: countValue(counts.failed, current.failed_count),
  };
}

function countValue(value: unknown, fallback: number) {
  return typeof value === "number" ? value : fallback;
}

function stepState(step: string, latestEvent: IngestionEvent | null, run: IngestionRun | null) {
  if (!run) return "idle";
  if (latestEvent?.event_type === "failed" && latestEvent.stage === step) return "failed";
  if (run.status === "completed") return "complete";
  const currentIndex = latestEvent ? stageOrder.indexOf(latestEvent.stage) : -1;
  const stepIndex = stageOrder.indexOf(step);
  if (currentIndex > stepIndex) return "complete";
  if (currentIndex === stepIndex) return "active";
  return "waiting";
}

function stateClasses(state: string) {
  if (state === "complete") return "bg-emerald-50 text-emerald-700";
  if (state === "active") return "bg-blue-50 text-blue-700";
  if (state === "failed") return "bg-red-50 text-red-700";
  return "bg-white text-slate-400";
}

function statusClass(status: string) {
  if (status === "completed" || status === "passed") return "status-green";
  if (status === "failed") return "status-red";
  if (status === "running" || status === "live" || status === "stored" || status === "filtered") return "status-blue";
  if (status === "reconnecting" || status === "connecting") return "status-amber";
  return "status-slate";
}

function formatTime(value?: string | null) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("en-KE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function MetricTile({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: number;
  icon: string;
  accent: "blue" | "green" | "red" | "slate";
}) {
  const colors = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-emerald-50 text-emerald-700",
    red: "bg-red-50 text-red-700",
    slate: "bg-slate-100 text-slate-700",
  };
  return (
    <div className="ld-card p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="ld-card-label">{label}</p>
        <span className={`grid h-9 w-9 place-items-center rounded-md ${colors[accent]}`}>
          <i className={`fas ${icon}`} aria-hidden="true"></i>
        </span>
      </div>
      <p className="mt-4 text-3xl font-extrabold text-slate-950">{value}</p>
    </div>
  );
}

function Counter({ label, value, tone = "slate" }: { label: string; value: number; tone?: "slate" | "red" }) {
  return (
    <div className="border-r border-slate-100 p-4 last:border-r-0">
      <p className="font-mono text-[10px] font-extrabold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-extrabold ${tone === "red" ? "text-red-600" : "text-slate-950"}`}>{value}</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  return <span className={`status-badge ${statusClass(status)}`}>{status}</span>;
}

function ViewTab({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-extrabold transition ${
        active ? "bg-slate-950 text-white" : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
      }`}
      onClick={onClick}
    >
      <i className={`fas ${icon}`} aria-hidden="true"></i> {label}
    </button>
  );
}

function ConnectionPill({ connection }: { connection: string }) {
  return (
    <span className={`status-badge ${statusClass(connection)}`}>
      {connection === "reconnecting" ? "Reconnecting..." : connection}
    </span>
  );
}

function EventRow({ event }: { event: IngestionEvent }) {
  const failed = event.event_type === "failed";
  const indexed = event.event_type === "indexed" || event.event_type === "completed";
  const icon = failed ? "fa-circle-exclamation" : indexed ? "fa-circle-check" : "fa-circle-dot";
  const iconClass = failed ? "bg-red-50 text-red-600" : indexed ? "bg-emerald-50 text-emerald-700" : "bg-blue-50 text-blue-700";
  return (
    <article className="grid grid-cols-[auto_minmax(0,1fr)_auto] gap-3 px-5 py-4">
      <span className={`mt-0.5 grid h-8 w-8 place-items-center rounded-md ${iconClass}`}>
        <i className={`fas ${icon}`} aria-hidden="true"></i>
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`status-badge ${statusClass(event.event_type)}`}>{event.event_type}</span>
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">{event.stage}</span>
          {event.error_type ? <span className="status-badge status-red">{event.error_type}</span> : null}
        </div>
        <p className="mt-2 text-sm font-semibold leading-5 text-slate-800">{event.message}</p>
        {event.url ? <p className="mt-1 truncate font-mono text-[11px] text-slate-500">{event.url}</p> : null}
      </div>
      <time className="whitespace-nowrap pt-1 font-mono text-[11px] font-semibold text-slate-400">{formatTime(event.created_at)}</time>
    </article>
  );
}

function RepairCard({ preflight }: { preflight?: PineconePreflight | null }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-5">
      <div className="mb-3 flex items-center gap-2 text-red-700">
        <i className="fas fa-screwdriver-wrench" aria-hidden="true"></i>
        <p className="font-mono text-[10px] font-extrabold uppercase tracking-[0.12em]">Repair required</p>
      </div>
      <p className="text-sm font-extrabold text-red-950">
        Your Pinecone index is {preflight?.index_dimension ?? "not verified"} dimensions; current embedding model writes{" "}
        {preflight?.embedding_dimension ?? 1536}.
      </p>
      <p className="mt-3 text-xs font-semibold leading-5 text-red-800">
        Create or reconfigure the Pinecone index with dimension 1536, or switch to a 3072-dimensional embedding model if that was intentional.
      </p>
      <p className="mt-3 rounded-md bg-white px-3 py-2 font-mono text-[11px] font-bold text-red-700">
        {preflight?.message ?? "Pinecone index dimension 3072 does not match embedding dimension 1536"}
      </p>
    </div>
  );
}

function PreflightCard({ preflight }: { preflight?: PineconePreflight | null }) {
  const status = preflight?.status ?? "unchecked";
  return (
    <div className="ld-card p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="ld-card-label">Pinecone preflight</p>
          <p className="mt-1 text-sm font-bold text-slate-900">{preflight?.index_name ?? "Index check"}</p>
        </div>
        <StatusPill status={status} />
      </div>
      <p className="text-xs font-semibold leading-5 text-slate-600">
        {preflight?.message ?? "Waiting for Pinecone index verification."}
      </p>
      {preflight?.embedding_model ? (
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          <SummaryRow label="Model" value={preflight.embedding_model} />
          <SummaryRow label="Dimension" value={preflight.embedding_dimension ?? "--"} />
        </div>
      ) : null}
    </div>
  );
}

function SummaryRow({ label, value, tone = "slate" }: { label: string; value: string | number; tone?: "slate" | "red" }) {
  return (
    <div className="flex justify-between gap-3 border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
      <span className="text-slate-500">{label}</span>
      <span className={`min-w-0 truncate text-right font-extrabold ${tone === "red" ? "text-red-600" : "text-slate-800"}`}>{value}</span>
    </div>
  );
}
