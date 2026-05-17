import Link from "next/link";
import { Suspense } from "react";
import { cookies } from "next/headers";
import { API_BASE_URL } from "@/lib/api";
import { Card, CardLabel } from "@/app/components/ui/Card";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Input } from "@/app/components/ui/Input";
import { DashboardSkeleton } from "./_components/DashboardSkeleton";

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

async function DashboardContent({ token }: { token: string }) {
  const stats = await getStats(token);
  const matters = await getMatters(token);
  const citationTotal = stats.citations_verified.total || 0;
  const citationProgress = citationTotal
    ? (stats.citations_verified.current / citationTotal) * 100
    : 0;

  return (
    <>
      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <CardLabel>Citations verified</CardLabel>
            <Badge variant="green" icon="fas fa-check-circle">Verified</Badge>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-4xl font-extrabold text-slate-950">{stats.citations_verified.current}</span>
            <span className="pb-1 text-sm font-semibold text-slate-500">of {stats.citations_verified.total}</span>
          </div>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full bg-success" style={{ width: `${citationProgress}%` }}></div>
          </div>
        </Card>

        <Card>
          <div className="mb-5 flex items-center justify-between">
            <CardLabel>Recent eKLR matches</CardLabel>
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-50 text-brand-blue">
              <i className="fas fa-database"></i>
            </span>
          </div>
          <span className="text-4xl font-extrabold text-slate-950">{stats.recent_matches}</span>
          <p className="mt-3 text-sm font-semibold text-slate-500">New precedents are available for retrieval and citation checks.</p>
        </Card>

        <Card>
          <div className="mb-5 flex items-center justify-between">
            <CardLabel>Draft status</CardLabel>
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-50 text-warning">
              <i className="fas fa-file-alt"></i>
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Card variant="muted" padding="sm" className="text-center">
              <span className="block text-2xl font-extrabold">{stats.draft_status.drafting}</span>
              <CardLabel>Drafting</CardLabel>
            </Card>
            <Card variant="muted" padding="sm" className="text-center">
              <span className="block text-2xl font-extrabold text-brand-blue">{stats.draft_status.verified}</span>
              <CardLabel>Verified</CardLabel>
            </Card>
            <Card variant="muted" padding="sm" className="text-center">
              <span className="block text-2xl font-extrabold text-success">{stats.draft_status.exported}</span>
              <CardLabel>Exported</CardLabel>
            </Card>
          </div>
        </Card>
      </div>

      <div className="ld-table-shell">
        <div className="flex items-center justify-between border-b border-border bg-white px-5 py-4">
          <div>
            <CardLabel>Active matters</CardLabel>
            <p className="mt-1 text-sm text-slate-500">Resume a pleading packet or inspect verification progress.</p>
          </div>
          <div className="w-44">
            <Input placeholder="Search case ID" className="!py-2 !rounded-md text-xs" />
          </div>
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
            {matters.map((matter: MatterRow) => {
              const matterTotal = matter.verification_total || 0;
              const matterProgress = matterTotal ? (matter.verification_done / matterTotal) * 100 : 0;
              return (
                <tr key={matter.id} className="transition hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <p className="font-bold text-slate-950">{matter.case_number}</p>
                    <p className="text-xs text-slate-500">{matter.division}</p>
                  </td>
                  <td className="px-6 py-4">
                    <Badge 
                      variant={matter.workflow_state === 'draft_generated' ? 'blue' : matter.workflow_state === 'citations_verified' ? 'green' : 'amber'}
                    >
                      {matter.workflow_state.replaceAll("_", " ")}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-xs text-slate-500 font-medium">{matter.verification_done} / {matter.verification_total} Verified</div>
                    <div className="w-24 h-1.5 bg-slate-100 rounded-full mt-1 overflow-hidden">
                      <div className="bg-warning h-full" style={{ width: `${matterProgress}%` }}></div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-500 font-medium">{matter.last_activity}</td>
                  <td className="px-6 py-4 text-right">
                    <Link href={`/drafting?matter_id=${matter.id}`} className="text-sm font-extrabold text-brand-blue hover:text-brand-blue-hover transition-colors">
                      Resume <i className="fas fa-chevron-right ml-1"></i>
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default async function Dashboard() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  if (!token) {
    // Should be handled by middleware, but safety first
    return <div>Unauthorized</div>;
  }

  return (
    <section className="ld-page">
      <div className="ld-page-inner">
        <div className="ld-page-header">
          <div>
            <p className="ld-eyebrow">Matter command desk</p>
            <h2 className="ld-title">Active pleadings, citations, and drafting flow.</h2>
            <p className="ld-subtitle">A working surface for live matters: start intake, monitor verification, and resume the drafting workspace without losing procedural context.</p>
          </div>
          <Link href="/pii-masking" passHref legacyBehavior>
            <Button size="lg" className="ld-primary-action">
              <i className="fas fa-plus"></i> New drafting matter
            </Button>
          </Link>
        </div>

        <Suspense fallback={<DashboardSkeleton />}>
          <DashboardContent token={token} />
        </Suspense>
      </div>
    </section>
  );
}
