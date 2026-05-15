"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";

/* ─── reusable input ─────────────────────────────────── */
function Field({
  label,
  name,
  type = "text",
  placeholder,
  required = true,
  onChange,
  extra,
}: {
  label: string;
  name: string;
  type?: string;
  placeholder: string;
  required?: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  extra?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label
          htmlFor={name}
          className="font-bold uppercase tracking-widest text-slate-400"
          style={{ fontSize: "0.675rem", letterSpacing: "0.13em" }}
        >
          {label}
        </label>
        {extra}
      </div>
      <input
        id={name}
        name={name}
        type={type}
        placeholder={placeholder}
        required={required}
        autoComplete={type === "password" ? "current-password" : type === "email" ? "email" : "off"}
        onChange={onChange}
        className="auth-input w-full px-4 py-3.5 rounded-xl border text-slate-900 placeholder-slate-400 outline-none text-[0.9375rem]"
        style={{
          background: "#f1f5fb",
          border: "1.5px solid #e2e8f0",
          fontFamily: "inherit",
        }}
      />
    </div>
  );
}

/* ─── main component ─────────────────────────────────── */
export default function SignupPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    fullName: "",
    firmName: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setFormData((p) => ({ ...p, [e.target.name]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          full_name: formData.fullName,
          firm_name: formData.firmName,
        }),
      });

      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || "Signup failed");
      }

      router.push("/login?signup=success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: "var(--font-inter), system-ui, sans-serif" }}>
      {/* Header */}
      <div className="mb-10">
        <p className="font-bold uppercase tracking-widest text-blue-600 mb-3" style={{ fontSize: "0.7rem" }}>
          LegalDocs
        </p>
        <h2
          className="font-black text-slate-900 leading-tight tracking-tight mb-2"
          style={{ fontSize: "clamp(1.9rem, 3vw, 2.4rem)" }}
        >
          Create your account
        </h2>
        <p className="text-slate-500 font-medium" style={{ fontSize: "1rem" }}>
          Sign up free and get started in minutes.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div
          className="mb-6 px-4 py-3.5 rounded-xl flex items-start gap-3 text-sm font-medium"
          style={{ background: "#fef2f2", border: "1.5px solid #fecaca", color: "#dc2626" }}
        >
          <svg className="h-5 w-5 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {/* Row: Full Name + Firm Name */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Full Name" name="fullName" placeholder="John Doe, Esq." onChange={handleChange} />
          <Field label="Firm Name" name="firmName" placeholder="Global Legal Partners" onChange={handleChange} />
        </div>

        <Field label="Email address" name="email" type="email" placeholder="you@example.com" onChange={handleChange} />
        <Field label="Password" name="password" type="password" placeholder="Min. 8 characters" onChange={handleChange} />

        {/* Terms */}
        <label className="flex items-start gap-3 cursor-pointer group">
          <div className="relative flex items-center mt-0.5">
            <input
              type="checkbox"
              required
              className="peer h-5 w-5 cursor-pointer appearance-none rounded-md transition-all"
              style={{ border: "2px solid #cbd5e1", background: "#f1f5fb" }}
            />
            <span
              className="absolute inset-0 rounded-md opacity-0 peer-checked:opacity-100 transition-opacity flex items-center justify-center"
              style={{ background: "linear-gradient(135deg,#2563eb,#4f46e5)" }}
            >
              <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3.5}>
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
          </div>
          <span className="text-slate-500 font-medium leading-snug" style={{ fontSize: "0.875rem" }}>
            I agree to the{" "}
            <Link href="#" className="text-blue-600 font-bold hover:underline underline-offset-2">Terms of Service</Link>{" "}
            and{" "}
            <Link href="#" className="text-blue-600 font-bold hover:underline underline-offset-2">Privacy Policy</Link>.
          </span>
        </label>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="auth-btn mt-1 w-full text-white font-extrabold rounded-xl py-4 flex items-center justify-center gap-2 disabled:opacity-50"
          style={{ fontSize: "0.8125rem", letterSpacing: "0.1em" }}
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          ) : (
            <>Sign Up</>
          )}
        </button>
      </form>

      {/* Footer link */}
      <p className="text-center mt-8 text-slate-500 font-medium" style={{ fontSize: "0.9rem" }}>
        Already have an account?{" "}
        <Link href="/login" className="text-blue-600 font-bold hover:underline underline-offset-2">
          Log in
        </Link>
      </p>

      {/* Copyright */}
      <p className="text-center mt-14 font-bold uppercase tracking-widest" style={{ fontSize: "0.6rem", color: "#c9d4e8" }}>
        © 2024 LegalDocs · All rights reserved
      </p>
    </div>
  );
}
