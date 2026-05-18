"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api";

type SourceDocumentSummary = {
  id: number;
  canonical_url: string;
  title: string;
  neutral_citation?: string | null;
  court?: string | null;
  judgment_date?: string | null;
  topic_tags: string[];
  source_format: string;
  fetch_status: string;
  indexed_at?: string | null;
  stored_at?: string | null;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
  text_length: number;
  chunk_count: number;
  last_ingestion_run_id?: number | null;
};

type SourceChunk = {
  id: number;
  chunk_index: number;
  text: string;
  text_hash: string;
  section_label?: string | null;
  pinecone_vector_id?: string | null;
  created_at: string;
};

type SourceDocumentDetail = SourceDocumentSummary & {
  normalized_text?: string | null;
  chunks: SourceChunk[];
};

type DocumentListResponse = {
  documents: SourceDocumentSummary[];
  total: number;
  page: number;
  page_size: number;
};

const pageSize = 12;
const statusOptions = [
  { value: "", label: "All status" },
  { value: "stored", label: "Stored" },
  { value: "indexed", label: "Indexed" },
  { value: "failed", label: "Failed" },
  { value: "skipped", label: "Skipped" },
];

export function SourceLibrary() {
  const [documents, setDocuments] = useState<SourceDocumentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<SourceDocumentDetail | null>(null);
  const [draftQuery, setDraftQuery] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<"text" | "chunks">("text");
  const selectedIdRef = useRef<number | null>(null);

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  const loadDetail = useCallback(async (documentId: number) => {
    setLoadingDetail(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}admin/kenyalaw/documents/${documentId}`);
      if (!res.ok) throw new Error("Unable to load the selected source document");
      const nextDetail: SourceDocumentDetail = await res.json();
      setDetail(nextDetail);
      setDetailTab("text");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load source document");
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (query) params.set("q", query);
      if (status) params.set("status", status);

      const res = await fetch(`${API_BASE_URL}admin/kenyalaw/documents?${params.toString()}`);
      if (!res.ok) throw new Error("Unable to load Kenya Law source library");
      const payload: DocumentListResponse = await res.json();
      setDocuments(payload.documents);
      setTotal(payload.total);

      const currentSelected = selectedIdRef.current;
      const currentStillVisible = payload.documents.some((document) => document.id === currentSelected);
      if (!currentSelected || !currentStillVisible) {
        const firstDocument = payload.documents[0] ?? null;
        setSelectedId(firstDocument?.id ?? null);
        if (firstDocument) {
          void loadDetail(firstDocument.id);
        } else {
          setDetail(null);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load source library");
    } finally {
      setLoadingList(false);
    }
  }, [loadDetail, page, query, status]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const selectedSummary = useMemo(
    () => documents.find((document) => document.id === selectedId) ?? null,
    [documents, selectedId],
  );
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const firstVisible = total ? (page - 1) * pageSize + 1 : 0;
  const lastVisible = Math.min(page * pageSize, total);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setQuery(draftQuery.trim());
  }

  function selectDocument(documentId: number) {
    setSelectedId(documentId);
    void loadDetail(documentId);
  }

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(420px,1.05fr)]">
      <section className="ld-card overflow-hidden">
        <div className="border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="ld-card-label">Source library</p>
              <h3 className="mt-1 text-lg font-extrabold text-slate-900">Fetched Kenya Law documents</h3>
            </div>
            <button className="ld-secondary-action" onClick={() => loadDocuments()} disabled={loadingList}>
              <i className="fas fa-rotate" aria-hidden="true"></i> Refresh
            </button>
          </div>

          <form className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-[minmax(0,1fr)_160px_auto]" onSubmit={submitSearch}>
            <label className="relative block">
              <i className="fas fa-magnifying-glass pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400" aria-hidden="true"></i>
              <input
                className="h-10 w-full rounded-md border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm font-semibold text-slate-800 outline-none transition focus:border-blue-400 focus:bg-white"
                value={draftQuery}
                onChange={(event) => setDraftQuery(event.target.value)}
                placeholder="Search title, citation, court, URL"
              />
            </label>
            <select
              className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 outline-none focus:border-blue-400"
              value={status}
              onChange={(event) => {
                setPage(1);
                setStatus(event.target.value);
              }}
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <button className="rounded-md bg-slate-950 px-4 text-sm font-extrabold text-white transition hover:bg-slate-800" type="submit">
              <i className="fas fa-arrow-right" aria-hidden="true"></i>
            </button>
          </form>
        </div>

        {error ? (
          <div className="border-b border-red-100 bg-red-50 px-5 py-3 text-sm font-bold text-red-700">{error}</div>
        ) : null}

        <div className="max-h-[760px] overflow-auto bg-white">
          {loadingList ? (
            <LibraryEmptyState icon="fa-spinner fa-spin" title="Loading sources" />
          ) : documents.length ? (
            <div className="divide-y divide-slate-100">
              {documents.map((document) => (
                <button
                  key={document.id}
                  className={`grid w-full grid-cols-[minmax(0,1fr)_auto] gap-4 px-5 py-4 text-left transition hover:bg-slate-50 ${
                    selectedId === document.id ? "bg-blue-50/70" : "bg-white"
                  }`}
                  onClick={() => selectDocument(document.id)}
                >
                  <span className="min-w-0">
                    <span className="flex flex-wrap items-center gap-2">
                      <SourceStatusPill status={document.fetch_status} />
                      {document.neutral_citation ? (
                        <span className="font-mono text-[11px] font-bold text-slate-500">{document.neutral_citation}</span>
                      ) : null}
                    </span>
                    <span className="mt-2 block truncate text-sm font-extrabold text-slate-950">{document.title}</span>
                    <span className="mt-1 block truncate text-xs font-semibold text-slate-500">
                      {document.court ?? "Unknown court"} {document.judgment_date ? `- ${document.judgment_date}` : ""}
                    </span>
                    <span className="mt-3 flex flex-wrap gap-1.5">
                      {document.topic_tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="rounded bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">
                          {tag}
                        </span>
                      ))}
                    </span>
                  </span>
                  <span className="grid justify-items-end gap-2 text-right">
                    <span className="font-mono text-[11px] font-bold text-slate-400">#{document.id}</span>
                    <span className="text-xs font-bold text-slate-600">{document.chunk_count} chunks</span>
                    <span className="text-xs font-semibold text-slate-400">{formatCount(document.text_length)} chars</span>
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <LibraryEmptyState icon="fa-file-circle-question" title="No stored source documents" />
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-slate-50 px-5 py-3 text-xs font-bold text-slate-500">
          <span>
            {firstVisible}-{lastVisible} of {total}
          </span>
          <div className="flex items-center gap-2">
            <button
              className="rounded-md border border-slate-200 bg-white px-3 py-2 text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={page <= 1 || loadingList}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              <i className="fas fa-arrow-left" aria-hidden="true"></i>
            </button>
            <span className="font-mono text-[11px]">
              {page} / {totalPages}
            </span>
            <button
              className="rounded-md border border-slate-200 bg-white px-3 py-2 text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={page >= totalPages || loadingList}
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            >
              <i className="fas fa-arrow-right" aria-hidden="true"></i>
            </button>
          </div>
        </div>
      </section>

      <SourceDocumentReader
        detail={detail}
        detailTab={detailTab}
        loading={loadingDetail}
        selectedSummary={selectedSummary}
        setDetailTab={setDetailTab}
      />
    </div>
  );
}

function SourceDocumentReader({
  detail,
  detailTab,
  loading,
  selectedSummary,
  setDetailTab,
}: {
  detail: SourceDocumentDetail | null;
  detailTab: "text" | "chunks";
  loading: boolean;
  selectedSummary: SourceDocumentSummary | null;
  setDetailTab: (tab: "text" | "chunks") => void;
}) {
  const activeDocument = detail ?? selectedSummary;

  return (
    <aside className="ld-card min-h-[620px] overflow-hidden bg-white">
      {activeDocument ? (
        <>
          <div className="border-b border-slate-200 bg-white px-6 py-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <SourceStatusPill status={activeDocument.fetch_status} />
                  {activeDocument.last_ingestion_run_id ? (
                    <span className="status-badge status-slate">Run #{activeDocument.last_ingestion_run_id}</span>
                  ) : null}
                </div>
                <h3 className="mt-3 text-xl font-extrabold leading-tight text-slate-950">{activeDocument.title}</h3>
                <p className="mt-2 text-sm font-semibold leading-6 text-slate-500">
                  {activeDocument.court ?? "Unknown court"} {activeDocument.judgment_date ? `- ${activeDocument.judgment_date}` : ""}
                </p>
              </div>
              <a
                className="ld-secondary-action"
                href={activeDocument.canonical_url}
                rel="noreferrer"
                target="_blank"
              >
                <i className="fas fa-up-right-from-square" aria-hidden="true"></i> Source
              </a>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
              <ReaderStat label="Citation" value={activeDocument.neutral_citation ?? "--"} />
              <ReaderStat label="Chunks" value={activeDocument.chunk_count} />
              <ReaderStat label="Text" value={formatCount(activeDocument.text_length)} />
              <ReaderStat label="Seen" value={formatShortDate(activeDocument.last_seen_at)} />
            </div>
          </div>

          <div className="flex border-b border-slate-200 bg-slate-50 p-1">
            <ReaderTab active={detailTab === "text"} icon="fa-file-lines" label="Text" onClick={() => setDetailTab("text")} />
            <ReaderTab active={detailTab === "chunks"} icon="fa-layer-group" label="Chunks" onClick={() => setDetailTab("chunks")} />
          </div>

          <div className="max-h-[720px] overflow-auto bg-white">
            {loading ? (
              <LibraryEmptyState icon="fa-spinner fa-spin" title="Loading document" />
            ) : detailTab === "chunks" ? (
              <ChunkList chunks={detail?.chunks ?? []} />
            ) : (
              <article className="source-reader px-7 py-6">
                {detail?.normalized_text ? (
                  <pre className="whitespace-pre-wrap font-serif text-[15px] leading-8 text-slate-900">{detail.normalized_text}</pre>
                ) : (
                  <LibraryEmptyState icon="fa-file-circle-question" title="No readable text stored" />
                )}
              </article>
            )}
          </div>
        </>
      ) : (
        <LibraryEmptyState icon="fa-scale-balanced" title="Select a source document" />
      )}
    </aside>
  );
}

function ChunkList({ chunks }: { chunks: SourceChunk[] }) {
  if (!chunks.length) {
    return <LibraryEmptyState icon="fa-layer-group" title="No chunks stored" />;
  }

  return (
    <div className="divide-y divide-slate-100">
      {chunks.map((chunk) => (
        <article key={chunk.id} className="px-6 py-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="status-badge status-blue">Chunk {chunk.chunk_index + 1}</span>
              <span className="status-badge status-slate">{chunk.section_label ?? "unknown"}</span>
            </div>
            {chunk.pinecone_vector_id ? (
              <span className="font-mono text-[10px] font-bold text-slate-400">{chunk.pinecone_vector_id}</span>
            ) : null}
          </div>
          <p className="whitespace-pre-wrap text-sm font-semibold leading-7 text-slate-800">{chunk.text}</p>
        </article>
      ))}
    </div>
  );
}

function ReaderStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="font-mono text-[10px] font-extrabold uppercase tracking-[0.12em] text-slate-400">{label}</p>
      <p className="mt-1 truncate font-extrabold text-slate-800">{value}</p>
    </div>
  );
}

function ReaderTab({
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
      className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-extrabold transition ${
        active ? "bg-white text-blue-700 shadow-sm" : "text-slate-500 hover:text-slate-800"
      }`}
      onClick={onClick}
    >
      <i className={`fas ${icon}`} aria-hidden="true"></i> {label}
    </button>
  );
}

function SourceStatusPill({ status }: { status: string }) {
  return <span className={`status-badge ${sourceStatusClass(status)}`}>{status}</span>;
}

function sourceStatusClass(status: string) {
  if (status === "indexed") return "status-green";
  if (status === "stored" || status === "fetched") return "status-blue";
  if (status === "failed") return "status-red";
  if (status === "skipped") return "status-amber";
  return "status-slate";
}

function LibraryEmptyState({ icon, title }: { icon: string; title: string }) {
  return (
    <div className="grid min-h-64 place-items-center px-6 py-12 text-center">
      <div>
        <div className="mx-auto grid h-11 w-11 place-items-center rounded-lg bg-slate-100 text-slate-500">
          <i className={`fas ${icon}`} aria-hidden="true"></i>
        </div>
        <p className="mt-3 text-sm font-bold text-slate-700">{title}</p>
      </div>
    </div>
  );
}

function formatShortDate(value?: string | null) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("en-KE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function formatCount(value?: number | null) {
  return new Intl.NumberFormat("en-KE").format(value ?? 0);
}
