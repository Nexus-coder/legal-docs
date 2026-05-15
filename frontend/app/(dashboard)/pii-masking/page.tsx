"use client";

import { useState } from "react";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";

export default function PIIMasking() {
  const [defendant, setDefendant] = useState("Samuel Mwangi Kamau");
  const [landId, setLandId] = useState("LR NO 209/45/8");
  const [facts, setFacts] = useState("");
  const [anonymizedFacts, setAnonymizedFacts] = useState("");
  const [isMasking, setIsMasking] = useState(false);

  const handleMask = async () => {
    if (!facts.trim()) return;
    setIsMasking(true);
    try {
      const res = await fetch(`${API_BASE_URL}pii/mask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          facts,
          entities: {
            [defendant]: "[DEFENDANT_1]",
            [landId]: "[LAND_ID_1]"
          }
        })
      });
      if (res.ok) {
        const data = await res.json();
        setAnonymizedFacts(data.anonymized_text);
      }
    } catch (error) {
      console.error("Masking failed", error);
    } finally {
      setIsMasking(false);
    }
  };

  return (
    <section className="flex-1 p-8 flex justify-center">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-slate-900">Context & Privacy Setup</h2>
          <p className="text-slate-500 mt-2">Ground your case in law and mask sensitive data before AI processing.</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
          <div className="flex border-b border-slate-100">
            <div className="flex-1 p-4 text-center border-b-2 border-blue-600 bg-blue-50">
              <span className="inline-block w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold leading-6 mb-1">1</span>
              <p className="text-xs font-bold text-blue-800">Jurisdiction</p>
            </div>
            <div className="flex-1 p-4 text-center">
              <span className="inline-block w-6 h-6 rounded-full bg-slate-200 text-slate-600 text-xs font-bold leading-6 mb-1">2</span>
              <p className="text-xs font-bold text-slate-400">PII Masking</p>
            </div>
            <div className="flex-1 p-4 text-center text-slate-400">
              <span className="inline-block w-6 h-6 rounded-full bg-slate-200 text-slate-600 text-xs font-bold leading-6 mb-1">3</span>
              <p className="text-xs font-bold text-slate-400">Facts Input</p>
            </div>
          </div>

          <div className="p-8 space-y-8">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">Court Division</label>
                <select className="w-full border-slate-200 rounded-lg p-3 bg-slate-50 focus:ring-2 focus:ring-blue-500">
                  <option>Environment and Land Court (ELC)</option>
                  <option>High Court - Civil Division</option>
                  <option>Commercial & Tax Division</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">Pleading Sub-category</label>
                <select className="w-full border-slate-200 rounded-lg p-3 bg-slate-50 focus:ring-2 focus:ring-blue-500">
                  <option>Adverse Possession</option>
                  <option>Boundary Dispute</option>
                  <option>Landlord-Tenant Conflict</option>
                </select>
              </div>
            </div>

            <div className="p-6 bg-slate-900 rounded-xl text-white">
              <h4 className="flex items-center text-sm font-bold mb-4">
                <i className="fas fa-mask text-amber-400 mr-2"></i> Real-time PII Anonymizer
              </h4>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="relative">
                    <input type="text" value={defendant} onChange={e => setDefendant(e.target.value)}
                      className="w-full bg-slate-800 border-slate-700 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500" />
                    <span className="absolute right-3 top-3 text-[10px] bg-blue-600 px-2 py-0.5 rounded mask-badge uppercase">[DEFENDANT_1]</span>
                  </div>
                  <div className="relative">
                    <input type="text" value={landId} onChange={e => setLandId(e.target.value)}
                      className="w-full bg-slate-800 border-slate-700 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500" />
                    <span className="absolute right-3 top-3 text-[10px] bg-blue-600 px-2 py-0.5 rounded mask-badge uppercase">[LAND_ID_1]</span>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Instruction Box (Case Facts)</label>
              <textarea placeholder="Paste case facts or summary instructions here..."
                value={facts} onChange={e => setFacts(e.target.value)}
                className="w-full h-40 border-slate-200 rounded-lg p-4 bg-slate-50 focus:ring-2 focus:ring-blue-500 text-sm mb-4"></textarea>
              <div className="flex justify-end">
                <button 
                  onClick={handleMask}
                  disabled={isMasking || !facts.trim()}
                  className="bg-amber-500 text-white px-4 py-2 rounded font-bold text-sm hover:bg-amber-600 shadow disabled:opacity-50 transition">
                  {isMasking ? "Anonymizing..." : "Anonymize Facts"}
                </button>
              </div>
              {anonymizedFacts && (
                <div className="mt-4">
                  <label className="block text-sm font-bold text-slate-700 mb-2">Anonymized Facts (Preview)</label>
                  <p className="w-full min-h-20 border-slate-200 border rounded-lg p-4 bg-slate-100 text-sm whitespace-pre-wrap">{anonymizedFacts}</p>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-100 text-right">
              <Link href="/drafting"
                className="bg-blue-600 text-white px-8 py-3 rounded-lg font-bold hover:bg-blue-700 transition inline-block">
                Launch Unified Workspace <i className="fas fa-arrow-right ml-2"></i>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
