import React from "react";
import { Card, CardLabel } from "@/app/components/ui/Card";

export function DashboardSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      {/* Three Cards Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Citations Card Skeleton */}
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <div className="h-3.5 w-28 rounded-md bg-slate-200" />
            <div className="h-6 w-20 rounded-full bg-slate-200" />
          </div>
          <div className="flex items-end gap-2">
            <div className="h-10 w-12 rounded-md bg-slate-200" />
            <div className="h-4.5 w-10 rounded-md bg-slate-200" />
          </div>
          <div className="mt-5 h-2 rounded-full bg-slate-100" />
        </Card>

        {/* Recent Matches Card Skeleton */}
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <div className="h-3.5 w-36 rounded-md bg-slate-200" />
            <div className="h-8 w-8 rounded-md bg-slate-200" />
          </div>
          <div className="h-10 w-16 rounded-md bg-slate-200" />
          <div className="mt-3 h-4 w-full rounded bg-slate-200" />
        </Card>

        {/* Draft Status Card Skeleton */}
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <div className="h-3.5 w-24 rounded-md bg-slate-200" />
            <div className="h-8 w-8 rounded-md bg-slate-200" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} variant="muted" padding="sm" className="text-center">
                <div className="mx-auto h-7 w-8 rounded bg-slate-200" />
                <div className="mx-auto mt-2 h-2.5 w-10 rounded bg-slate-200" />
              </Card>
            ))}
          </div>
        </Card>
      </div>

      {/* Table Shell Skeleton */}
      <div className="ld-table-shell">
        {/* Table Title and Search */}
        <div className="flex items-center justify-between border-b border-border bg-white px-5 py-4">
          <div className="space-y-2">
            <div className="h-3.5 w-24 rounded bg-slate-200" />
            <div className="h-3.5 w-72 rounded bg-slate-200" />
          </div>
          <div className="h-8 w-44 rounded-md bg-slate-200" />
        </div>
        {/* Table Skeleton Rows */}
        <div className="divide-y divide-slate-100 bg-white">
          {[1, 2, 3, 4, 5].map((row) => (
            <div key={row} className="grid grid-cols-[1.5fr_1fr_1.2fr_1fr_0.8fr] gap-4 px-6 py-5 items-center">
              <div className="space-y-2">
                <div className="h-4.5 w-32 rounded bg-slate-200" />
                <div className="h-3 w-20 rounded bg-slate-200" />
              </div>
              <div>
                <div className="h-6 w-24 rounded-full bg-slate-200" />
              </div>
              <div className="space-y-2">
                <div className="h-3 w-16 rounded bg-slate-200" />
                <div className="h-1.5 w-24 rounded-full bg-slate-200" />
              </div>
              <div>
                <div className="h-3.5 w-24 rounded bg-slate-200" />
              </div>
              <div className="text-right">
                <div className="ml-auto h-4.5 w-16 rounded bg-slate-200" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
