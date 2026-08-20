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
  const { profile, isLoading } = useAuthStore();
  const { toast } = useToast();
  const [step, setStep] = useState<"auth" | "onboard">("auth");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    tenantName: "",
    tenantSlug: "",
    fullName: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoading && profile) {
      navigate("/");
    }
  }, [profile, isLoading, navigate]);

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
      setStep("onboard");
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
      await apiClient.post("/v1/auth/onboard", {
        tenant_name: formData.tenantName,
        tenant_slug: formData.tenantSlug,
        contact_email: formData.email,
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

  if (isLoading) return <div className="flex items-center justify-center min-h-screen">Loading...</div>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-afri-green-light to-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-2 text-center">
          <CardTitle className="text-2xl">Create account</CardTitle>
          <CardDescription>
            {step === "auth" ? "Get started with AfriDocs" : "Set up your organization"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && <div className="p-3 mb-4 bg-destructive/10 text-destructive text-sm rounded">{error}</div>}

          {step === "auth" ? (
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
          ) : (
            <form onSubmit={handleOnboard} className="space-y-3">
              <input
                type="text"
                placeholder="Organization name"
                value={formData.tenantName}
                onChange={(e) => setFormData({ ...formData, tenantName: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm"
                required
              />
              <input
                type="text"
                placeholder="Organization slug (e.g. acme-corp)"
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
            <button onClick={() => navigate("/login")} className="text-afri-green hover:underline font-medium">
              Sign in
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
