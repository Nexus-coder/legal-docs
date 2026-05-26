"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";
import { Button } from "@/app/components/ui/Button";
import { Badge } from "@/app/components/ui/Badge";
import { Card, CardLabel } from "@/app/components/ui/Card";
import { DraftEditor, type EditableDraftDocument } from "./_components/DraftEditor";

type Evidence = {
  id: number;
  citation_type: string;
  title: string;
  source?: string | null;
  snippet: string;
  confidence: number;
  status: string;
};

type DraftDocument = EditableDraftDocument;

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

type DraftingRun = {
  id: number;
  matter_id: number;
  status: "running" | "completed" | "failed" | string;
  error_status?: string | null;
};

type DraftingEvent = {
  id: number;
  drafting_run_id: number;
  event_type: string;
  stage: string;
  message: string;
  document_type?: string | null;
  error_type?: string | null;
  created_at: string;
};

type PacketDocument = {
  document_type: string;
  title: string;
  activity_title: string;
  required: boolean;
  selected_by_default: boolean;
};

type DraftingPacket = {
  subcategory: string;
  pleading_type: string;
  documents: PacketDocument[];
};

type GenerationStep = {
  key: string;
  label: string;
};

type ActivityState = "pending" | "active" | "complete" | "error";
type MobilePanel = "control" | "draft" | "review";
type ConnectionState = "idle" | "connecting" | "live" | "reconnecting" | "completed" | "failed";

const FALLBACK_PACKET_DOCUMENTS: PacketDocument[] = [
  {
    document_type: "injunction_motion",
    title: "Notice of Motion",
    activity_title: "Drafting Notice of Motion",
    required: true,
    selected_by_default: true,
  },
  {
    document_type: "supporting_affidavit",
    title: "Supporting Affidavit",
    activity_title: "Drafting Supporting Affidavit",
    required: true,
    selected_by_default: true,
  },
  {
    document_type: "injunction_certificate_of_urgency",
    title: "Certificate of Urgency",
    activity_title: "Drafting Certificate of Urgency",
    required: false,
    selected_by_default: false,
  },
  {
    document_type: "injunction_draft_order",
    title: "Draft Order",
    activity_title: "Drafting Draft Order",
    required: false,
    selected_by_default: false,
  },
  {
    document_type: "injunction_written_submissions",
    title: "Written Submissions",
    activity_title: "Drafting Written Submissions",
    required: false,
    selected_by_default: false,
  },
];

function selectedTypesFromPacket(documents: PacketDocument[]) {
  return documents
    .filter((document) => document.required || document.selected_by_default)
    .map((document) => document.document_type);
}

function generationStepsFor(documents: PacketDocument[], selectedTypes: Set<string>): GenerationStep[] {
  const selectedDocuments = documents.filter(
    (document) => document.required || selectedTypes.has(document.document_type),
  );
  return [
    { key: "read_facts", label: "Reading masked facts" },
    { key: "authorities", label: "Searching Kenyan authorities" },
    ...selectedDocuments.map((document) => ({
      key: document.document_type,
      label: document.activity_title,
    })),
    { key: "critique", label: "Running critique" },
    { key: "completed", label: "Ready for advocate review" },
  ];
}

const FALLBACK_GENERATION_STEPS = generationStepsFor(
  FALLBACK_PACKET_DOCUMENTS,
  new Set(selectedTypesFromPacket(FALLBACK_PACKET_DOCUMENTS)),
);

const terminalEvents = new Set(["completed", "failed"]);

function tokenFromCookie() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("token="))
    ?.split("=")[1];
}

function placeholderMatter(matterId: string): Matter {
  return {
    id: Number(matterId) || 0,
    case_number: `Matter #${matterId}`,
    division: "Environment and Land Court",
    jurisdiction: "Environment and Land Court",
    subcategory: "Temporary Injunction",
    workflow_state: "loading",
    draft_documents: [],
    verification_done: 0,
    verification_total: 0,
    citation_evidence: [],
    activities: [],
  };
}

