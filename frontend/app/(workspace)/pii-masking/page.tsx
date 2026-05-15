"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";

type PiiEntity = {
  entity_type: string;
  text: string;
  start: number;
  end: number;
  score: number;
};

const steps = [
  { id: 1, label: "Jurisdiction", icon: "fa-scale-balanced" },
  { id: 2, label: "Facts & PII", icon: "fa-shield-alt" },
  { id: 3, label: "Review", icon: "fa-file-circle-check" },
];

export default function PIIMasking() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [jurisdiction, setJurisdiction] = useState("Environment and Land Court (ELC)");
  const [subcategory, setSubcategory] = useState("Adverse Possession");

  const [facts, setFacts] = useState("");
  const [anonymizedFacts, setAnonymizedFacts] = useState("");
  const [detectedEntities, setDetectedEntities] = useState<PiiEntity[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [matterId, setMatterId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const getToken = () =>
    document.cookie
      .split("; ")
      .find((row) => row.startsWith("token="))
      ?.split("=")[1];

  const handleAnalyze = async () => {
    if (!facts.trim()) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      const token = getToken();
      if (!token) throw new Error("Authentication required");

      let activeMatterId = matterId;
      if (!activeMatterId) {
        const matterRes = await fetch(`${API_BASE_URL}matters/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            case_number: `MAT-${new Date().toISOString().slice(0, 10)}-${Date.now().toString().slice(-5)}`,
            division: jurisdiction,
            jurisdiction,
            subcategory,
            last_activity: "Matter created",
          }),
        });
        if (!matterRes.ok) throw new Error("Could not create matter");
        const matter = await matterRes.json();
        activeMatterId = matter.id;
        setMatterId(matter.id);
      }

      const res = await fetch(`${API_BASE_URL}pii/mask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          matter_id: activeMatterId,
          text: facts,
          jurisdiction,
          subcategory,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setDetectedEntities(data.entities);
        setAnonymizedFacts(data.masked_text);
        setStep(3);
      } else {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "PII masking failed");
      }
    } catch (error) {
      console.error("Analysis failed", error);
      setError(error instanceof Error ? error.message : "Analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleLaunch = () => {
    if (!matterId) return;
    const params = new URLSearchParams({ matter_id: String(matterId) });
    router.push(`/drafting?${params.toString()}`);
  };

  return (
    <section className="ld-page">
      <div className="ld-page-inner">
        <div className="ld-page-header">
          <div>
            <p className="ld-eyebrow">Context intake</p>
            <h2 className="ld-title">Prepare case facts before drafting.</h2>
            <p className="ld-subtitle">Select the legal frame, mask sensitive details, and pass a clean matter packet into the drafting workspace.</p>
          </div>
          <span className="status-badge status-blue"><i className="fas fa-shield-alt"></i> Privacy guard active</span>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="ld-card p-4">
            <p className="ld-card-label mb-4">Setup flow</p>
            <div className="space-y-2">
              {steps.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setStep(item.id)}
                  className={`flex w-full items-center gap-3 rounded-lg border px-3 py-3 text-left transition ${
                    step === item.id ? "border-blue-200 bg-blue-50 text-blue-800" : "border-slate-200 bg-white text-slate-600 hover:border-blue-200"
                  }`}
                >
                  <span className={`flex h-8 w-8 items-center justify-center rounded-md ${step === item.id ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-500"}`}>
                    <i className={`fas ${item.icon} text-xs`}></i>
                  </span>
                  <span>
                    <span className="block text-sm font-extrabold">{item.label}</span>
                    <span className="ld-card-label">Step {item.id}</span>
                  </span>
                </button>
              ))}
            </div>
            <div className="mt-5 rounded-lg bg-slate-950 p-4 text-white">
              <div className="mb-3 flex items-center gap-2 text-blue-300">
                <i className="fas fa-circle-notch animate-spin text-xs"></i>
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em]">Standing by</span>
              </div>
              <p className="text-sm font-bold">Drafting handoff queue</p>
              <p className="mt-2 text-xs leading-5 text-slate-400">The workspace will receive jurisdiction, pleading type, anonymized facts, and masked entity evidence.</p>
            </div>
          </aside>

          <div className="ld-card overflow-hidden">
            <div className="grid grid-cols-3 border-b border-slate-200">
              {steps.map((item) => (
                <div key={item.id} className={`ld-step ${step >= item.id ? "ld-step-active" : ""}`}>
                  <span className="text-xs font-extrabold">{item.label}</span>
                </div>
              ))}
            </div>

            <div className="min-h-[520px] p-6 md:p-8">
              {step === 1 && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                    <label className="block">
                      <span className="ld-card-label mb-2 block">Court division</span>
                      <select
                        value={jurisdiction}
                        onChange={(e) => setJurisdiction(e.target.value)}
                        className="w-full rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm font-semibold outline-none transition focus:border-blue-500"
                      >
                        <option>Environment and Land Court (ELC)</option>
                        <option>High Court - Civil Division</option>
                        <option>Commercial & Tax Division</option>
                      </select>
                    </label>
                    <label className="block">
                      <span className="ld-card-label mb-2 block">Pleading sub-category</span>
                      <select
                        value={subcategory}
                        onChange={(e) => setSubcategory(e.target.value)}
                        className="w-full rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm font-semibold outline-none transition focus:border-blue-500"
                      >
                        <option>Adverse Possession</option>
                        <option>Boundary Dispute</option>
                        <option>Landlord-Tenant Conflict</option>
                        <option>Personal Injury Claim</option>
                      </select>
                    </label>
                  </div>
                  <div className="ld-card-muted flex items-start gap-3 p-4">
                    <i className="fas fa-info-circle mt-1 text-amber-500"></i>
                    <p className="text-sm leading-6 text-slate-600">The selected legal frame controls retrieval, citation checking, and the drafting packet assembled in the next workspace.</p>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-5">
                  <label className="block">
                    <span className="ld-card-label mb-2 block">Instruction box</span>
                    <textarea
                      placeholder="Paste case facts or summary instructions here. E.g. 'The plaintiff has occupied LR 209/45 since 1998...'"
                      value={facts}
                      onChange={(e) => setFacts(e.target.value)}
                      className="h-80 w-full resize-none rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6 outline-none transition focus:border-blue-500"
                    ></textarea>
                  </label>
                  <div className="flex flex-col gap-4 rounded-lg bg-slate-950 p-4 text-white md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-500/20 text-blue-300">
                        <i className="fas fa-shield-alt"></i>
                      </span>
                      <div>
                        <p className="text-sm font-extrabold">Thinking through privacy risk</p>
                        <p className="text-xs text-slate-400">Names, dates, locations, and identifiers will be masked before drafting.</p>
                      </div>
                    </div>
                    <button onClick={handleAnalyze} disabled={isAnalyzing || !facts.trim()} className="ld-primary-action disabled:cursor-not-allowed disabled:opacity-50">
                      {isAnalyzing ? (
                        <>
                          <i className="fas fa-circle-notch animate-spin"></i> Analyzing facts
                        </>
                      ) : (
                        <>
                          <i className="fas fa-wand-magic-sparkles"></i> Analyze & mask PII
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-5">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="ld-card-label">Anonymized facts preview</p>
                      <p className="mt-1 text-sm text-slate-500">Review the clean packet before opening the drafting desk.</p>
                    </div>
                    <span className="status-badge status-green">{detectedEntities.length} entities masked</span>
                  </div>
                  <div className="min-h-[260px] whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-6 text-sm leading-7 text-slate-700">
                    {anonymizedFacts}
                  </div>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="ld-card-muted p-4">
                      <p className="ld-card-label mb-1">Jurisdiction</p>
                      <p className="text-sm font-extrabold text-slate-800">{jurisdiction}</p>
                    </div>
                    <div className="ld-card-muted p-4">
                      <p className="ld-card-label mb-1">Pleading type</p>
                      <p className="text-sm font-extrabold text-slate-800">{subcategory}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-4">
              <button onClick={() => setStep((prev) => Math.max(1, prev - 1))} disabled={step === 1} className="ld-secondary-action disabled:opacity-0">
                <i className="fas fa-arrow-left"></i> Back
              </button>

              {step < 3 ? (
                <button onClick={() => setStep((prev) => Math.min(3, prev + 1))} disabled={step === 2 && !anonymizedFacts} className="ld-primary-action disabled:cursor-not-allowed disabled:opacity-50">
                  Continue <i className="fas fa-arrow-right"></i>
                </button>
              ) : (
                <button onClick={handleLaunch} className="ld-primary-action">
                  Launch workspace <i className="fas fa-arrow-right"></i>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
