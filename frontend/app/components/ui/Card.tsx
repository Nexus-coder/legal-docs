import type React from "react";

type CardProps = {
  children: React.ReactNode;
  variant?: "default" | "muted" | "glass";
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
};

export function Card({
  children,
  variant = "default",
  className = "",
  padding = "md",
}: CardProps) {
  const variants = {
    default: "bg-white/88 border-border-card shadow-premium",
    muted: "bg-slate-50/86 border-border-card",
    glass: "bg-white/90 backdrop-blur-md border-white/20",
  };

  const paddings = {
    none: "",
    sm: "p-3",
    md: "p-5",
    lg: "p-8",
  };

  return (
    <div
      className={`border rounded-lg ${variants[variant]} ${paddings[padding]} ${className}`}
    >
      {children}
    </div>
  );
}

export function CardLabel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={`text-[10px] font-extrabold uppercase tracking-widest text-muted font-mono ${className}`}>
      {children}
    </p>
  );
}
