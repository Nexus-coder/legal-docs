import type React from "react";

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
  extra?: React.ReactNode;
};

export function Input({
  label,
  error,
  extra,
  className = "",
  id,
  ...props
}: InputProps) {
  const inputId = id || props.name;

  return (
    <div className="flex flex-col gap-2 w-full">
      {(label || extra) && (
        <div className="flex items-center justify-between">
          {label && (
            <label
              htmlFor={inputId}
              className="text-[0.675rem] font-bold uppercase tracking-[0.13em] text-muted-foreground"
            >
              {label}
            </label>
          )}
          {extra}
        </div>
      )}
      <input
        id={inputId}
        className={`
          w-full px-4 py-3.5 rounded-xl border-1.5 transition-all duration-200 outline-none text-[0.9375rem] font-sans
          bg-[#f1f5fb] border-border text-slate-900 placeholder-muted-foreground
          focus:bg-white focus:border-brand-blue focus:ring-4 focus:ring-brand-blue/10
          disabled:opacity-50 disabled:cursor-not-allowed
          ${error ? "border-error bg-error-bg/30" : ""}
          ${className}
        `}
        {...props}
      />
      {error && <p className="text-xs font-semibold text-error mt-1">{error}</p>}
    </div>
  );
}
