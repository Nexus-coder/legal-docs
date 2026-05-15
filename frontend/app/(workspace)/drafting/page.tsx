"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";

type Evidence = {
  id: number;
  citation_type: string;
  title: string;
  source?: string | null;
  snippet: string;
  confidence: number;
  status: string;
};

type DraftDocument = {
  id: number;
  document_type: string;
  title: string;
  content: string;
  status: string;
  error_status?: string | null;
  revision_count: number;
};

type Matter = {
  id: number;
  case_number: string;
  division: string;
  jurisdiction?: string | null;
  subcategory?: string | null;
  workflow_state: string;
  masked_facts?: string | null;
  draft_content?: string | null;
  drafting_error?: string | null;
  draft_documents: DraftDocument[];
  verification_done: number;
  verification_total: number;
  citation_evidence: Evidence[];
  activities: { id: number; title: string; detail?: string | null; created_at: string }[];
};

type PacketDocument = {
  document_type: string;
  title: string;
  subtitle: string;
  enabled: boolean;
};

type ActivityState = "pending" | "active" | "complete" | "error";
type MobilePanel = "control" | "draft" | "review";

const PACKET_DOCUMENTS: PacketDocument[] = [
  {
    document_type: "injunction_motion",
    title: "Notice of Motion",
    subtitle: "Active application document",
    enabled: true,
  },
  {
    document_type: "supporting_affidavit",
    title: "Supporting Affidavit",
    subtitle: "Facts and exhibit narrative",
    enabled: true,
  },
  {
    document_type: "certificate_of_urgency",
    title: "Certificate of Urgency",
    subtitle: "Future slot",
    enabled: false,
  },
  {
    document_type: "draft_order",
    title: "Draft Order",
    subtitle: "Future slot",
    enabled: false,
  },
  {
    document_type: "submissions",
    title: "Submissions",
    subtitle: "Future slot",
    enabled: false,
  },
];

const GENERATION_STEPS = [
  "Thinking through document structure",
  "Reading masked matter facts",
  "Searching Kenyan authorities",
  "Generating Notice of Motion",
  "Generating Supporting Affidavit",
  "Checking draft against review rules",
  "Ready for advocate review",
];

function tokenFromCookie() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("token="))
    ?.split("=")[1];
}

function statusBadgeClass(status?: string | null) {
  if (status === "verified") return "status-green";
  if (status === "needs_review") return "status-amber";
  if (status === "error") return "status-red";
  if (status === "draft") return "status-blue";
  return "status-slate";
}

function statusLabel(status?: string | null, enabled = true) {
  if (!enabled) return "Future";
  if (!status) return "Not generated";
  return status.replaceAll("_", " ");
}

function workflowLabel(state: string) {
  return state.replaceAll("_", " ");
}

function generationStepState({
  index,
  generating,
  activeStep,
  hasDocuments,
  hasError,
}: {
  index: number;
  generating: boolean;
  activeStep: number;
  hasDocuments: boolean;
  hasError: boolean;
}): ActivityState {
  if (hasError && index === activeStep) return "error";
  if (generating) {
    if (index < activeStep) return "complete";
    if (index === activeStep) return "active";
    return "pending";
  }
  if (hasDocuments) return "complete";
  return index === 0 ? "active" : "pending";
}

function activityIcon(state: ActivityState, index: number) {
  if (state === "complete") return "✓";
  if (state === "error") return "!";
  return state === "active" ? "•" : String(index + 1);
}

function buildFallbackMotion(matter: Matter) {
  return [
    "Take notice that the Applicant shall move this Honourable Court for orders preserving the suit property pending inter partes hearing and determination of the application.",
    "",
    "1. That this application be certified urgent and heard on priority basis in view of the threatened interference with the Applicant's quiet possession of the suit property.",
    "",
    "2. That pending hearing and determination of this application, the Respondent, whether by itself, its servants, agents, or any person claiming through it, be restrained from entering, alienating, charging, transferring, evicting, wasting, or otherwise interfering with the suit property.",
    "",
    "3. That pending hearing and determination of the suit, the Respondent be restrained from dealing with the suit property in any manner adverse to the Applicant's possession and occupation.",
    "",
    `Grounded in: ${matter.subcategory || "injunction pending land suit"}.`,
  ].join("\n");
}

