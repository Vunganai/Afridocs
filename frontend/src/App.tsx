import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthInit } from "@/hooks/useAuth";
import { useAuthStore } from "@/stores/authStore";
import { AppLayout } from "@/components/layout/AppLayout";
import { Toaster } from "@/components/ui/toaster";
import { LoginPage } from "@/pages/auth/Login";
import { RegisterPage } from "@/pages/auth/Register";
import { DashboardPage } from "@/pages/dashboard/Dashboard";
import { UploadPage } from "@/pages/documents/Upload";
import { DocumentListPage } from "@/pages/documents/List";
import { DocumentDetailPage } from "@/pages/documents/Detail";
import { ReviewQueuePage } from "@/pages/review/ReviewQueue";
import { ReviewDetailPage } from "@/pages/review/ReviewDetail";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5_000 },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { profile, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return profile ? <>{children}</> : <Navigate to="/login" replace />;
}

function AppRoutes() {
  // Initialise Supabase auth listener once, at the top of the tree
  useAuthInit();

  return (
    <Routes>
      {/* ── Public ─────────────────────────────────────────── */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* ── Protected (wrapped in AppLayout) ────────────────── */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/documents" element={<DocumentListPage />} />
        <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
        <Route path="/review" element={<ReviewQueuePage />} />
        <Route path="/review/:documentId" element={<ReviewDetailPage />} />
      </Route>

      {/* ── Fallback ─────────────────────────────────────────── */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
