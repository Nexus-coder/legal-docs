"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";
import {
  AuthAlert,
  AuthCopyright,
  AuthFieldGrid,
  AuthFooterLink,
  AuthForm,
  AuthFormFrame,
  AuthHeader,
  AuthSubmitButton,
  AuthTextField,
} from "../_components/AuthFormComponents";
import SignupTerms from "./_components/SignupTerms";

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
    <AuthFormFrame>
      <AuthHeader title="Create your account" subtitle="Sign up free and get started in minutes." />
      {error && <AuthAlert tone="error">{error}</AuthAlert>}

      <AuthForm onSubmit={handleSubmit}>
        <AuthFieldGrid>
          <AuthTextField label="Full Name" name="fullName" placeholder="John Doe, Esq." onChange={handleChange} />
          <AuthTextField label="Firm Name" name="firmName" placeholder="Global Legal Partners" onChange={handleChange} />
        </AuthFieldGrid>

        <AuthTextField label="Email address" name="email" type="email" placeholder="you@example.com" onChange={handleChange} />
        <AuthTextField label="Password" name="password" type="password" placeholder="Min. 8 characters" onChange={handleChange} />
        <SignupTerms />
        <AuthSubmitButton loading={loading}>Sign Up</AuthSubmitButton>
      </AuthForm>

      <AuthFooterLink text="Already have an account?" href="/login" linkText="Log in" />
      <AuthCopyright />
    </AuthFormFrame>
  );
}
