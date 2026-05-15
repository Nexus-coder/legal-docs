import Link from "next/link";
import { cookies } from "next/headers";
import { API_BASE_URL } from "@/lib/api";

type MatterRow = {
  id: number;
  case_number: string;
  division: string;
  workflow_state: string;
  verification_done: number;
  verification_total: number;
  last_activity?: string;
};

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
  const citationTotal = stats.citations_verified.total || 0;
  const citationProgress = citationTotal
    ? (stats.citations_verified.current / citationTotal) * 100
    : 0;

  return (
    <section className="ld-page">
      <div className="ld-page-inner">
        <div className="ld-page-header">
          <div>
            <p className="ld-eyebrow">Matter command desk</p>
            <h2 className="ld-title">Active pleadings, citations, and drafting flow.</h2>
            <p className="ld-subtitle">A working surface for live matters: start intake, monitor verification, and resume the drafting workspace without losing procedural context.</p>
          </div>
          <Link href="/pii-masking" className="ld-primary-action">
            <i className="fas fa-plus"></i> New drafting matter
          </Link>
        </div>

        <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="ld-card p-5">
            <div className="mb-5 flex items-center justify-between">
              <p className="ld-card-label">Citations verified</p>
              <span className="status-badge status-green"><i className="fas fa-check-circle"></i> Verified</span>
            </div>
            <div className="flex items-end gap-2">
              <span className="text-4xl font-extrabold text-slate-950">{stats.citations_verified.current}</span>
              <span className="pb-1 text-sm font-semibold text-slate-500">of {stats.citations_verified.total}</span>
            </div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full bg-green-500" style={{ width: `${citationProgress}%` }}></div>
            </div>
          </div>
          <div className="ld-card p-5">
            <div className="mb-5 flex items-center justify-between">
              <p className="ld-card-label">Recent eKLR matches</p>
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-50 text-blue-600">
                <i className="fas fa-database"></i>
              </span>
            </div>
            <span className="text-4xl font-extrabold text-slate-950">{stats.recent_matches}</span>
            <p className="mt-3 text-sm font-semibold text-slate-500">New precedents are available for retrieval and citation checks.</p>
          </div>
          <div className="ld-card p-5">
            <div className="mb-5 flex items-center justify-between">
              <p className="ld-card-label">Draft status</p>
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-50 text-amber-600">
                <i className="fas fa-file-alt"></i>
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="ld-card-muted p-3 text-center"><span className="block text-2xl font-extrabold">{stats.draft_status.drafting}</span><span className="ld-card-label">Drafting</span></div>
              <div className="ld-card-muted p-3 text-center"><span className="block text-2xl font-extrabold text-blue-600">{stats.draft_status.verified}</span><span className="ld-card-label">Verified</span></div>
              <div className="ld-card-muted p-3 text-center"><span className="block text-2xl font-extrabold text-green-600">{stats.draft_status.exported}</span><span className="ld-card-label">Exported</span></div>
            </div>
          </div>
        </div>

        <div className="ld-table-shell">
          <div className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4">
            <div>
              <p className="ld-card-label">Active matters</p>
              <p className="mt-1 text-sm text-slate-500">Resume a pleading packet or inspect verification progress.</p>
            </div>
            <input type="text" placeholder="Search case ID" className="w-44 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs outline-none focus:border-blue-500" />
          </div>
          <table>
          <thead>
            <tr>
              <th className="px-6 py-4">Case ID & Division</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Verification</th>
              <th className="px-6 py-4">Last Activity</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {matters.map((matter: MatterRow) => (
              (() => {
                const matterTotal = matter.verification_total || 0;
                const matterProgress = matterTotal ? (matter.verification_done / matterTotal) * 100 : 0;
                return (
              <tr key={matter.id} className="transition hover:bg-slate-50">
                <td className="px-6 py-4">
                  <p className="font-bold text-slate-950">{matter.case_number}</p>
                  <p className="text-xs text-slate-500">{matter.division}</p>
                </td>
                <td className="px-6 py-4">
                  <span className={`status-badge ${matter.workflow_state === 'draft_generated' ? 'status-blue' : matter.workflow_state === 'citations_verified' ? 'status-green' : 'status-amber'}`}>
                    {matter.workflow_state.replaceAll("_", " ")}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="text-xs text-slate-500">{matter.verification_done} / {matter.verification_total} Verified</div>
                  <div className="w-24 h-1.5 bg-slate-100 rounded-full mt-1 overflow-hidden">
                    <div className="bg-amber-400 h-full" style={{ width: `${matterProgress}%` }}></div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-500">{matter.last_activity}</td>
                <td className="px-6 py-4 text-right">
                  <Link href={`/drafting?matter_id=${matter.id}`} className="text-sm font-extrabold text-blue-600 hover:text-blue-800">
                    Resume <i className="fas fa-chevron-right ml-1"></i>
                  </Link>
                </td>
              </tr>
                );
              })()
            ))}
          </tbody>
        </table>
        </div>
      </div>
    </section>
  );
}
