"use client";

import React, { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";
import {
  AuthAlert,
  AuthCopyright,
  AuthDivider,
  AuthFooterLink,
  AuthForm,
  AuthFormFrame,
  AuthHeader,
  AuthInlineLink,
  AuthSubmitButton,
  AuthTextField,
} from "../_components/AuthFormComponents";

function LoginForm() {
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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthFormFrame>
      <AuthHeader title="Welcome back!" subtitle="Sign in to your account." />
      {signupSuccess && <AuthAlert tone="success">Account created successfully. You can now log in.</AuthAlert>}
      {error && <AuthAlert tone="error">{error}</AuthAlert>}

      <AuthForm onSubmit={handleSubmit}>
        <AuthTextField label="Email address" name="email" type="email" placeholder="you@example.com" onChange={handleChange} />
        <AuthTextField
          label="Password"
          name="password"
          type="password"
          placeholder="Enter your password"
          onChange={handleChange}
          extra={<AuthInlineLink href="#">Forgot password?</AuthInlineLink>}
        />
        <AuthSubmitButton loading={loading}>Log In</AuthSubmitButton>
      </AuthForm>

      <AuthDivider />
      <AuthFooterLink text="Don't have an account?" href="/signup" linkText="Sign up" />
      <AuthCopyright />
    </AuthFormFrame>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="text-slate-500">Loading...</div>}>
      <LoginForm />
    </Suspense>
  );
}
