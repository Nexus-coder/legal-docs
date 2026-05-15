import type React from "react";
import Sidebar from "./Sidebar";

export default function WorkspaceShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      <Sidebar />
      <main className="min-w-0 flex-1 flex flex-col overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
