export default function DraftingWorkspace() {
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
              <p className="font-bold border-b pb-1">GROUND 1: ADVERSE POSSESSION</p>
              <p>
                The Plaintiff has been in open, notorious, and continuous possession of{" "}
                <span className="bg-blue-200 rounded px-1">[LAND_ID_1]</span> for a period
                exceeding 12 years without the consent of the Registered Owner, meeting the
                threshold under <strong>Section 7 of the Limitation of Actions Act</strong>.
              </p>
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
            <div className="text-center mb-8">
              <h5 className="font-serif text-lg font-bold">REPUBLIC OF KENYA</h5>
              <p className="font-serif text-sm">IN THE ENVIRONMENT AND LAND COURT AT NAIROBI</p>
              <div className="border-y my-4 py-2 uppercase text-xs font-bold">
                Giella v. Cassman Brown & Co. Ltd [1973] EA 358
              </div>
            </div>
            <div className="font-serif text-sm leading-relaxed space-y-4">
              <p className="font-bold">HELD:</p>
              <p>
                "The conditions for the grant of an interlocutory injunction are now well
                settled in East Africa; first, an applicant must show a prima facie case with a
                probability of success. Secondly, an interlocutory injunction will not
                normally be granted unless the applicant might otherwise suffer irreparable
                injury..."
              </p>
              <p className="text-slate-400 italic mt-8 border-t pt-4">
                This section was used to generate Block #2 (Injunction Prayers).
              </p>
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
            <p className="text-xs font-bold mb-1">Giella v. Cassman Brown [1973]</p>
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
