import { API_BASE_URL } from "@/lib/api";

async function getDraft() {
  try {
    const res = await fetch(`${API_BASE_URL}drafting/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jurisdiction: "Environment & Land Court",
        subcategory: "Adverse Possession",
        instructions: "Draft grounds for adverse possession claim."
      }),
      next: { revalidate: 0 }
    });
    if (!res.ok) return { blocks: [] };
    return res.json();
  } catch (e) {
    return { blocks: [] };
  }
}

async function getCitations() {
  try {
    const res = await fetch(`${API_BASE_URL}drafting/citations`, { next: { revalidate: 0 } });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    return null;
  }
}

export default async function DraftingWorkspace() {
  const [draftData, citation] = await Promise.all([
    getDraft(),
    getCitations()
  ]);

  const block = draftData?.blocks?.[0] || {
    title: "GROUND 1: ADVERSE POSSESSION",
    content: "The Plaintiff has been in open, notorious, and continuous possession of [LAND_ID_1] for a period exceeding 12 years without the consent of the Registered Owner, meeting the threshold under Section 7 of the Limitation of Actions Act.",
  };

  return (
    <section className="flex-1 flex h-full overflow-hidden">
      <div className="w-1/3 border-r border-slate-200 bg-white flex flex-col">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <span className="font-bold text-sm tracking-tight">
            <i className="fas fa-robot text-blue-600 mr-2"></i> AI CO-PILOT
          </span>
          <span className="text-[10px] px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-bold uppercase tracking-widest">
            Generating...
          </span>
        </div>
        <div className="flex-1 p-6 space-y-6 overflow-y-auto">
          <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
            <h4 className="text-xs font-bold text-blue-900 mb-2 uppercase tracking-widest">
              Pleading Block: Grounds
            </h4>
            <div className="space-y-4 text-sm leading-relaxed text-slate-700">
              <p className="font-bold border-b pb-1">{block.title}</p>
              <p>{block.content}</p>
            </div>
          </div>
          <div className="p-4 border border-slate-200 rounded-lg bg-white shadow-sm opacity-50 grayscale">
            <h4 className="text-xs font-bold text-slate-500 mb-2 uppercase tracking-widest">
              Pleading Block: Prayers
            </h4>
            <p className="text-sm italic">Waiting for verification of grounds...</p>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-slate-100 flex flex-col">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white shadow-sm">
          <span className="font-bold text-sm text-slate-600 uppercase tracking-widest">
            <i className="fas fa-book-open mr-2 text-amber-500"></i> Ground Truth: Citation Reference
          </span>
          <div className="flex space-x-2">
            <span className="px-3 py-1 bg-slate-200 text-slate-700 text-xs rounded-full font-bold">
              eKLR 2024
            </span>
          </div>
        </div>
        <div className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-2xl mx-auto bg-white p-10 shadow-lg min-h-full border-t-4 border-amber-400">
            {citation ? (
              <>
                <div className="text-center mb-8">
                  <h5 className="font-serif text-lg font-bold">REPUBLIC OF KENYA</h5>
                  <p className="font-serif text-sm">{citation.court}</p>
                  <div className="border-y my-4 py-2 uppercase text-xs font-bold">
                    {citation.title}
                  </div>
                </div>
                <div className="font-serif text-sm leading-relaxed space-y-4">
                  <p className="font-bold">HELD:</p>
                  <p>{citation.held}</p>
                  <p className="text-slate-400 italic mt-8 border-t pt-4">
                    This section was used to generate Block #1 (Grounds).
                  </p>
                </div>
              </>
            ) : (
                <div className="text-center text-slate-500 py-20">Loading Citations...</div>
            )}
          </div>
        </div>
      </div>

      <div className="w-80 bg-slate-50 border-l border-slate-200 flex flex-col">
        <div className="p-4 border-b border-slate-200 bg-white">
          <h4 className="font-bold text-sm flex items-center">
            <i className="fas fa-check-double text-green-600 mr-2"></i> Verification Checklist
          </h4>
          <div className="w-full bg-slate-200 h-1.5 rounded-full mt-3 overflow-hidden">
            <div className="bg-green-500 h-full w-[50%] transition-all"></div>
          </div>
          <p className="text-[10px] text-slate-500 mt-2 font-bold uppercase">
            1 of 2 citations approved
          </p>
        </div>
        <div className="flex-1 p-4 space-y-4 overflow-y-auto">
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-bold text-green-700 uppercase">Statute</span>
              <i className="fas fa-check-circle text-green-500"></i>
            </div>
            <p className="text-xs font-bold mb-1">Limitation of Actions Act, Sec 7</p>
            <p className="text-[10px] text-slate-600 mb-3">Matching Confidence: 100%</p>
            <button className="w-full py-1.5 bg-white border border-green-200 text-green-700 text-xs font-bold rounded shadow-sm opacity-50" disabled>
              Verified
            </button>
          </div>

          <div className="p-3 bg-white border border-blue-200 rounded-lg shadow-sm">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-bold text-blue-700 uppercase">Precedent</span>
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
            </div>
            <p className="text-xs font-bold mb-1">{citation?.title?.split('[')[0] || "Giella v. Cassman Brown"}</p>
            <p className="text-[10px] text-slate-600 mb-3">Matching Confidence: 94%</p>
            <button className="w-full py-1.5 bg-blue-600 text-white text-xs font-bold rounded shadow-md hover:bg-blue-700">
              Verify & Approve
            </button>
          </div>
        </div>
        <div className="p-4 border-t border-slate-200 bg-white">
          <button className="w-full py-3 bg-slate-200 text-slate-400 font-bold rounded-lg cursor-not-allowed group relative">
            <i className="fas fa-file-export mr-2"></i> Export to .docx
            <span className="absolute bottom-full left-0 w-full mb-2 bg-slate-800 text-white text-[10px] p-2 rounded hidden group-hover:block">
              Verify all citations to unlock export.
            </span>
          </button>
        </div>
      </div>
    </section>
  );
}
