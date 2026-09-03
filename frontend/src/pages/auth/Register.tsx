import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { supabase } from "@/lib/supabase";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/useToast";

export function RegisterPage() {
  const navigate = useNavigate();
  const { profile, isLoading, supabaseUser } = useAuthStore();
  const { toast } = useToast();

  // step: "auth"    → sign up form
  //       "verify"  → waiting for email confirmation
  //       "onboard" → org details form (user confirmed, no backend profile yet)
  const [step, setStep] = useState<"auth" | "verify" | "onboard">("auth");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    tenantName: "",
    tenantSlug: "",
    fullName: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // If already fully onboarded, go to dashboard
  useEffect(() => {
    if (!isLoading && profile) {
      navigate("/");
    }
  }, [profile, isLoading, navigate]);

  // If Supabase session exists but no backend profile yet, jump to onboarding
  // This handles the case where the user confirmed their email and came back
  useEffect(() => {
    if (!isLoading && supabaseUser && !profile) {
      setStep("onboard");
    }
  }, [isLoading, supabaseUser, profile]);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { error: signUpError } = await supabase.auth.signUp({
        email: formData.email,
        password: formData.password,
      });
      if (signUpError) throw signUpError;
      // Show verify step — user must confirm email before onboarding
      setStep("verify");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleOnboard = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // Ensure we have a fresh valid session before calling the backend
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        const { error: refreshError } = await supabase.auth.refreshSession();
        if (refreshError) throw new Error("Your session expired. Please sign in again.");
      }

      await apiClient.post("/v1/auth/onboard", {
        tenant_name: formData.tenantName,
        tenant_slug: formData.tenantSlug,
        contact_email: formData.email || supabaseUser?.email,
        full_name: formData.fullName || undefined,
        country_code: "ZA",
        default_currency: "ZAR",
      });
      toast({ title: "Welcome!", description: "Your account is ready." });
      navigate("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-afri-green-light to-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-2 text-center">
          <CardTitle className="text-2xl">
            {step === "auth" && "Create account"}
            {step === "verify" && "Check your email"}
            {step === "onboard" && "Set up your organisation"}
          </CardTitle>
          <CardDescription>
            {step === "auth" && "Get started with AfriDocs"}
            {step === "verify" && "We sent a confirmation link to your inbox"}
            {step === "onboard" && "Almost there — tell us about your organisation"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="p-3 mb-4 bg-destructive/10 text-destructive text-sm rounded">
              {error}
            </div>
          )}

          {step === "auth" && (
            <form onSubmit={handleSignUp} className="space-y-3">
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm"
                required
              />
              <input
                type="password"
                placeholder="Password (min 6 chars)"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm"
                minLength={6}
                required
              />
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Creating account..." : "Continue"}
              </Button>
            </form>
          )}

          {step === "verify" && (
            <div className="text-center space-y-4">
              <p className="text-sm text-muted-foreground">
                Click the confirmation link in your email. Once confirmed, come back
                to this page — it will automatically advance to the next step.
              </p>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => navigate("/login")}
              >
                Sign in instead
              </Button>
            </div>
          )}

          {step === "onboard" && (
            <form onSubmit={handleOnboard} className="space-y-3">
              <input
                type="text"
                placeholder="Organisation name"
                value={formData.tenantName}
                onChange={(e) => setFormData({ ...formData, tenantName: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm"
                required
              />
              <input
                type="text"
                placeholder="Organisation slug (e.g. acme-corp)"
                value={formData.tenantSlug}
                onChange={(e) => setFormData({ ...formData, tenantSlug: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm"
                pattern="^[a-z0-9\-]+$"
                title="Lowercase letters, numbers, and hyphens only"
                required
              />
              <input
                type="text"
                placeholder="Your full name (optional)"
                value={formData.fullName}
                onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm"
              />
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Setting up..." : "Create organisation"}
              </Button>
            </form>
          )}

          <p className="text-xs text-center text-muted-foreground mt-4">
            Already have an account?{" "}
            <button
              onClick={() => navigate("/login")}
              className="text-afri-green hover:underline font-medium"
            >
              Sign in
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
