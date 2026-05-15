import Sidebar from "../components/Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      <Sidebar />
      <main className="min-w-0 flex-1 flex flex-col overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
