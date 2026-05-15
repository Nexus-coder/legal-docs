import Link from "next/link";
import { cookies } from "next/headers";
import { API_BASE_URL } from "@/lib/api";

async function getStats(token: string) {
  const res = await fetch(`${API_BASE_URL}stats`, {
    headers: { Authorization: `Bearer ${token}` },
    next: { revalidate: 0 },
  });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

async function getMatters(token: string) {
  const res = await fetch(`${API_BASE_URL}matters/`, {
    headers: { Authorization: `Bearer ${token}` },
    next: { revalidate: 0 },
  });
  if (!res.ok) throw new Error("Failed to fetch matters");
  return res.json();
}

export default async function Dashboard() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  if (!token) {
    // Should be handled by middleware, but safety first
    return <div>Unauthorized</div>;
  }

  const stats = await getStats(token);
  const matters = await getMatters(token);

  return (
    <section className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Matter Management</h2>
          <p className="text-slate-500">Manage your active litigation and pleadings</p>
        </div>
        <Link href="/pii-masking"
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-bold shadow-lg shadow-blue-200 flex items-center transition">
          <i className="fas fa-plus mr-2"></i> Quick Start Pleading
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-slate-500">Citations Verified</p>
            <i className="fas fa-check-circle text-green-500"></i>
          </div>
          <div className="flex items-end space-x-2">
            <span className="text-4xl font-bold">{stats.citations_verified.current}</span>
            <span className="text-slate-400 mb-1">/ {stats.citations_verified.total} Total</span>
          </div>
          <div className="w-full bg-slate-100 h-2 rounded-full mt-4 overflow-hidden">
            <div className="bg-green-500 h-full" style={{ width: `${(stats.citations_verified.current / stats.citations_verified.total) * 100}%` }}></div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-slate-500">Recent eKLR Matches</p>
            <i className="fas fa-database text-blue-500"></i>
          </div>
          <span className="text-4xl font-bold">{stats.recent_matches}</span>
          <p className="text-xs text-slate-400 mt-2">+5 new precedents since yesterday</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-slate-500">Draft Status</p>
            <i className="fas fa-file-alt text-amber-500"></i>
          </div>
          <div className="flex space-x-4">
            <div className="text-center"><span className="block text-xl font-bold">{stats.draft_status.drafting}</span><span
              className="text-[10px] text-slate-400 uppercase">Drafting</span></div>
            <div className="text-center"><span className="block text-xl font-bold text-blue-600">{stats.draft_status.verified}</span><span
              className="text-[10px] text-slate-400 uppercase">Verified</span></div>
            <div className="text-center"><span className="block text-xl font-bold text-green-600">{stats.draft_status.exported}</span><span
              className="text-[10px] text-slate-400 uppercase">Exported</span></div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
          <h3 className="font-bold text-slate-700 uppercase text-xs tracking-wider">Active Matters</h3>
          <div className="flex space-x-2">
            <input type="text" placeholder="Search Case ID..."
              className="text-xs px-3 py-1 border rounded-md" />
          </div>
        </div>
        <table className="w-full text-left">
          <thead className="text-xs uppercase text-slate-400 border-b">
            <tr>
              <th className="px-6 py-4">Case ID & Division</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Verification</th>
              <th className="px-6 py-4">Last Activity</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {matters.map((matter: any) => (
              <tr key={matter.id} className="hover:bg-slate-50 transition">
                <td className="px-6 py-4">
                  <p className="font-bold">{matter.case_number}</p>
                  <p className="text-xs text-slate-500">{matter.division}</p>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 ${matter.status === 'Drafting' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-700'} text-[10px] font-bold rounded uppercase tracking-wide`}>
                    {matter.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="text-xs text-slate-500">{matter.verification_done} / {matter.verification_total} Verified</div>
                  <div className="w-24 h-1.5 bg-slate-100 rounded-full mt-1 overflow-hidden">
                    <div className="bg-amber-400 h-full" style={{ width: `${(matter.verification_done / matter.verification_total) * 100}%` }}></div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-500">{matter.last_activity}</td>
                <td className="px-6 py-4 text-right">
                  <Link href="/drafting" className="text-blue-600 hover:text-blue-800 font-semibold text-sm">
                    Resume <i className="fas fa-chevron-right ml-1"></i>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
