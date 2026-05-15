export default function AdminScreen() {
  return (
    <section className="flex-1 p-8">
      <div className="grid grid-cols-12 gap-8">
        <div className="col-span-12">
          <h2 className="text-3xl font-bold text-slate-900">Knowledge Base Auditor</h2>
          <p className="text-slate-500">System health, hallucination monitoring, and eKLR ingestion.</p>
        </div>

        <div className="col-span-8 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-4 bg-red-50 border-b border-red-100 flex justify-between items-center">
            <h3 className="font-bold text-red-700 text-xs tracking-wider uppercase">
              <i className="fas fa-exclamation-triangle mr-2"></i> Hallucination Monitor (Low Confidence Generations)
            </h3>
            <span className="text-[10px] bg-red-100 text-red-700 px-2 py-1 rounded font-bold">4 Flagged Items</span>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-400 text-xs uppercase font-bold border-b">
              <tr>
                <th className="px-6 py-4">Draft Reference</th>
                <th className="px-6 py-4">AI Claim</th>
                <th className="px-6 py-4">Vector Search Status</th>
                <th className="px-6 py-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr className="hover:bg-red-50/30">
                <td className="px-6 py-4 font-mono text-xs">#ELC-45-G3</td>
                <td className="px-6 py-4">Cited &quot;Sec 22 of Land Act&quot; for Adverse Possession</td>
                <td className="px-6 py-4">
                  <span className="px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-xs">No Match Found</span>
                </td>
                <td className="px-6 py-4">
                  <button className="text-blue-600 font-bold text-xs underline">Retrain Model</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="col-span-4 space-y-6">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h4 className="font-bold mb-4 text-sm uppercase tracking-wider">eKLR Ingestion Portal</h4>
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-blue-400 transition cursor-pointer">
              <i className="fas fa-cloud-upload-alt text-3xl text-slate-300 mb-2"></i>
              <p className="text-xs text-slate-500">Drag & drop latest eKLR PDF reports here</p>
            </div>
            <button className="w-full mt-4 bg-slate-900 text-white py-2 rounded-lg font-bold text-sm">
              Sync Vector Database
            </button>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h4 className="font-bold mb-4 text-sm uppercase tracking-wider text-green-700">
              <i className="fas fa-shield-alt mr-2"></i> Data Sovereignty Log
            </h4>
            <div className="space-y-3">
              <div className="flex justify-between text-[10px] border-b pb-2">
                <span className="text-slate-500">Last PII Scrub</span>
                <span className="font-bold">2 mins ago</span>
              </div>
              <div className="flex justify-between text-[10px] border-b pb-2">
                <span className="text-slate-500">Encryption Standard</span>
                <span className="font-bold">AES-256 (DPA Compliant)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