function getStatusVariant(status?: string | null): "blue" | "green" | "amber" | "red" | "slate" {
  if (status === "verified") return "green";
  if (status === "needs_review") return "amber";
  if (status === "error") return "red";
  if (status === "draft") return "blue";
  return "slate";
}

function statusLabel(status?: string | null, selected = true) {
  if (!selected) return "Not selected";
  if (!status) return "Not generated";
  return status.replaceAll("_", " ");
}

function workflowLabel(state: string) {
  if (state === "loading") return "loading matter";
  return state.replaceAll("_", " ");
}

function connectionLabel(connection: ConnectionState, loading: boolean) {
  if (loading) return "connecting";
  if (connection === "completed") return "completed";
  if (connection === "failed") return "failed";
  if (connection === "reconnecting") return "reconnecting";
  if (connection === "live") return "live";
  if (connection === "connecting") return "connecting";
  return "idle";
}

function connectionClass(connection: ConnectionState, loading: boolean) {
  const label = connectionLabel(connection, loading);
  if (label === "completed") return "status-green";
  if (label === "failed") return "status-red";
  if (label === "live") return "status-blue";
  if (label === "connecting" || label === "reconnecting") return "status-amber";
  return "status-slate";
}

function activeStepFromEvents(
  events: DraftingEvent[],
  hasDocuments: boolean,
  connection: ConnectionState,
  loading: boolean,
  generationSteps: GenerationStep[],
) {
  if (loading) return 0;
  if (connection === "completed") return generationSteps.length - 1;
  const latest = events.at(-1);
  if (!latest) return hasDocuments && connection === "idle" ? generationSteps.length - 1 : 0;
  if (latest.event_type === "failed") return stageIndex(latest.stage, generationSteps);
  if (latest.event_type === "completed") return generationSteps.length - 1;
  if (hasDocuments && connection === "idle") return generationSteps.length - 1;
  return stageIndex(latest.stage, generationSteps);
}

function stageIndex(stage: string, generationSteps: GenerationStep[]) {
  if (stage === "read_facts" || stage === "start") return 0;
  if (stage === "authorities") return 1;
  const index = generationSteps.findIndex((step) => step.key === stage);
  if (index >= 0) return index;
  if (stage === "completed") return generationSteps.length - 1;
  return 0;
}

function generationStepState({
  index,
  activeStep,
  isDrafting,
  hasDocuments,
  hasError,
}: {
  index: number;
  activeStep: number;
  isDrafting: boolean;
  hasDocuments: boolean;
  hasError: boolean;
}): ActivityState {
  if (hasError && index === activeStep) return "error";
  if (hasDocuments && !isDrafting) return "complete";
  if (isDrafting) {
    if (index < activeStep) return "complete";
    if (index === activeStep) return "active";
    return "pending";
  }
  return index === 0 ? "active" : "pending";
}

