import React from "react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen w-full flex overflow-hidden" style={{ fontFamily: "var(--font-inter), system-ui, sans-serif" }}>

      {/* ── Left Sidebar ─────────────────────────────────────── */}
      <aside
        className="hidden lg:flex lg:w-[42%] xl:w-[40%] flex-col justify-between relative overflow-hidden flex-shrink-0"
        style={{ background: "#0b1120" }}
      >
        {/* Dot-grid texture */}
        <div className="sidebar-dots absolute inset-0 pointer-events-none" />
        {/* Coloured glow blobs */}
        <div className="sidebar-glow absolute inset-0 pointer-events-none" />

        {/* Top — Logo + Hero text */}
        <div className="relative z-10 px-12 pt-14">
          {/* Logo */}
          <div className="flex items-center gap-3.5 mb-20">
            <div
              className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: "linear-gradient(135deg,#2563eb,#4f46e5)" }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <span className="text-white font-bold text-[1.1rem] tracking-tight">
              The Sovereign Archive
            </span>
          </div>

          {/* Hero */}
          <h1 className="text-white font-black leading-[1.08] tracking-tight mb-7" style={{ fontSize: "clamp(2.4rem, 3.5vw, 3.2rem)" }}>
            Manage your<br />
            <span style={{ background: "linear-gradient(90deg,#60a5fa,#a5b4fc)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              legal documents
            </span><br />
            with ease.
          </h1>

          <p className="text-slate-400 font-medium leading-relaxed max-w-xs" style={{ fontSize: "1.0625rem" }}>
            LegalDocs helps advocates and legal teams draft, review, and
            organise case documents — all in one place.
          </p>
        </div>

        {/* Bottom — Testimonial */}
        <div className="relative z-10 px-12 pb-14">
          {/* Thin divider */}
          <div className="h-px mb-8" style={{ background: "rgba(255,255,255,0.08)" }} />

          <div
            className="p-7 rounded-2xl"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.09)",
              backdropFilter: "blur(12px)",
            }}
          >
            {/* Quote mark */}
            <svg className="h-7 w-7 mb-4 opacity-40" style={{ color: "#60a5fa" }} fill="currentColor" viewBox="0 0 24 24">
              <path d="M9.983 3v7.391c0 5.704-3.731 9.57-8.983 10.609l-.995-2.151c2.432-.917 3.995-3.638 3.995-5.849h-4v-10h9.983zm14.017 0v7.391c0 5.704-3.748 9.571-9 10.609l-.996-2.151c2.433-.917 3.996-3.638 3.996-5.849h-3.983v-10h9.983z" />
            </svg>
            <p className="text-slate-200 italic leading-relaxed mb-6" style={{ fontSize: "0.9375rem" }}>
              "LegalDocs has completely changed how we manage case files. It saves
              our team hours every week."
            </p>
            <div className="flex items-center gap-4">
              <div
                className="w-11 h-11 rounded-xl flex-shrink-0"
                style={{ background: "linear-gradient(135deg,#1e3a5f,#2d4a7a)" }}
              />
              <div>
                <p className="text-white font-bold text-sm">Marcus Sterling, Esq.</p>
                <p className="font-bold uppercase tracking-widest" style={{ fontSize: "0.65rem", color: "#60a5fa" }}>
                  Senior Partner, Sterling & Associates
                </p>
              </div>
            </div>
          </div>

          {/* Bottom badges */}
          <div className="flex items-center gap-5 mt-8">
            {["Secure", "Private", "Reliable"].map((label) => (
              <span key={label} className="flex items-center gap-1.5 font-bold uppercase tracking-widest" style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.25)" }}>
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500/50" />
                {label}
              </span>
            ))}
          </div>
        </div>
      </aside>

      {/* ── Right Form Panel ─────────────────────────────────── */}
      <main className="flex-1 auth-gradient-bg overflow-y-auto flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-[520px] auth-form-animate">
          {children}
        </div>
      </main>
    </div>
  );
}
