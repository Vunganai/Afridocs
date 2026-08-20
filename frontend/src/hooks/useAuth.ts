import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { apiClient } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import type { UserProfile } from "@/types";

export function useAuthInit() {
  const { setSession, setProfile, setLoading, clear } = useAuthStore();

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session, session?.user ?? null);
      if (session) {
        fetchProfile().finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    });

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        setSession(session, session?.user ?? null);
        if (session) {
          await fetchProfile();
        } else {
          clear();
        }
        setLoading(false);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  async function fetchProfile() {
    try {
      const { data } = await apiClient.get<UserProfile>("/v1/auth/me");
      setProfile(data);
    } catch {
      // Profile not found — user needs to complete onboarding
      setProfile(null);
    }
  }
}

export function useSignOut() {
  const navigate = useNavigate();
  const { clear } = useAuthStore();

  return async () => {
    await supabase.auth.signOut();
    clear();
    navigate("/login");
  };
}
