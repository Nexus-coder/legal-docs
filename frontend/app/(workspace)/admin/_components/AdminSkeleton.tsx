import React from "react";

export function AdminSkeleton() {
  return (
    <div className="animate-pulse space-y-5">
      {/* 4 Metric Tiles Grid */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="ld-card p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="h-3.5 w-28 rounded-md bg-slate-200" />
              <div className="h-9 w-9 rounded-md bg-slate-200" />
            </div>
            <div className="mt-4 h-8 w-16 rounded-md bg-slate-200" />
          </div>
        ))}
      </div>

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        {/* Left Column: Console Main Panel */}
        <div className="space-y-5">
          <div className="ld-card overflow-hidden">
            {/* Run Timeline Header */}
            <div className="border-b border-slate-200 bg-white px-5 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-2">
                  <div className="h-3 w-20 rounded-md bg-slate-200" />
                  <div className="h-5 w-44 rounded-md bg-slate-200" />
                </div>
                <div className="h-6 w-20 rounded-full bg-slate-200" />
              </div>
            </div>

            {/* Five Pipeline Steps */}
            <div className="grid grid-cols-1 border-b border-slate-200 bg-slate-50 sm:grid-cols-5">
              {[
                { label: "Discover", icon: "fa-magnifying-glass" },
                { label: "Fetch", icon: "fa-cloud-arrow-down" },
                { label: "Filter", icon: "fa-filter" },
                { label: "Index", icon: "fa-database" },
                { label: "Verify", icon: "fa-circle-check" },
              ].map((step, idx) => (
                <div
                  key={idx}
                  className="min-h-24 border-slate-200 p-4 sm:border-r sm:last:border-r-0"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="h-3 w-12 rounded bg-slate-200" />
                    <i className={`fas ${step.icon} text-slate-200`} aria-hidden="true" />
                  </div>
                  <div className="mt-4 h-4 w-16 rounded bg-slate-200" />
                </div>
              ))}
            </div>

            {/* Five Counters */}
            <div className="grid grid-cols-2 gap-0 border-b border-slate-200 bg-white md:grid-cols-5">
              {["Discovered", "Fetched", "Indexed", "Skipped", "Failed"].map((_, idx) => (
                <div key={idx} className="border-r border-slate-100 p-4 last:border-r-0">
                  <div className="h-3 w-16 rounded bg-slate-200" />
                  <div className="mt-3 h-7 w-10 rounded bg-slate-200" />
                </div>
              ))}
            </div>

            {/* Event Logs List */}
            <div className="divide-y divide-slate-100 bg-white p-5 space-y-4">
              {[1, 2, 3].map((row) => (
                <div key={row} className="flex gap-4 py-3 first:pt-0 last:pb-0">
                  <div className="h-8 w-8 shrink-0 rounded-md bg-slate-200" />
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="h-5 w-16 rounded-full bg-slate-200" />
                      <div className="h-3.5 w-12 rounded bg-slate-200" />
                    </div>
                    <div className="h-3.5 w-3/4 rounded bg-slate-200" />
                    <div className="h-2.5 w-1/2 rounded bg-slate-200" />
                  </div>
                  <div className="h-3 w-10 rounded bg-slate-200" />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Sidebar Panels */}
        <aside className="space-y-5">
          {/* Controls Card */}
          <div className="ld-card p-5">
            <div className="mb-4 flex items-center justify-between">
              <div className="space-y-2">
                <div className="h-3 w-16 rounded bg-slate-200" />
                <div className="h-4.5 w-28 rounded bg-slate-200" />
              </div>
              <div className="h-6 w-16 rounded-full bg-slate-200" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="h-10 rounded-md bg-slate-200" />
              <div className="h-10 rounded-md bg-slate-200" />
            </div>
          </div>

          {/* Pinecone Preflight Card */}
          <div className="ld-card p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="space-y-2">
                <div className="h-3 w-24 rounded bg-slate-200" />
                <div className="h-4.5 w-32 rounded bg-slate-200" />
              </div>
              <div className="h-6 w-16 rounded-full bg-slate-200" />
            </div>
            <div className="space-y-2">
              <div className="h-3.5 w-full rounded bg-slate-200" />
              <div className="h-3.5 w-5/6 rounded bg-slate-200" />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <div className="h-3 w-10 rounded bg-slate-200" />
                <div className="h-3.5 w-16 rounded bg-slate-200" />
              </div>
              <div className="space-y-1">
                <div className="h-3 w-10 rounded bg-slate-200" />
                <div className="h-3.5 w-16 rounded bg-slate-200" />
              </div>
            </div>
          </div>

          {/* Latest Run Card */}
          <div className="ld-card p-5">
            <div className="mb-4 flex items-center gap-2">
              <div className="h-4 w-4 rounded-full bg-slate-200" />
              <div className="h-3 w-20 rounded bg-slate-200" />
            </div>
            <div className="space-y-3.5">
              {[1, 2, 3, 4, 5].map((row) => (
                <div key={row} className="flex justify-between border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                  <div className="h-3.5 w-16 rounded bg-slate-200" />
                  <div className="h-3.5 w-12 rounded bg-slate-200" />
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
