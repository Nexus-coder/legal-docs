import Link from "next/link";
import type React from "react";

type AuthHeaderProps = {
  title: string;
  subtitle: string;
};

type AuthAlertProps = {
  tone: "success" | "error";
  children: React.ReactNode;
};

type AuthTextFieldProps = {
  label: string;
  name: string;
  type?: string;
  placeholder: string;
  required?: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  extra?: React.ReactNode;
};

type AuthSubmitButtonProps = {
  loading: boolean;
  children: React.ReactNode;
};

type AuthFooterLinkProps = {
  text: string;
  href: string;
  linkText: string;
};

type AuthFormProps = {
  onSubmit: (e: React.FormEvent) => void;
  children: React.ReactNode;
};

export function AuthFormFrame({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontFamily: "var(--font-inter), system-ui, sans-serif" }}>
      {children}
    </div>
  );
}

export function AuthHeader({ title, subtitle }: AuthHeaderProps) {
  return (
    <div className="mb-10">
      <p className="font-bold uppercase tracking-widest text-blue-600 mb-3" style={{ fontSize: "0.7rem" }}>
        LegalDocs
      </p>
      <h2
        className="font-black text-slate-900 leading-tight tracking-tight mb-2"
        style={{ fontSize: "clamp(1.9rem, 3vw, 2.4rem)" }}
      >
        {title}
      </h2>
      <p className="text-slate-500 font-medium" style={{ fontSize: "1rem" }}>
        {subtitle}
      </p>
    </div>
  );
}

export function AuthAlert({ tone, children }: AuthAlertProps) {
  const styles =
    tone === "success"
      ? { background: "#f0fdf4", border: "1.5px solid #bbf7d0", color: "#16a34a" }
      : { background: "#fef2f2", border: "1.5px solid #fecaca", color: "#dc2626" };

  return (
    <div className="mb-6 px-4 py-3.5 rounded-xl flex items-start gap-3 text-sm font-medium" style={styles}>
      <svg className="h-5 w-5 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        {tone === "success" ? (
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        )}
      </svg>
      {children}
    </div>
  );
}

export function AuthTextField({
  label,
  name,
  type = "text",
  placeholder,
  required = true,
  onChange,
  extra,
}: AuthTextFieldProps) {
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
        style={{ background: "#f1f5fb", border: "1.5px solid #e2e8f0", fontFamily: "inherit" }}
      />
    </div>
  );
}

export function AuthForm({ onSubmit, children }: AuthFormProps) {
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5">
      {children}
    </form>
  );
}

export function AuthFieldGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-4">{children}</div>;
}

export function AuthInlineLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="font-bold uppercase tracking-widest text-blue-600 hover:underline underline-offset-2"
      style={{ fontSize: "0.675rem" }}
    >
      {children}
    </Link>
  );
}

export function AuthSubmitButton({ loading, children }: AuthSubmitButtonProps) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="auth-btn mt-1 w-full text-white font-extrabold rounded-xl py-4 flex items-center justify-center gap-2 disabled:opacity-50"
      style={{ fontSize: "0.8125rem", letterSpacing: "0.1em" }}
    >
      {loading ? <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : children}
    </button>
  );
}

export function AuthDivider() {
  return (
    <div className="flex items-center gap-4 my-8">
      <div className="flex-1 h-px" style={{ background: "#e8eef7" }} />
      <span className="font-semibold text-slate-400 text-xs">or</span>
      <div className="flex-1 h-px" style={{ background: "#e8eef7" }} />
    </div>
  );
}

export function AuthFooterLink({ text, href, linkText }: AuthFooterLinkProps) {
  return (
    <p className="text-center mt-8 text-slate-500 font-medium" style={{ fontSize: "0.9rem" }}>
      {text}{" "}
      <Link href={href} className="text-blue-600 font-bold hover:underline underline-offset-2">
        {linkText}
      </Link>
    </p>
  );
}

export function AuthCopyright() {
  return (
    <p className="text-center mt-14 font-bold uppercase tracking-widest" style={{ fontSize: "0.6rem", color: "#c9d4e8" }}>
      &copy; 2024 LegalDocs &middot; All rights reserved
    </p>
  );
}
