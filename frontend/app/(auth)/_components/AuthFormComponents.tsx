import Link from "next/link";
import type React from "react";
import { Button } from "@/app/components/ui/Button";
import { Input } from "@/app/components/ui/Input";

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
    <div className="font-sans antialiased">
      {children}
    </div>
  );
}

export function AuthHeader({ title, subtitle }: AuthHeaderProps) {
  return (
    <div className="mb-10">
      <p className="text-[0.7rem] font-bold uppercase tracking-widest text-brand-blue mb-3">
        LegalDocs
      </p>
      <h2 className="text-4xl lg:text-5xl font-black text-slate-900 leading-tight tracking-tight mb-2">
        {title}
      </h2>
      <p className="text-base text-slate-500 font-medium">
        {subtitle}
      </p>
    </div>
  );
}

export function AuthAlert({ tone, children }: AuthAlertProps) {
  const toneStyles = {
    success: "bg-success-bg border-success-border text-success",
    error: "bg-error-bg border-error-border text-error",
  };

  return (
    <div className={`mb-6 px-4 py-3.5 rounded-xl border-1.5 flex items-start gap-3 text-sm font-medium ${toneStyles[tone]}`}>
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
    <Input
      label={label}
      name={name}
      type={type}
      placeholder={placeholder}
      required={required}
      onChange={onChange}
      extra={extra}
      autoComplete={type === "password" ? "current-password" : type === "email" ? "email" : "off"}
    />
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
  return <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{children}</div>;
}

export function AuthInlineLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="text-[0.675rem] font-bold uppercase tracking-widest text-brand-blue hover:underline underline-offset-2"
    >
      {children}
    </Link>
  );
}

export function AuthSubmitButton({ loading, children }: AuthSubmitButtonProps) {
  return (
    <Button
      type="submit"
      loading={loading}
      size="lg"
      className="mt-1 w-full text-[0.8125rem] tracking-[0.1em] uppercase font-extrabold"
    >
      {children}
    </Button>
  );
}

export function AuthDivider() {
  return (
    <div className="flex items-center gap-4 my-8">
      <div className="flex-1 h-px bg-[#e8eef7]" />
      <span className="font-semibold text-slate-400 text-xs">or</span>
      <div className="flex-1 h-px bg-[#e8eef7]" />
    </div>
  );
}

export function AuthFooterLink({ text, href, linkText }: AuthFooterLinkProps) {
  return (
    <p className="text-center mt-8 text-sm text-slate-500 font-medium">
      {text}{" "}
      <Link href={href} className="text-brand-blue font-bold hover:underline underline-offset-2">
        {linkText}
      </Link>
    </p>
  );
}

export function AuthCopyright() {
  return (
    <p className="text-center mt-14 font-bold uppercase tracking-widest text-[0.6rem] text-[#c9d4e8]">
      &copy; {new Date().getFullYear()} LegalDocs &middot; All rights reserved
    </p>
  );
}