function activityIcon(state: ActivityState, index: number) {
  if (state === "complete") return "ok";
  if (state === "error") return "!";
  return state === "active" ? "..." : String(index + 1);
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
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("draft");
  const [error, setError] = useState<string | null>(null);
  const [activeRun, setActiveRun] = useState<DraftingRun | null>(null);
  const [events, setEvents] = useState<DraftingEvent[]>([]);
  const [packet, setPacket] = useState<DraftingPacket | null>(null);
  const [selectedDocumentTypes, setSelectedDocumentTypes] = useState<Set<string>>(
    () => new Set(selectedTypesFromPacket(FALLBACK_PACKET_DOCUMENTS)),
  );
  const [connection, setConnection] = useState<ConnectionState>("idle");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const streamRunIdRef = useRef<number | null>(null);
  const terminalEventSeenRef = useRef(false);
  const matterRef = useRef<Matter | null>(null);

  useEffect(() => {
    if (isFullscreen) {
      document.body.classList.add("fullscreen-active");
    } else {
      document.body.classList.remove("fullscreen-active");
    }
    return () => {
      document.body.classList.remove("fullscreen-active");
    };
  }, [isFullscreen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen]);

  const authHeaders = useMemo<Record<string, string>>(() => {
    const headers: Record<string, string> = {};
    const token = tokenFromCookie();
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  }, []);

  const closeStream = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    streamRunIdRef.current = null;
  }, []);

  useEffect(() => {
    matterRef.current = matter;
  }, [matter]);

  const refreshMatter = useCallback(async () => {
    if (!matterId) return;
    const res = await fetch(`${API_BASE_URL}matters/${matterId}`, {
      headers: authHeaders,
      credentials: "include",
    });
    if (res.ok) {
      const data: Matter = await res.json();
      setMatter(data);
    }
  }, [authHeaders, matterId]);

  const loadDraftingPacket = useCallback(async (sourceMatter: Matter) => {
    const params = new URLSearchParams({
      subcategory: sourceMatter.subcategory || "Temporary Injunction",
    });
    const res = await fetch(`${API_BASE_URL}drafting/packet?${params.toString()}`, {
      headers: authHeaders,
      credentials: "include",
    });
    if (!res.ok) {
      setPacket(null);
      setSelectedDocumentTypes(new Set(selectedTypesFromPacket(FALLBACK_PACKET_DOCUMENTS)));
      return;
    }
    const data = (await res.json()) as DraftingPacket;
    setPacket(data);
    const existingDocumentTypes = new Set(
      (sourceMatter.draft_documents || []).map((document) => document.document_type),
    );
    setActiveDocumentType((current) => {
      if (data.documents.some((document) => document.document_type === current)) return current;
      const firstGeneratedDocument = data.documents.find((document) =>
        existingDocumentTypes.has(document.document_type),
      );
      return firstGeneratedDocument?.document_type || data.documents[0]?.document_type || current;
    });
    setSelectedDocumentTypes(
      new Set(
        existingDocumentTypes.size
          ? data.documents
              .filter((document) => document.required || existingDocumentTypes.has(document.document_type))
              .map((document) => document.document_type)
          : selectedTypesFromPacket(data.documents),
      ),
    );
  }, [authHeaders]);

  const connectToRun = useCallback((runId: number) => {
    if (eventSourceRef.current && streamRunIdRef.current === runId) return;
    closeStream();
    setConnection("connecting");
    streamRunIdRef.current = runId;
    terminalEventSeenRef.current = false;
    const source = new EventSource(`${API_BASE_URL}drafting/runs/${runId}/events`, {
      withCredentials: true,
    });
    eventSourceRef.current = source;

    source.onopen = () => setConnection("live");
    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as DraftingEvent;
      setEvents((current) => {
        const withoutDuplicate = current.filter((item) => item.id !== event.id);
        return [...withoutDuplicate, event].sort((a, b) => a.id - b.id);
      });
      if (event.event_type === "document_ready") {
        void refreshMatter();
      }
      if (terminalEvents.has(event.event_type)) {
        terminalEventSeenRef.current = true;
        setConnection(event.event_type === "completed" ? "completed" : "failed");
        setGenerating(false);
        if (event.error_type) setError(readableDraftingError(event.error_type));
        closeStream();
        void refreshMatter();
      }
    };
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) {
        setGenerating(false);
        if (!terminalEventSeenRef.current) {
          setConnection("failed");
          setError("Live drafting connection closed before the run completed. Retry the run.");
        }
        return;
      }
      setConnection("reconnecting");
    };
  }, [closeStream, refreshMatter]);

  const startDrafting = useCallback(async (sourceMatter?: Matter | null) => {
    const targetMatter = sourceMatter ?? matterRef.current;
    if (!targetMatter || targetMatter.workflow_state === "loading") return;
    const packetDocuments = packet?.documents.length ? packet.documents : FALLBACK_PACKET_DOCUMENTS;
    const selectedTypes = packetDocuments
      .filter((document) => document.required || selectedDocumentTypes.has(document.document_type))
      .map((document) => document.document_type);
    setGenerating(true);
    setError(null);
    setEvents([]);
    setConnection("connecting");
    try {
      const res = await fetch(`${API_BASE_URL}drafting/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        credentials: "include",
        body: JSON.stringify({
          matter_id: targetMatter.id,
          jurisdiction: targetMatter.jurisdiction || targetMatter.division,
          subcategory: targetMatter.subcategory || "Temporary Injunction",
          pleading_type: packet?.pleading_type,
          selected_document_types: selectedTypes,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Draft generation failed");
      setActiveRun(data);
      connectToRun(data.id);
    } catch (err) {
      setConnection("failed");
      setGenerating(false);
      setError(err instanceof Error ? err.message : "Draft generation failed");
    }
  }, [authHeaders, connectToRun, packet, selectedDocumentTypes]);

  useEffect(() => {
    const load = async () => {
      if (!matterId) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE_URL}matters/${matterId}`, {
          headers: authHeaders,
          credentials: "include",
        });
        if (!res.ok) throw new Error("Matter not found");
        const data: Matter = await res.json();
        setMatter(data);
        void loadDraftingPacket(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load matter");
      } finally {
        setLoading(false);
      }
    };
    void load();
    return closeStream;
  }, [authHeaders, closeStream, loadDraftingPacket, matterId]);

  const verifyCitations = async () => {
    if (!matter) return;
    setVerifying(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}matters/${matter.id}/verify-citations`, {
        method: "POST",
        headers: authHeaders,
        credentials: "include",
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

  const handleDocumentSaved = useCallback((savedDocument: DraftDocument) => {
    setMatter((current) => {
      if (!current) return current;
      const draftDocuments = current.draft_documents.map((document) =>
        document.id === savedDocument.id ? savedDocument : document,
      );
      return {
        ...current,
        draft_documents: draftDocuments,
        draft_content: draftDocuments
          .filter((document) => document.content)
          .map((document) => `# ${document.title}\n\n${document.content}`)
          .join("\n\n"),
      };
    });
  }, []);

  const toggleOptionalDocument = useCallback((documentType: string) => {
    setSelectedDocumentTypes((current) => {
      const next = new Set(current);
      if (next.has(documentType)) {
        next.delete(documentType);
      } else {
        next.add(documentType);
      }
      return next;
    });
  }, []);

  const packetDocuments = useMemo(
    () => packet?.documents.length ? packet.documents : FALLBACK_PACKET_DOCUMENTS,
    [packet],
  );
  const selectedPacketTypes = useMemo(
    () => new Set([
      ...packetDocuments.filter((document) => document.required).map((document) => document.document_type),
      ...selectedDocumentTypes,
    ]),
    [packetDocuments, selectedDocumentTypes],
  );
  const selectedCount = packetDocuments.filter((document) =>
    selectedPacketTypes.has(document.document_type),
  ).length;
  const generationSteps = useMemo(
    () => generationStepsFor(packetDocuments, selectedPacketTypes),
    [packetDocuments, selectedPacketTypes],
  );

  useEffect(() => {
    if (!packetDocuments.length) return;
    const activeStillExists = packetDocuments.some(
      (document) => document.document_type === activeDocumentType,
    );
    if (!activeStillExists) {
      setActiveDocumentType(packetDocuments[0].document_type);
    }
  }, [activeDocumentType, packetDocuments]);

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

  const displayMatter = matter ?? placeholderMatter(matterId);
  const documents = displayMatter.draft_documents || [];
  const activeDocument = documents.find((document) => document.document_type === activeDocumentType);
  const activePacketItem = packetDocuments.find((document) => document.document_type === activeDocumentType);
  const hasDocuments = documents.some((document) => document.content);
  const isDrafting = loading || generating || connection === "connecting" || connection === "live" || connection === "reconnecting";
  const activeGenerationStep = activeStepFromEvents(
    events,
    hasDocuments,
    connection,
    loading,
    generationSteps,
  );
  const hasGenerationError = connection === "failed" || Boolean(error && !hasDocuments && !loading);
  const progress = displayMatter.verification_total
    ? Math.round((displayMatter.verification_done / displayMatter.verification_total) * 100)
    : 0;
  const activeContent = activeDocument?.content || "";
  const latestEvent = events.at(-1);
  const runLabel = activeRun ? `Run #${activeRun.id}` : "No active run";

  return (
    <section className={`drafting-shell ${isFullscreen ? "fullscreen-mode" : ""}`} data-mobile-panel={mobilePanel}>
      <header className="drafting-topbar">
        <div>
          <div className="drafting-breadcrumbs">Matters / {displayMatter.case_number} / Drafting</div>
          <h1 className="drafting-title">Legal drafting desk</h1>
        </div>
        <div className="topbar-status-group">
          <span className={`status-badge ${connectionClass(connection, loading)}`}>
            {connectionLabel(connection, loading)}
          </span>
          <div className="matter-pill">
            <span className="matter-pill-dot"></span>
            {displayMatter.case_number} / {workflowLabel(displayMatter.workflow_state)}
          </div>
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
              <div className="summary-row"><span>Case</span><strong className="mono-text">{displayMatter.case_number}</strong></div>
              <div className="summary-row"><span>Court</span><strong>{displayMatter.jurisdiction || displayMatter.division}</strong></div>
              <div className="summary-row"><span>Issue</span><strong>{displayMatter.subcategory || "Injunction pending land suit"}</strong></div>
              <div className="summary-row"><span>Privacy</span><Badge variant={loading ? "slate" : "green"}>{loading ? "Loading" : "PII masked"}</Badge></div>
            </div>
          </div>

          <div className="drafting-rail-section">
            <div className="rail-heading-row mb-4">
              <CardLabel>Filing packet</CardLabel>
              <span className="mono-text text-slate-400">{selectedCount} selected</span>
            </div>
            <div className="packet-list">
              {packetDocuments.map((document) => {
                const draftDocument = documents.find((item) => item.document_type === document.document_type);
                const isActive = activeDocumentType === document.document_type;
                const isSelected = selectedPacketTypes.has(document.document_type);
                const selectionLocked = isDrafting || hasDocuments;
                return (
                  <div
                    key={document.document_type}
                    className={`packet-item ${isActive ? "active" : ""} ${!isSelected ? "unselected" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={document.required || selectionLocked}
                      onChange={() => toggleOptionalDocument(document.document_type)}
                      aria-label={`${isSelected ? "Remove" : "Add"} ${document.title}`}
                    />
                    <button
                      type="button"
                      onClick={() => setActiveDocumentType(document.document_type)}
                      className="packet-title-button"
                    >
                      <span className="packet-title">
                        {document.title}
                        <span className="packet-subtitle">
                          {draftDocument?.content
                            ? "Generated from masked facts"
                            : document.required
                              ? "Required filing document"
                              : isSelected
                                ? "Optional document selected"
                                : "Optional document available"}
                        </span>
                      </span>
                    </button>
                    <Badge variant={document.required ? "blue" : isSelected ? "amber" : "slate"}>
                      {document.required ? "Required" : isSelected ? "Optional" : "Skipped"}
                    </Badge>
                    <Badge variant={getStatusVariant(draftDocument?.status)}>
                      {statusLabel(draftDocument?.status, isSelected)}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="drafting-rail-section">
            <div className="rail-heading-row">
              <CardLabel>Generation activity</CardLabel>
              <span className="mono-text text-slate-400">{runLabel}</span>
            </div>
            <div className="activity-stack mt-4" aria-live="polite">
              {generationSteps.map((step, index) => {
                const state = generationStepState({
                  index,
                  activeStep: activeGenerationStep,
                  isDrafting,
                  hasDocuments,
                  hasError: hasGenerationError,
                });
                return (
                  <div key={step.key} className={`activity-step ${state}`}>
                    <span className="activity-icon">{activityIcon(state, index)}</span>
                    <span>
                      <span className="font-medium">{step.label}</span>
                      {index === activeGenerationStep && latestEvent?.message ? (
                        <span className="activity-detail">{latestEvent.message}</span>
                      ) : null}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="drafting-rail-section">
            <CardLabel className="mb-4">Activity timeline</CardLabel>
            <div className="space-y-3">
              {displayMatter.activities.length ? displayMatter.activities.map((activity) => (
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
            <div className="drafting-error-banner">
              <span>{error}</span>
              <Button variant="secondary" size="sm" onClick={() => startDrafting()} disabled={!matter || generating}>
                Retry
              </Button>
            </div>
          )}
          <div className="document-toolbar">
            <div>
              <CardLabel className="mb-1">Selected document</CardLabel>
              <h2 className="text-xl font-bold text-slate-900">{activeDocument?.title || activePacketItem?.title || "Draft document"}</h2>
            </div>
            <div className="toolbar-actions">
              <Button
                variant="secondary"
                size="sm"
                disabled={!activeContent}
                onClick={() => setIsFullscreen((prev) => !prev)}
                title={isFullscreen ? "Exit Full Screen" : "Full Screen"}
              >
                <i className={`fas ${isFullscreen ? "fa-compress" : "fa-expand"} mr-1.5`}></i>
                {isFullscreen ? "Exit Full Screen" : "Full Screen"}
              </Button>
              <Button variant="secondary" size="sm" disabled={!activeContent} onClick={() => navigator.clipboard?.writeText(activeContent)}>
                Copy text
              </Button>
              <Button variant="secondary" size="sm" onClick={() => startDrafting()} loading={generating} disabled={!matter || loading}>
                Regenerate
              </Button>
              <Button variant="locked" size="sm">
                Export locked
              </Button>
            </div>
          </div>

          <article className="document-paper">
            {activeDocument && activeContent ? (
              <DraftEditor
                document={activeDocument}
                evidence={displayMatter.citation_evidence}
                authHeaders={authHeaders}
                onDocumentSaved={handleDocumentSaved}
                onError={setError}
                isFullscreen={isFullscreen}
                onToggleFullscreen={() => setIsFullscreen((prev) => !prev)}
              />
            ) : (
              <>
                <div className="paper-meta">
                  <strong>REPUBLIC OF KENYA</strong>
                  <span>IN THE {displayMatter.jurisdiction || displayMatter.division}</span>
                  <span className="mono-text">{displayMatter.case_number}</span>
                </div>
                <div className="document-divider-title">
                  {activeDocument?.title || activePacketItem?.title || "Draft document"}
                </div>
                <div className="draft-empty">
                  <div className="draft-empty-inner">
                    <h3 className="text-xl font-bold text-slate-900 mb-2">
                      {isDrafting ? "Drafting in progress" : "No draft generated yet"}
                    </h3>
                    <p className="text-slate-500 mb-6">
                      {isDrafting
                        ? "The desk is preparing the selected filing packet from masked matter facts."
                        : "Choose any optional documents, then generate the filing packet for this matter."}
                    </p>
                    {!isDrafting && (
                      <Button onClick={() => startDrafting()} size="lg" disabled={!matter}>
                        Generate {selectedCount} Document{selectedCount === 1 ? "" : "s"}
                      </Button>
                    )}
                  </div>
                </div>
              </>
            )}
            {!activeContent && hasDocuments && activeDocumentType === "injunction_motion" && (
              <div className="draft-copy mt-6 text-slate-500">{buildFallbackMotion(displayMatter)}</div>
            )}
          </article>
        </section>

        <aside className="drafting-review-rail" aria-label="Review and evidence rail">
          <div className="review-card">
            <CardLabel className="mb-4">Verification</CardLabel>
            <div className="progress-block">
              <div className="progress-top mb-1">
                <strong className="text-sm">{displayMatter.verification_done} of {displayMatter.verification_total} authorities reviewed</strong>
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
              {displayMatter.citation_evidence.length ? displayMatter.citation_evidence.map((item) => (
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
              disabled={verifying || !displayMatter.citation_evidence.length || !matter}
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
                  &quot;{selectedEvidence.snippet}&quot;
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

function readableDraftingError(errorStatus: string) {
  const labels: Record<string, string> = {
    empty_context: "No masked matter facts were available for drafting.",
    retrieval_failed: "Kenyan authority retrieval failed. Retry the run before relying on the draft.",
    unsupported_subcategory: "This matter type is not configured for automated drafting yet.",
    unsupported_document_type: "One selected document is not available for this filing packet.",
    empty_document_selection: "No drafting documents were selected for generation.",
    model_failed: "The drafting model did not complete. Retry when the model is available.",
    max_revisions_failed: "Draft generated, but the critique loop reached its revision limit. Review the draft manually before relying on it.",
    malformed_output: "Drafting finished with an unreadable model output.",
  };
  return labels[errorStatus] || errorStatus.replaceAll("_", " ");
}

function DraftingShellSkeleton() {
  const matter = placeholderMatter("...");
  return (
    <section className="drafting-shell" data-mobile-panel="draft">
      <header className="drafting-topbar">
        <div>
          <div className="drafting-breadcrumbs">Matters / Preparing desk / Drafting</div>
          <h1 className="drafting-title">Temporary injunction drafting desk</h1>
        </div>
        <div className="topbar-status-group">
          <span className="status-badge status-amber">connecting</span>
          <div className="matter-pill"><span className="matter-pill-dot"></span>Preparing matter packet</div>
        </div>
      </header>
      <div className="drafting-layout">
        <section className="drafting-rail">
          <div className="drafting-rail-section">
            <CardLabel className="mb-4">Matter</CardLabel>
            <div className="summary-grid">
              <div className="skeleton-line"></div>
              <div className="skeleton-line"></div>
              <div className="skeleton-line short"></div>
            </div>
          </div>
          <div className="drafting-rail-section">
            <CardLabel className="mb-4">Generation activity</CardLabel>
            <div className="activity-stack" aria-live="polite">
              {FALLBACK_GENERATION_STEPS.map((step, index) => (
                <div key={step.key} className={`activity-step ${index === 0 ? "active" : "pending"}`}>
                  <span className="activity-icon">{index === 0 ? "..." : index + 1}</span>
                  <span className="font-medium">{step.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
        <section className="document-canvas-wrap">
          <div className="document-toolbar">
            <div>
              <CardLabel className="mb-1">Selected document</CardLabel>
              <h2 className="text-xl font-bold text-slate-900">Notice of Motion</h2>
            </div>
          </div>
          <article className="document-paper">
            <div className="paper-meta">
              <strong>REPUBLIC OF KENYA</strong>
              <span>IN THE {matter.division}</span>
              <span className="mono-text">{matter.case_number}</span>
            </div>
            <div className="document-divider-title">Notice of Motion</div>
            <div className="draft-empty">
              <div className="draft-empty-inner">
                <h3>Drafting in progress</h3>
                <p className="text-slate-500">Preparing the legal desk.</p>
              </div>
            </div>
          </article>
        </section>
        <aside className="drafting-review-rail">
          <div className="review-card">
            <CardLabel className="mb-4">Verification</CardLabel>
            <div className="skeleton-line"></div>
          </div>
        </aside>
      </div>
    </section>
  );
}

export default function DraftingWorkspace() {
  return (
    <Suspense fallback={<DraftingShellSkeleton />}>
      <DraftingWorkspaceContent />
    </Suspense>
  );
}
