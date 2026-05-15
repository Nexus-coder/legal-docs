"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";

type Evidence = {
  id: number;
  citation_type: string;
  title: string;
  source?: string;
  snippet: string;
  confidence: number;
  status: string;
};

type Matter = {
  id: number;
  case_number: string;
  division: string;
  jurisdiction?: string;
  subcategory?: string;
  workflow_state: string;
  masked_facts?: string;
  draft_content?: string;
  drafting_error?: string;
  verification_done: number;
  verification_total: number;
  citation_evidence: Evidence[];
  activities: { id: number; title: string; detail?: string; created_at: string }[];
};

function tokenFromCookie() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("token="))
    ?.split("=")[1];
}

function DraftingWorkspaceContent() {
  const searchParams = useSearchParams();
  const matterId = searchParams.get("matter_id");
  const [matter, setMatter] = useState<Matter | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [error, setError] = useState<string | null>(null);

  const authHeaders = useMemo<Record<string, string>>(() => {
    const headers: Record<string, string> = {};
    const token = tokenFromCookie();
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  }, []);

  useEffect(() => {
    const load = async () => {
      if (!matterId) {
        setLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_BASE_URL}matters/${matterId}`, {
          headers: authHeaders,
        });
        if (!res.ok) throw new Error("Matter not found");
        const data = await res.json();
        setMatter(data);
        if (data.workflow_state === "pii_masked" && !data.draft_content) {
          await generateDraft(data);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load matter");
      } finally {
        setLoading(false);
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matterId]);

  const refreshMatter = async () => {
    if (!matterId) return;
    const res = await fetch(`${API_BASE_URL}matters/${matterId}`, { headers: authHeaders });
    if (res.ok) setMatter(await res.json());
  };

  const generateDraft = async (sourceMatter = matter) => {
    if (!sourceMatter) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}drafting/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({
          matter_id: sourceMatter.id,
          jurisdiction: sourceMatter.jurisdiction || sourceMatter.division,
          subcategory: sourceMatter.subcategory || "Pleading",
        }),
      });
      const data = await res.json();
      if (!res.ok || (data.error_status && !data.blocks?.length)) {
        throw new Error(data.error_status || data.detail || "Draft generation failed");
      }
      if (data.error_status) {
        setError("Draft generated, but the critique loop reached its revision limit. Review the draft manually before relying on it.");
      }
      await refreshMatter();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Draft generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const verifyCitations = async () => {
    if (!matter) return;
    setVerifying(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}matters/${matter.id}/verify-citations`, {
        method: "POST",
        headers: authHeaders,
      });
      if (!res.ok) throw new Error("Citation verification failed");
      const data = await res.json();
      setMatter(data.matter);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Citation verification failed");
    } finally {
      setVerifying(false);
    }
  };

  if (!matterId) {
    return (
      <section className="p-8">
        <div className="rounded-lg border border-slate-200 bg-white p-8">
          <h2 className="text-xl font-bold text-slate-900">Select a matter to draft</h2>
          <p className="mt-2 text-sm text-slate-500">Start from Context & PII or resume an existing matter from the dashboard.</p>
          <Link href="/" className="mt-6 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white">Back to dashboard</Link>
        </div>
      </section>
    );
  }

  if (loading) return <section className="p-8 text-sm text-slate-500">Loading drafting workspace...</section>;
  if (!matter) return <section className="p-8 text-sm text-red-600">{error || "Matter unavailable"}</section>;

  const progress = matter.verification_total
    ? Math.round((matter.verification_done / matter.verification_total) * 100)
    : 0;

  return (
    <section className="flex-1 flex h-full overflow-hidden">
      <div className="w-1/3 border-r border-slate-200 bg-white flex flex-col">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <span className="font-bold text-sm tracking-tight">
            <i className="fas fa-robot text-blue-600 mr-2"></i> AI CO-PILOT
          </span>
          <span className="text-[10px] px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-bold uppercase tracking-widest">
            {generating ? "Generating" : matter.workflow_state.replaceAll("_", " ")}
          </span>
        </div>
        <div className="flex-1 p-6 space-y-6 overflow-y-auto">
          {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-bold text-red-700">{error}</div>}
          <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
            <h4 className="text-xs font-bold text-blue-900 mb-2 uppercase tracking-widest">
              Pleading Block: Grounds
            </h4>
            <div className="space-y-4 text-sm leading-relaxed text-slate-700">
              <p className="font-bold border-b pb-1">PROPOSED DRAFT: {(matter.subcategory || "PLEADING").toUpperCase()}</p>
              <p className="whitespace-pre-wrap">
                {matter.draft_content || (generating ? "Generating from masked facts..." : "No draft has been generated yet.")}
              </p>
            </div>
            {!matter.draft_content && (
              <button onClick={() => generateDraft()} disabled={generating} className="mt-4 rounded bg-blue-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">
                Generate Draft
              </button>
            )}
          </div>
          <div className="p-4 border border-slate-200 rounded-lg bg-white shadow-sm">
            <h4 className="text-xs font-bold text-slate-500 mb-3 uppercase tracking-widest">Activity Timeline</h4>
            <div className="space-y-3">
              {matter.activities.map((activity) => (
                <div key={activity.id} className="border-l-2 border-slate-200 pl-3">
                  <p className="text-xs font-bold text-slate-700">{activity.title}</p>
                  {activity.detail && <p className="text-[11px] text-slate-500">{activity.detail}</p>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-slate-100 flex flex-col">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white shadow-sm">
          <span className="font-bold text-sm text-slate-600 uppercase tracking-widest">
            <i className="fas fa-book-open mr-2 text-amber-500"></i> Citation Evidence
          </span>
          <span className="px-3 py-1 bg-slate-200 text-slate-700 text-xs rounded-full font-bold">
            {matter.case_number}
          </span>
        </div>
        <div className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-2xl mx-auto bg-white p-10 shadow-lg min-h-full border-t-4 border-amber-400">
            <h5 className="font-serif text-lg font-bold text-center">REPUBLIC OF KENYA</h5>
            <p className="font-serif text-sm text-center">{matter.jurisdiction || matter.division}</p>
            <div className="border-y my-4 py-2 uppercase text-xs font-bold text-center">
              {matter.subcategory || "Pleading"} Evidence Review
            </div>
            <div className="space-y-4">
              {matter.citation_evidence.length ? matter.citation_evidence.map((item) => (
                <button key={item.id} onClick={() => setSelectedEvidence(item)} className="w-full text-left rounded-lg border border-slate-200 p-4 hover:border-blue-300 hover:bg-blue-50 transition">
                  <p className="text-xs font-bold uppercase text-blue-700">{item.citation_type}</p>
                  <p className="mt-1 font-bold text-slate-800">{item.title}</p>
                  <p className="mt-2 line-clamp-2 text-sm text-slate-600">{item.snippet}</p>
                </button>
              )) : (
                <p className="py-20 text-center text-slate-500">Citation evidence appears after draft generation.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="w-80 bg-slate-50 border-l border-slate-200 flex flex-col">
        <div className="p-4 border-b border-slate-200 bg-white">
          <h4 className="font-bold text-sm flex items-center">
            <i className="fas fa-check-double text-green-600 mr-2"></i> Verification Checklist
          </h4>
          <div className="w-full bg-slate-200 h-1.5 rounded-full mt-3 overflow-hidden">
            <div className="bg-green-500 h-full transition-all" style={{ width: `${progress}%` }}></div>
          </div>
          <p className="text-[10px] text-slate-500 mt-2 font-bold uppercase">
            {matter.verification_done} of {matter.verification_total} citations approved
          </p>
        </div>
        <div className="flex-1 p-4 space-y-4 overflow-y-auto">
          {matter.citation_evidence.map((item) => (
            <div key={item.id} className="p-3 bg-white border border-blue-200 rounded-lg shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-[10px] font-bold text-blue-700 uppercase">{item.citation_type}</span>
                <span className={`text-[10px] font-bold uppercase ${item.status === "verified" ? "text-green-600" : "text-amber-600"}`}>{item.status}</span>
              </div>
              <p className="text-xs font-bold mb-1">{item.title}</p>
              <p className="text-[10px] text-slate-600 mb-3">Matching Confidence: {Math.round(item.confidence * 100)}%</p>
              <button onClick={() => setSelectedEvidence(item)} className="w-full py-1.5 bg-blue-600 text-white text-xs font-bold rounded shadow-md hover:bg-blue-700">
                Inspect Evidence
              </button>
            </div>
          ))}
        </div>
        <div className="p-4 border-t border-slate-200 bg-white space-y-2">
          <button onClick={verifyCitations} disabled={verifying || !matter.citation_evidence.length} className="w-full py-3 bg-green-600 text-white font-bold rounded-lg disabled:opacity-50">
            Verify Citations
          </button>
          <button disabled className="w-full py-3 bg-slate-200 text-slate-400 font-bold rounded-lg cursor-not-allowed">
            <i className="fas fa-file-export mr-2"></i> Export to .docx
          </button>
        </div>
      </div>

      {selectedEvidence && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30" onClick={() => setSelectedEvidence(null)}>
          <aside className="h-full w-[420px] bg-white shadow-2xl p-6" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase text-blue-700">{selectedEvidence.citation_type}</p>
                <h3 className="mt-1 text-lg font-bold text-slate-900">{selectedEvidence.title}</h3>
              </div>
              <button onClick={() => setSelectedEvidence(null)} className="rounded border border-slate-200 px-3 py-1 text-sm font-bold text-slate-500">Close</button>
            </div>
            <p className="mt-4 text-xs font-bold uppercase text-slate-400">Source</p>
            <p className="mt-1 text-sm text-slate-700">{selectedEvidence.source || "Internal legal corpus"}</p>
            <p className="mt-6 text-xs font-bold uppercase text-slate-400">Evidence Snippet</p>
            <p className="mt-2 rounded-lg bg-slate-50 p-4 text-sm leading-relaxed text-slate-700">{selectedEvidence.snippet}</p>
          </aside>
        </div>
      )}
    </section>
  );
}

export default function DraftingWorkspace() {
  return (
    <Suspense fallback={<section className="p-8 text-sm text-slate-500">Loading drafting workspace...</section>}>
      <DraftingWorkspaceContent />
    </Suspense>
  );
}
