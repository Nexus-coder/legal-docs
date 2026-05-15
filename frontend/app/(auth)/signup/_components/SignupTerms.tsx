import Link from "next/link";

export default function SignupTerms() {
  return (
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
  );
}
