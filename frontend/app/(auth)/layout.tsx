import React from "react";
import AuthBrandPanel from "./_components/AuthBrandPanel";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen w-full flex overflow-hidden" style={{ fontFamily: "var(--font-inter), system-ui, sans-serif" }}>
      <AuthBrandPanel />
      <main className="flex-1 auth-gradient-bg overflow-y-auto flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-[520px] auth-form-animate">
          {children}
        </div>
      </main>
    </div>
  );
}
