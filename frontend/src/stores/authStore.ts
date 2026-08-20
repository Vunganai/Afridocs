/**
 * Zustand auth store.
 * Holds the Supabase session + our UserProfile from the backend.
 */

import type { Session, User } from "@supabase/supabase-js";
import { create } from "zustand";
import type { UserProfile } from "@/types";

interface AuthState {
  session: Session | null;
  supabaseUser: User | null;
  profile: UserProfile | null;
  isLoading: boolean;

  setSession: (session: Session | null, user: User | null) => void;
  setProfile: (profile: UserProfile | null) => void;
  setLoading: (loading: boolean) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  supabaseUser: null,
  profile: null,
  isLoading: true,

  setSession: (session, user) => set({ session, supabaseUser: user }),
  setProfile: (profile) => set({ profile }),
  setLoading: (isLoading) => set({ isLoading }),
  clear: () => set({ session: null, supabaseUser: null, profile: null }),
}));
