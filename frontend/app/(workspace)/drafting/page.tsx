"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";
import { Button } from "@/app/components/ui/Button";
import { Badge } from "@/app/components/ui/Badge";
import { Card, CardLabel } from "@/app/components/ui/Card";

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

function getStatusVariant(status?: string | null): "blue" | "green" | "amber" | "red" | "slate" {
  if (status === "verified") return "green";
  if (status === "needs_review") return "amber";
  if (status === "error") return "red";
  if (status === "draft") return "blue";
  return "slate";
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
        <Card className="p-8">
          <h2 className="text-xl font-bold text-slate-900">Select a matter to draft</h2>
          <p className="mt-2 text-sm text-slate-500">Start from Context & PII or resume an existing matter from the dashboard.</p>
          <Link href="/" passHref legacyBehavior>
            <Button className="mt-6">Back to dashboard</Button>
          </Link>
        </Card>
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
            <CardLabel className="mb-4">Matter</CardLabel>
            <div className="summary-grid">
              <div className="summary-row"><span>Case</span><strong className="mono-text">{matter.case_number}</strong></div>
              <div className="summary-row"><span>Court</span><strong>{matter.jurisdiction || matter.division}</strong></div>
              <div className="summary-row"><span>Issue</span><strong>{matter.subcategory || "Injunction pending land suit"}</strong></div>
              <div className="summary-row"><span>Privacy</span><Badge variant="green">PII masked</Badge></div>
            </div>
          </div>

          <div className="drafting-rail-section">
            <CardLabel className="mb-4">Filing packet</CardLabel>
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
                    <Badge variant={getStatusVariant(draftDocument?.status)}>
                      {statusLabel(draftDocument?.status, document.enabled)}
                    </Badge>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="drafting-rail-section">
            <CardLabel className="mb-4">Generation activity</CardLabel>
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
                    <span className="font-medium">{step}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="drafting-rail-section">
            <CardLabel className="mb-4">Activity timeline</CardLabel>
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
              <CardLabel className="mb-1">Selected document</CardLabel>
              <h2 className="text-xl font-bold text-slate-900">{activeDocument?.title || activePacketItem?.title || "Draft document"}</h2>
            </div>
            <div className="toolbar-actions">
              <Button variant="secondary" size="sm" disabled={!activeContent}>
                Copy text
              </Button>
              <Button variant="secondary" size="sm" onClick={() => generateDraft()} loading={generating}>
                Regenerate
              </Button>
              <Button variant="locked" size="sm">
                Export locked
              </Button>
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
                  <h3 className="text-xl font-bold text-slate-900 mb-2">{generating ? "Drafting in progress" : "No draft generated yet"}</h3>
                  <p className="text-slate-500 mb-6">
                    {generating
                      ? "LegalDocs is preparing the motion and affidavit from masked matter facts."
                      : "Generate the injunction packet to create the Notice of Motion and Supporting Affidavit."}
                  </p>
                  {!generating && (
                    <Button onClick={() => generateDraft()} size="lg">
                      Generate Motion + Affidavit
                    </Button>
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
            <CardLabel className="mb-4">Verification</CardLabel>
            <div className="progress-block">
              <div className="progress-top mb-1">
                <strong className="text-sm">{matter.verification_done} of {matter.verification_total} authorities reviewed</strong>
                <span className="mono-text text-xs">{progress}%</span>
              </div>
              <div className="progress-track mb-3">
                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <Badge variant={progress === 100 ? "green" : "amber"}>
                {progress === 100 ? "Export ready" : "Export locked until verified"}
              </Badge>
            </div>
          </div>

          <div className="review-card">
            <CardLabel className="mb-4">Citation evidence</CardLabel>
            <div className="evidence-list">
              {matter.citation_evidence.length ? matter.citation_evidence.map((item) => (
                <button key={item.id} type="button" onClick={() => setSelectedEvidence(item)} className="evidence-item hover:border-brand-blue hover:bg-brand-blue/5 transition-all">
                  <span className="evidence-kicker">
                    <span className="text-brand-blue">{item.citation_type}</span>
                    <span className="text-brand-blue-hover">{Math.round(item.confidence * 100)}%</span>
                  </span>
                  <strong className="text-slate-900">{item.title}</strong>
                  <p className="text-slate-600">{item.snippet}</p>
                </button>
              )) : (
                <div className="risk-item !bg-slate-50 !border-slate-100">
                  <Badge variant="slate">Pending</Badge>
                  <p className="mt-2 text-slate-500 text-xs">Citation evidence appears after draft generation.</p>
                </div>
              )}
            </div>
          </div>

          <div className="review-card">
            <CardLabel className="mb-4">Review risks</CardLabel>
            <div className="risk-list">
              <div className="risk-item">
                <Badge variant="amber">Needs advocate check</Badge>
                <p className="mt-2 text-xs text-amber-900 font-medium">Confirm whether a separate Certificate of Urgency should be generated for filing.</p>
              </div>
              <div className="risk-item">
                <Badge variant="amber">Evidence pending</Badge>
                <p className="mt-2 text-xs text-amber-900 font-medium">Attach exhibit references before relying on affidavit paragraphs.</p>
              </div>
            </div>
          </div>

          <div className="review-card border-none">
            <Button
              onClick={verifyCitations}
              disabled={verifying || !matter.citation_evidence.length}
              loading={verifying}
              className="w-full"
            >
              Verify citations
            </Button>
          </div>
        </aside>
      </div>

      {selectedEvidence && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30 backdrop-blur-sm transition-opacity" onClick={() => setSelectedEvidence(null)}>
          <aside className="h-full w-[420px] max-w-[100vw] bg-white p-8 shadow-2xl animate-in slide-in-from-right duration-300" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between gap-4 mb-8">
              <div>
                <CardLabel className="mb-2">{selectedEvidence.citation_type}</CardLabel>
                <h3 className="text-xl font-bold text-slate-900 leading-tight">{selectedEvidence.title}</h3>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setSelectedEvidence(null)}>
                <i className="fas fa-times"></i>
              </Button>
            </div>
            
            <div className="space-y-8">
              <div>
                <CardLabel className="mb-2">Source</CardLabel>
                <p className="text-sm font-medium text-slate-700">{selectedEvidence.source || "Internal legal corpus"}</p>
              </div>
              
              <div>
                <CardLabel className="mb-3">Evidence snippet</CardLabel>
                <div className="rounded-xl bg-slate-50 border border-slate-100 p-5 text-sm leading-relaxed text-slate-700 font-serif">
                  "{selectedEvidence.snippet}"
                </div>
              </div>
              
              <div className="pt-4">
                <Button className="w-full">Open full precedent</Button>
              </div>
            </div>
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
