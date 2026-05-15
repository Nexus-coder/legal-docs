"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const signupSuccess = searchParams.get("signup") === "success";

  const [formData, setFormData] = useState({ email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setFormData((p) => ({ ...p, [e.target.name]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const body = new URLSearchParams();
      body.append("username", formData.email);
      body.append("password", formData.password);

      const res = await fetch(`${API_BASE_URL}auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });

      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || "Login failed");
      }

      const data = await res.json();
      document.cookie = `token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`;
      router.push("/");
    } catch (err: any) {
      setError(err.message);
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
          Welcome back!
        </h2>
        <p className="text-slate-500 font-medium" style={{ fontSize: "1rem" }}>
          Sign in to your account.
        </p>
      </div>

      {/* Success */}
      {signupSuccess && (
        <div
          className="mb-6 px-4 py-3.5 rounded-xl flex items-start gap-3 text-sm font-medium"
          style={{ background: "#f0fdf4", border: "1.5px solid #bbf7d0", color: "#16a34a" }}
        >
          <svg className="h-5 w-5 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Account created successfully. You can now log in.
        </div>
      )}

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
        {/* Email */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="email"
            className="font-bold uppercase tracking-widest text-slate-400"
            style={{ fontSize: "0.675rem", letterSpacing: "0.13em" }}
          >
            Email address
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            placeholder="you@example.com"
            autoComplete="email"
            onChange={handleChange}
            className="auth-input w-full px-4 py-3.5 rounded-xl border text-slate-900 placeholder-slate-400 outline-none text-[0.9375rem]"
            style={{ background: "#f1f5fb", border: "1.5px solid #e2e8f0", fontFamily: "inherit" }}
          />
        </div>

        {/* Password */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label
              htmlFor="password"
              className="font-bold uppercase tracking-widest text-slate-400"
              style={{ fontSize: "0.675rem", letterSpacing: "0.13em" }}
            >
              Password
            </label>
            <Link
              href="#"
              className="font-bold uppercase tracking-widest text-blue-600 hover:underline underline-offset-2"
              style={{ fontSize: "0.675rem" }}
            >
              Forgot password?
            </Link>
          </div>
          <input
            id="password"
            name="password"
            type="password"
            required
            placeholder="Enter your password"
            autoComplete="current-password"
            onChange={handleChange}
            className="auth-input w-full px-4 py-3.5 rounded-xl border text-slate-900 placeholder-slate-400 outline-none text-[0.9375rem]"
            style={{ background: "#f1f5fb", border: "1.5px solid #e2e8f0", fontFamily: "inherit" }}
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="auth-btn mt-2 w-full text-white font-extrabold rounded-xl py-4 flex items-center justify-center gap-2 disabled:opacity-50"
          style={{ fontSize: "0.8125rem", letterSpacing: "0.1em" }}
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          ) : (
            <>Log In</>
          )}
        </button>
      </form>

      {/* Divider with "or" */}
      <div className="flex items-center gap-4 my-8">
        <div className="flex-1 h-px" style={{ background: "#e8eef7" }} />
        <span className="font-semibold text-slate-400 text-xs">or</span>
        <div className="flex-1 h-px" style={{ background: "#e8eef7" }} />
      </div>

      {/* Sign-up prompt */}
      <p className="text-center text-slate-500 font-medium" style={{ fontSize: "0.9rem" }}>
        Don't have an account?{" "}
        <Link href="/signup" className="text-blue-600 font-bold hover:underline underline-offset-2">
          Sign up
        </Link>
      </p>

      {/* Copyright */}
      <p className="text-center mt-14 font-bold uppercase tracking-widest" style={{ fontSize: "0.6rem", color: "#c9d4e8" }}>
        © 2024 LegalDocs · All rights reserved
      </p>
    </div>
  );
}
