import type React from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "locked";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  children,
  className = "",
  ...props
}: ButtonProps) {
  const baseStyles = "inline-flex items-center justify-center font-bold transition-all duration-150 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variants = {
    primary: "bg-brand-blue text-white shadow-auth hover:bg-brand-blue-hover hover:shadow-auth-hover",
    secondary: "bg-white text-slate-700 border border-border hover:border-brand-blue hover:text-brand-blue-hover",
    ghost: "bg-transparent text-slate-600 hover:bg-slate-100",
    danger: "bg-error text-white hover:bg-error/90",
    locked: "bg-border text-muted cursor-not-allowed active:scale-100",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-xs rounded-md gap-1.5",
    md: "px-4 py-2 text-sm rounded-lg gap-2",
    lg: "px-6 py-3.5 text-base rounded-xl gap-2.5",
  };

  const currentVariant = variant === "locked" || props.disabled ? variants.locked : variants[variant];

  return (
    <button
      className={`${baseStyles} ${currentVariant} ${sizes[size]} ${className}`}
      {...props}
      disabled={props.disabled || loading || variant === "locked"}
    >
      {loading ? (
        <div className="w-4 h-4 border-2 border-current/40 border-t-current rounded-full animate-spin" />
      ) : null}
      {children}
    </button>
  );
}
