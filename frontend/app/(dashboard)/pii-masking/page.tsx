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
        })
      });
      if (res.ok) {
        const data = await res.json();
        setDetectedEntities(data.entities);
        setAnonymizedFacts(data.masked_text);
        setStep(3); // Move to review step
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
    <section className="flex-1 p-8 flex justify-center">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-slate-900">Context & Privacy Setup</h2>
          <p className="text-slate-500 mt-2">Ground your case in law and mask sensitive data before AI processing.</p>
        </div>
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            {error}
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
          {/* Progress Header */}
          <div className="flex border-b border-slate-100">
            <div className={`flex-1 p-4 text-center border-b-2 transition ${step >= 1 ? 'border-blue-600 bg-blue-50' : 'border-transparent'}`}>
              <span className={`inline-block w-6 h-6 rounded-full text-xs font-bold leading-6 mb-1 ${step >= 1 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'}`}>1</span>
              <p className={`text-xs font-bold ${step >= 1 ? 'text-blue-800' : 'text-slate-400'}`}>Jurisdiction</p>
            </div>
            <div className={`flex-1 p-4 text-center border-b-2 transition ${step >= 2 ? 'border-blue-600 bg-blue-50' : 'border-transparent'}`}>
              <span className={`inline-block w-6 h-6 rounded-full text-xs font-bold leading-6 mb-1 ${step >= 2 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'}`}>2</span>
              <p className={`text-xs font-bold ${step >= 2 ? 'text-blue-800' : 'text-slate-400'}`}>Facts & PII</p>
            </div>
            <div className={`flex-1 p-4 text-center border-b-2 transition ${step >= 3 ? 'border-blue-600 bg-blue-50' : 'border-transparent'}`}>
              <span className={`inline-block w-6 h-6 rounded-full text-xs font-bold leading-6 mb-1 ${step >= 3 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'}`}>3</span>
              <p className={`text-xs font-bold ${step >= 3 ? 'text-blue-800' : 'text-slate-400'}`}>Review</p>
            </div>
          </div>

          <div className="p-8 min-h-[400px] flex flex-col justify-between">
            {step === 1 && (
              <div className="space-y-8 animate-in fade-in duration-500">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">Court Division</label>
                    <select 
                      value={jurisdiction}
                      onChange={(e) => setJurisdiction(e.target.value)}
                      className="w-full border-slate-200 rounded-lg p-3 bg-slate-50 focus:ring-2 focus:ring-blue-500 outline-none transition"
                    >
                      <option>Environment and Land Court (ELC)</option>
                      <option>High Court - Civil Division</option>
                      <option>Commercial & Tax Division</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">Pleading Sub-category</label>
                    <select 
                      value={subcategory}
                      onChange={(e) => setSubcategory(e.target.value)}
                      className="w-full border-slate-200 rounded-lg p-3 bg-slate-50 focus:ring-2 focus:ring-blue-500 outline-none transition"
                    >
                      <option>Adverse Possession</option>
                      <option>Boundary Dispute</option>
                      <option>Landlord-Tenant Conflict</option>
                      <option>Personal Injury Claim</option>
                    </select>
                  </div>
                </div>
                <div className="p-4 bg-amber-50 rounded-lg border border-amber-100 flex items-start">
                  <i className="fas fa-info-circle text-amber-500 mt-1 mr-3"></i>
                  <p className="text-xs text-amber-800 leading-relaxed">
                    Selecting the correct jurisdiction helps the AI co-pilot retrieve relevant precedents and statutory frameworks for your pleading.
                  </p>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6 animate-in slide-in-from-right-4 fade-in duration-500">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-2">Instruction Box (Case Facts)</label>
                  <textarea 
                    placeholder="Paste case facts or summary instructions here. E.g. 'The plaintiff has occupied LR 209/45 since 1998...'"
                    value={facts} 
                    onChange={e => setFacts(e.target.value)}
                    className="w-full h-64 border-slate-200 rounded-lg p-4 bg-slate-50 focus:ring-2 focus:ring-blue-500 text-sm outline-none transition resize-none"
                  ></textarea>
                </div>
                <div className="p-4 bg-slate-900 rounded-xl text-white flex items-center justify-between">
                  <div className="flex items-center">
                    <i className="fas fa-shield-alt text-blue-400 mr-3"></i>
                    <div>
                      <p className="text-sm font-bold">Privacy Guard Active</p>
                      <p className="text-[10px] text-slate-400">ML models will automatically identify names, dates, and locations.</p>
                    </div>
                  </div>
                  <button 
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || !facts.trim()}
                    className="bg-blue-600 text-white px-6 py-2 rounded-lg font-bold text-sm hover:bg-blue-700 disabled:opacity-50 transition"
                  >
                    {isAnalyzing ? (
                      <span className="flex items-center">
                        <i className="fas fa-circle-notch animate-spin mr-2"></i> Analyzing...
                      </span>
                    ) : "Analyze & Mask PII"}
                  </button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-6 animate-in slide-in-from-right-4 fade-in duration-500">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-bold text-slate-700">Anonymized Facts (Preview)</h4>
                  <span className="text-[10px] bg-green-100 text-green-700 px-2 py-1 rounded-full font-bold uppercase">
                    {detectedEntities.length} Entities Masked
                  </span>
                </div>
                <div className="relative group">
                  <div className="w-full min-h-[250px] border-slate-200 border rounded-lg p-6 bg-slate-50 text-sm whitespace-pre-wrap leading-relaxed text-slate-600">
                    {anonymizedFacts}
                  </div>
                  <button 
                    onClick={() => setStep(2)}
                    className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition bg-white shadow-sm border border-slate-200 px-3 py-1 rounded text-xs font-bold text-slate-600 hover:bg-slate-50"
                  >
                    Edit Raw Facts
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 border border-slate-100 rounded-lg bg-slate-50">
                    <p className="text-[10px] uppercase font-bold text-slate-400 mb-1">Jurisdiction</p>
                    <p className="text-sm font-bold text-slate-700">{jurisdiction}</p>
                  </div>
                  <div className="p-4 border border-slate-100 rounded-lg bg-slate-50">
                    <p className="text-[10px] uppercase font-bold text-slate-400 mb-1">Pleading Type</p>
                    <p className="text-sm font-bold text-slate-700">{subcategory}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation Controls */}
            <div className="flex justify-between items-center pt-8 border-t border-slate-100 mt-8">
              <button 
                onClick={() => setStep(prev => Math.max(1, prev - 1))}
                disabled={step === 1}
                className="text-slate-400 font-bold hover:text-slate-600 disabled:opacity-0 transition"
              >
                <i className="fas fa-arrow-left mr-2"></i> Back
              </button>

              {step < 3 ? (
                <button 
                  onClick={() => setStep(prev => Math.min(3, prev + 1))}
                  disabled={step === 2 && !anonymizedFacts} // Must analyze in step 2
                  className="bg-slate-900 text-white px-8 py-3 rounded-lg font-bold hover:bg-slate-800 transition shadow-lg"
                >
                  Continue <i className="fas fa-arrow-right ml-2"></i>
                </button>
              ) : (
                <button 
                  onClick={handleLaunch}
                  className="bg-blue-600 text-white px-10 py-3 rounded-lg font-bold hover:bg-blue-700 transition shadow-xl shadow-blue-100"
                >
                  Launch Workspace <i className="fas fa-rocket ml-2"></i>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

