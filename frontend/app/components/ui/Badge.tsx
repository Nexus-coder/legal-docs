import type React from "react";

type BadgeVariant = "blue" | "green" | "amber" | "slate" | "red";

type BadgeProps = {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  icon?: string;
};

export function Badge({
  children,
  variant = "slate",
  className = "",
  icon,
}: BadgeProps) {
  const variants = {
    blue: "text-brand-blue-hover bg-blue-100/80",
    green: "text-success bg-success-bg",
    amber: "text-warning bg-warning-bg",
    slate: "text-slate-600 bg-slate-100",
    red: "text-error bg-error-bg",
  };

  return (
    <span
      className={`inline-flex items-center justify-center min-h-[22px] px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold uppercase whitespace-nowrap gap-1.5 ${variants[variant]} ${className}`}
    >
      {icon && <i className={`${icon} text-[1.1em]`}></i>}
      {children}
    </span>
  );
}
