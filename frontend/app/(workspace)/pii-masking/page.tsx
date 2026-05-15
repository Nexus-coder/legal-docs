"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";
import { Button } from "@/app/components/ui/Button";
import { Badge } from "@/app/components/ui/Badge";
import { Card, CardLabel } from "@/app/components/ui/Card";

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
          <Badge variant="blue" icon="fas fa-shield-alt">Privacy guard active</Badge>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-error-border bg-error-bg px-4 py-3 text-sm font-semibold text-error">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[300px_minmax(0,1fr)]">
          <Card className="p-4 h-fit">
            <CardLabel className="mb-4">Setup flow</CardLabel>
            <div className="space-y-2">
              {steps.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setStep(item.id)}
                  className={`flex w-full items-center gap-3 rounded-xl border-1.5 px-3 py-3 text-left transition-all duration-200 ${
                    step === item.id ? "border-brand-blue/30 bg-brand-blue/5 text-brand-blue" : "border-border bg-white text-slate-600 hover:border-brand-blue/20 hover:bg-slate-50"
                  }`}
                >
                  <span className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${step === item.id ? "bg-brand-blue text-white" : "bg-slate-100 text-slate-500"}`}>
                    <i className={`fas ${item.icon} text-xs`}></i>
                  </span>
                  <span>
                    <span className="block text-sm font-extrabold">{item.label}</span>
                    <CardLabel className="opacity-60">Step {item.id}</CardLabel>
                  </span>
                </button>
              ))}
            </div>
            <div className="mt-5 rounded-xl bg-slate-950 p-5 text-white shadow-2xl">
              <div className="mb-3 flex items-center gap-2 text-brand-blue/60">
                <i className="fas fa-circle-notch animate-spin text-xs"></i>
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em]">Standing by</span>
              </div>
              <p className="text-sm font-bold">Drafting handoff queue</p>
              <p className="mt-2 text-xs leading-5 text-slate-400 font-medium">The workspace will receive jurisdiction, pleading type, anonymized facts, and masked entity evidence.</p>
            </div>
          </Card>

          <Card padding="none" className="overflow-hidden">
            <div className="grid grid-cols-3 border-b border-border">
              {steps.map((item) => (
                <div key={item.id} className={`ld-step !py-4 transition-all duration-300 ${step >= item.id ? "ld-step-active" : ""}`}>
                  <span className="text-xs font-black tracking-wide uppercase">{item.label}</span>
                </div>
              ))}
            </div>

            <div className="min-h-[520px] p-6 md:p-10">
              {step === 1 && (
                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                    <div className="flex flex-col gap-2">
                      <CardLabel>Court division</CardLabel>
                      <select
                        value={jurisdiction}
                        onChange={(e) => setJurisdiction(e.target.value)}
                        className="w-full rounded-xl border-1.5 border-border bg-[#f1f5fb] p-4 text-[0.9375rem] font-bold text-slate-900 outline-none transition focus:border-brand-blue focus:bg-white focus:ring-4 focus:ring-brand-blue/10"
                      >
                        <option>Environment and Land Court (ELC)</option>
                        <option>High Court - Civil Division</option>
                        <option>Commercial & Tax Division</option>
                      </select>
                    </div>
                    <div className="flex flex-col gap-2">
                      <CardLabel>Pleading sub-category</CardLabel>
                      <select
                        value={subcategory}
                        onChange={(e) => setSubcategory(e.target.value)}
                        className="w-full rounded-xl border-1.5 border-border bg-[#f1f5fb] p-4 text-[0.9375rem] font-bold text-slate-900 outline-none transition focus:border-brand-blue focus:bg-white focus:ring-4 focus:ring-brand-blue/10"
                      >
                        <option>Adverse Possession</option>
                        <option>Boundary Dispute</option>
                        <option>Landlord-Tenant Conflict</option>
                        <option>Personal Injury Claim</option>
                      </select>
                    </div>
                  </div>
                  <Card variant="muted" className="flex items-start gap-4 p-5 !border-amber-100 !bg-amber-50/50">
                    <i className="fas fa-info-circle mt-0.5 text-warning text-lg"></i>
                    <p className="text-sm leading-relaxed text-slate-700 font-medium">The selected legal frame controls retrieval, citation checking, and the drafting packet assembled in the next workspace.</p>
                  </Card>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex flex-col gap-2">
                    <CardLabel>Instruction box</CardLabel>
                    <textarea
                      placeholder="Paste case facts or summary instructions here. E.g. 'The plaintiff has occupied LR 209/45 since 1998...'"
                      value={facts}
                      onChange={(e) => setFacts(e.target.value)}
                      className="h-80 w-full resize-none rounded-xl border-1.5 border-border bg-[#f1f5fb] p-6 text-[0.9375rem] font-medium leading-relaxed text-slate-800 outline-none transition focus:border-brand-blue focus:bg-white focus:ring-4 focus:ring-brand-blue/10 placeholder-slate-400"
                    ></textarea>
                  </div>
                  <div className="flex flex-col gap-6 rounded-xl bg-slate-950 p-6 text-white md:flex-row md:items-center md:justify-between shadow-xl">
                    <div className="flex items-center gap-4">
                      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-blue/20 text-brand-blue">
                        <i className="fas fa-shield-alt text-xl"></i>
                      </span>
                      <div>
                        <p className="text-sm font-black tracking-tight">Privacy Guard active</p>
                        <p className="text-xs text-slate-400 font-medium mt-0.5">Names, dates, and identifiers will be masked before drafting.</p>
                      </div>
                    </div>
                    <Button onClick={handleAnalyze} loading={isAnalyzing} disabled={!facts.trim()} size="lg" className="md:w-auto w-full">
                      <i className="fas fa-wand-magic-sparkles mr-2"></i> Analyze & mask PII
                    </Button>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <CardLabel>Anonymized facts preview</CardLabel>
                      <p className="mt-1 text-sm text-slate-500 font-medium">Review the clean packet before handoff.</p>
                    </div>
                    <Badge variant="green" icon="fas fa-check-circle">{detectedEntities.length} entities masked</Badge>
                  </div>
                  <div className="min-h-[260px] whitespace-pre-wrap rounded-xl border-1.5 border-border bg-[#f1f5fb] p-8 text-[0.9375rem] leading-relaxed text-slate-700 font-medium shadow-inner">
                    {anonymizedFacts}
                  </div>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Card variant="muted" padding="sm" className="flex flex-col gap-1">
                      <CardLabel className="opacity-60">Jurisdiction</CardLabel>
                      <p className="text-sm font-black text-slate-800">{jurisdiction}</p>
                    </Card>
                    <Card variant="muted" padding="sm" className="flex flex-col gap-1">
                      <CardLabel className="opacity-60">Pleading type</CardLabel>
                      <p className="text-sm font-black text-slate-800">{subcategory}</p>
                    </Card>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-border bg-slate-50/50 px-8 py-6">
              <Button variant="secondary" onClick={() => setStep((prev) => Math.max(1, prev - 1))} disabled={step === 1} className={step === 1 ? "opacity-0 pointer-events-none" : ""}>
                <i className="fas fa-arrow-left mr-2"></i> Back
              </Button>

              {step < 3 ? (
                <Button onClick={() => setStep((prev) => Math.min(3, prev + 1))} disabled={step === 2 && !anonymizedFacts}>
                  Continue <i className="fas fa-arrow-right ml-2"></i>
                </Button>
              ) : (
                <Button onClick={handleLaunch} size="lg" className="px-8 shadow-premium">
                  Launch workspace <i className="fas fa-arrow-right ml-2"></i>
                </Button>
              )}
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}
