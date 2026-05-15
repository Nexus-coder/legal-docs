export default function AdminScreen() {
  return (
    <section className="ld-page">
      <div className="ld-page-inner">
        <div className="ld-page-header">
          <div>
            <p className="ld-eyebrow">System auditor</p>
            <h2 className="ld-title">Knowledge base, confidence, and data controls.</h2>
            <p className="ld-subtitle">Monitor low-confidence generations, sync precedent sources, and keep the drafting system accountable.</p>
          </div>
          <button className="ld-secondary-action">
            <i className="fas fa-rotate"></i> Refresh audit
          </button>
        </div>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="ld-table-shell">
            <div className="flex items-center justify-between border-b border-red-100 bg-red-50 px-5 py-4">
              <div>
                <p className="font-mono text-[10px] font-extrabold uppercase tracking-[0.14em] text-red-600">
                  Hallucination monitor
                </p>
                <p className="mt-1 text-sm text-red-700">Low-confidence generations requiring human review.</p>
              </div>
              <span className="status-badge status-red">4 flagged items</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Draft reference</th>
                  <th>AI claim</th>
                  <th>Vector search status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr className="transition hover:bg-red-50/40">
                  <td className="font-mono text-xs font-bold text-slate-700">#ELC-45-G3</td>
                  <td className="text-sm text-slate-700">Cited &quot;Sec 22 of Land Act&quot; for Adverse Possession</td>
                  <td>
                    <span className="status-badge status-red">No match found</span>
                  </td>
                  <td>
                    <button className="text-sm font-extrabold text-blue-600 hover:text-blue-800">Open review</button>
                  </td>
                </tr>
                <tr className="transition hover:bg-amber-50/40">
                  <td className="font-mono text-xs font-bold text-slate-700">#CIV-19-D1</td>
                  <td className="text-sm text-slate-700">Relied on an unverified procedural deadline</td>
                  <td>
                    <span className="status-badge status-amber">Weak match</span>
                  </td>
                  <td>
                    <button className="text-sm font-extrabold text-blue-600 hover:text-blue-800">Open review</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <aside className="space-y-5">
            <div className="ld-card p-5">
              <div className="mb-4 flex items-center justify-between">
                <p className="ld-card-label">eKLR ingestion portal</p>
                <span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-50 text-blue-600">
                  <i className="fas fa-cloud-upload-alt"></i>
                </span>
              </div>
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center transition hover:border-blue-400">
                <i className="fas fa-file-arrow-up mb-3 text-3xl text-slate-300"></i>
                <p className="text-sm font-bold text-slate-700">Drop latest eKLR reports</p>
                <p className="mt-1 text-xs text-slate-500">PDF ingestion, chunking, and vector sync.</p>
              </div>
              <button className="mt-4 w-full rounded-lg bg-slate-950 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-slate-800">
                Sync vector database
              </button>
            </div>

            <div className="ld-card p-5">
              <div className="mb-4 flex items-center gap-2 text-green-700">
                <i className="fas fa-shield-alt"></i>
                <p className="ld-card-label text-green-700">Data sovereignty log</p>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between border-b border-slate-100 pb-3 text-xs">
                  <span className="text-slate-500">Last PII scrub</span>
                  <span className="font-extrabold text-slate-800">2 mins ago</span>
                </div>
                <div className="flex justify-between border-b border-slate-100 pb-3 text-xs">
                  <span className="text-slate-500">Encryption standard</span>
                  <span className="font-extrabold text-slate-800">AES-256</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">DPA posture</span>
                  <span className="font-extrabold text-green-700">Compliant</span>
                </div>
              </div>
            </div>

            <div className="rounded-lg bg-slate-950 p-5 text-white">
              <div className="mb-3 flex items-center gap-2 text-blue-300">
                <i className="fas fa-circle-notch animate-spin text-xs"></i>
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em]">Monitoring</span>
              </div>
              <p className="text-sm font-bold">Generating confidence report</p>
              <p className="mt-2 text-xs leading-5 text-slate-400">Review queue, citation mismatches, and knowledge freshness are being checked.</p>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