function DraftingWorkspaceContent() {
  const searchParams = useSearchParams();
  const matterId = searchParams.get("matter_id");
  const [matter, setMatter] = useState<Matter | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [activeDocumentType, setActiveDocumentType] = useState("injunction_motion");
  const [activeGenerationStep, setActiveGenerationStep] = useState(0);
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("draft");
  const [error, setError] = useState<string | null>(null);

  const authHeaders = useMemo<Record<string, string>>(() => {
    const headers: Record<string, string> = {};
    const token = tokenFromCookie();
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  }, []);

  useEffect(() => {
    if (!generating) return;
    setActiveGenerationStep(0);
    const interval = window.setInterval(() => {
      setActiveGenerationStep((step) => Math.min(step + 1, GENERATION_STEPS.length - 2));
    }, 1400);
    return () => window.clearInterval(interval);
  }, [generating]);

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
        const data: Matter = await res.json();
        setMatter(data);
        if (
          data.workflow_state === "pii_masked" &&
          !(data.draft_documents || []).length &&
          !data.draft_content
        ) {
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
    if (res.ok) {
      const data: Matter = await res.json();
      setMatter(data);
      setActiveGenerationStep(GENERATION_STEPS.length - 1);
    }
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
          subcategory: sourceMatter.subcategory || "Temporary Injunction",
        }),
      });
      const data = await res.json();
      if (!res.ok || (data.error_status && !data.documents?.length && !data.blocks?.length)) {
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

  const documents = matter.draft_documents || [];
  const activeDocument = documents.find((document) => document.document_type === activeDocumentType);
  const activePacketItem = PACKET_DOCUMENTS.find((document) => document.document_type === activeDocumentType);
  const hasDocuments = documents.some((document) => document.content);
  const hasGenerationError = Boolean(error && !hasDocuments);
  const progress = matter.verification_total
    ? Math.round((matter.verification_done / matter.verification_total) * 100)
    : 0;
  const activeContent = activeDocument?.content || "";

  return (
    <section className="drafting-shell" data-mobile-panel={mobilePanel}>
      <header className="drafting-topbar">
        <div>
          <div className="drafting-breadcrumbs">Matters / {matter.case_number} / Drafting</div>
          <h1 className="drafting-title">Temporary injunction drafting desk</h1>
        </div>
        <div className="matter-pill">
          <span className="matter-pill-dot"></span>
          {matter.case_number} · {workflowLabel(matter.workflow_state)}
        </div>
      </header>

      <div className="mobile-drafting-tabs" aria-label="Workspace panels">
        {(["control", "draft", "review"] as MobilePanel[]).map((panel) => (
          <button
            key={panel}
            type="button"
            className={mobilePanel === panel ? "active" : ""}
            onClick={() => setMobilePanel(panel)}
          >
            {panel === "control" ? "Control" : panel === "draft" ? "Draft" : "Review"}
          </button>
        ))}
      </div>

      <div className="drafting-layout">
        <section className="drafting-rail" aria-label="Drafting control rail">
          <div className="drafting-rail-section">
            <p className="drafting-label">Matter</p>
            <div className="summary-grid">
              <div className="summary-row"><span>Case</span><strong className="mono-text">{matter.case_number}</strong></div>
              <div className="summary-row"><span>Court</span><strong>{matter.jurisdiction || matter.division}</strong></div>
              <div className="summary-row"><span>Issue</span><strong>{matter.subcategory || "Injunction pending land suit"}</strong></div>
              <div className="summary-row"><span>Privacy</span><span className="status-badge status-green">PII masked</span></div>
            </div>
          </div>

          <div className="drafting-rail-section">
            <p className="drafting-label">Filing packet</p>
            <div className="packet-list">
              {PACKET_DOCUMENTS.map((document, index) => {
                const draftDocument = documents.find((item) => item.document_type === document.document_type);
                const isActive = activeDocumentType === document.document_type;
                return (
                  <button
                    key={document.document_type}
                    type="button"
                    onClick={() => document.enabled && setActiveDocumentType(document.document_type)}
                    disabled={!document.enabled}
                    className={`packet-item ${isActive ? "active" : ""}`}
                  >
                    <span className="packet-number">{index + 1}</span>
                    <span className="packet-title">
                      {document.title}
                      <span className="packet-subtitle">{draftDocument?.content ? "Generated from masked facts" : document.subtitle}</span>
                    </span>
                    <span className={`status-badge ${statusBadgeClass(draftDocument?.status)}`}>
                      {statusLabel(draftDocument?.status, document.enabled)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="drafting-rail-section">
            <p className="drafting-label">Generation activity</p>
            <div className="activity-stack" aria-live="polite">
              {GENERATION_STEPS.map((step, index) => {
                const state = generationStepState({
                  index,
                  generating,
                  activeStep: activeGenerationStep,
                  hasDocuments,
                  hasError: hasGenerationError,
                });
                return (
                  <div key={step} className={`activity-step ${state}`}>
                    <span className="activity-icon">{activityIcon(state, index)}</span>
                    <span>{step}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="drafting-rail-section">
            <p className="drafting-label">Activity timeline</p>
            <div className="space-y-3">
              {matter.activities.length ? matter.activities.map((activity) => (
                <div key={activity.id} className="border-l-2 border-slate-200 pl-3">
                  <p className="text-xs font-bold text-slate-700">{activity.title}</p>
                  {activity.detail && <p className="text-[11px] text-slate-500">{activity.detail}</p>}
                </div>
              )) : (
                <p className="text-sm text-slate-500">Matter activity appears here as drafting progresses.</p>
              )}
            </div>
          </div>
        </section>

        <section className="document-canvas-wrap" aria-label="Document canvas">
          {error && (
            <div className="mx-auto mb-4 max-w-[840px] rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
              {error}
            </div>
          )}
          <div className="document-toolbar">
            <div>
              <p className="drafting-label mb-1">Selected document</p>
              <h2>{activeDocument?.title || activePacketItem?.title || "Draft document"}</h2>
            </div>
            <div className="toolbar-actions">
              <button type="button" className="drafting-btn drafting-btn-secondary" disabled={!activeContent}>
                Copy text
              </button>
              <button type="button" className="drafting-btn drafting-btn-secondary" onClick={() => generateDraft()} disabled={generating}>
                {generating ? "Generating" : "Regenerate"}
              </button>
              <button type="button" className="drafting-btn drafting-btn-locked" disabled>
                Export locked
              </button>
            </div>
          </div>

          <article className="document-paper">
            <div className="paper-meta">
              <strong>REPUBLIC OF KENYA</strong>
              <span>IN THE {matter.jurisdiction || matter.division}</span>
              <span className="mono-text">{matter.case_number}</span>
            </div>
            <div className="document-divider-title">
              {activeDocument?.title || activePacketItem?.title || "Draft document"}
            </div>
            {activeContent ? (
              <div className="draft-copy">{activeContent}</div>
            ) : (
              <div className="draft-empty">
                <div className="draft-empty-inner">
                  <h3>{generating ? "Drafting in progress" : "No draft generated yet"}</h3>
                  <p>
                    {generating
                      ? "LegalDocs is preparing the motion and affidavit from masked matter facts."
                      : "Generate the injunction packet to create the Notice of Motion and Supporting Affidavit."}
                  </p>
                  {!generating && (
                    <button type="button" onClick={() => generateDraft()} className="drafting-btn drafting-btn-primary mt-4">
                      Generate Motion + Affidavit
                    </button>
                  )}
                </div>
              </div>
            )}
            {!activeContent && hasDocuments && activeDocumentType === "injunction_motion" && (
              <div className="draft-copy mt-6 text-slate-500">{buildFallbackMotion(matter)}</div>
            )}
          </article>
        </section>

        <aside className="drafting-review-rail" aria-label="Review and evidence rail">
          <div className="review-card">
            <p className="drafting-label">Verification</p>
            <div className="progress-block">
              <div className="progress-top">
                <strong>{matter.verification_done} of {matter.verification_total} authorities reviewed</strong>
                <span className="mono-text">{progress}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <span className={`status-badge ${progress === 100 ? "status-green" : "status-amber"}`}>
                {progress === 100 ? "Export ready" : "Export locked until verified"}
              </span>
            </div>
          </div>

          <div className="review-card">
            <p className="drafting-label">Citation evidence</p>
            <div className="evidence-list">
              {matter.citation_evidence.length ? matter.citation_evidence.map((item) => (
                <button key={item.id} type="button" onClick={() => setSelectedEvidence(item)} className="evidence-item">
                  <span className="evidence-kicker">
                    <span>{item.citation_type}</span>
                    <span>{Math.round(item.confidence * 100)}%</span>
                  </span>
                  <strong>{item.title}</strong>
                  <p>{item.snippet}</p>
                </button>
              )) : (
                <div className="risk-item">
                  <span className="status-badge status-slate">Pending</span>
                  <p className="mt-2">Citation evidence appears after draft generation.</p>
                </div>
              )}
            </div>
          </div>

          <div className="review-card">
            <p className="drafting-label">Review risks</p>
            <div className="risk-list">
              <div className="risk-item">
                <span className="status-badge status-amber">Needs advocate check</span>
                <p className="mt-2">Confirm whether a separate Certificate of Urgency should be generated for filing.</p>
              </div>
              <div className="risk-item">
                <span className="status-badge status-amber">Evidence pending</span>
                <p className="mt-2">Attach exhibit references before relying on affidavit paragraphs.</p>
              </div>
            </div>
          </div>

          <div className="review-card">
            <button
              type="button"
              onClick={verifyCitations}
              disabled={verifying || !matter.citation_evidence.length}
              className="drafting-btn drafting-btn-primary w-full justify-center"
            >
              {verifying ? "Verifying citations" : "Verify citations"}
            </button>
          </div>
        </aside>
      </div>

      {selectedEvidence && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30" onClick={() => setSelectedEvidence(null)}>
          <aside className="h-full w-[420px] max-w-[100vw] bg-white p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="drafting-label mb-1">{selectedEvidence.citation_type}</p>
                <h3 className="mt-1 text-lg font-bold text-slate-900">{selectedEvidence.title}</h3>
              </div>
              <button onClick={() => setSelectedEvidence(null)} className="rounded border border-slate-200 px-3 py-1 text-sm font-bold text-slate-500">Close</button>
            </div>
            <p className="drafting-label mt-6 mb-1">Source</p>
            <p className="text-sm text-slate-700">{selectedEvidence.source || "Internal legal corpus"}</p>
            <p className="drafting-label mt-6 mb-2">Evidence snippet</p>
            <p className="rounded-lg bg-slate-50 p-4 text-sm leading-relaxed text-slate-700">{selectedEvidence.snippet}</p>
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
