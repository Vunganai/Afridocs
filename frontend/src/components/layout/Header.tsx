import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useSignOut } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { LogOut, FileText } from "lucide-react";

export function Header() {
  const { profile } = useAuthStore();
  const signOut = useSignOut();
  const navigate = useNavigate();

  if (!profile) return null;

  return (
    <header className="sticky top-0 z-40 border-b bg-background">
      <div className="container flex h-16 items-center justify-between px-4">
        <Link to="/" className="flex items-center gap-2 font-bold text-lg">
          <FileText className="h-5 w-5 text-afri-green" />
          <span>AfriDocs</span>
        </Link>

        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">{profile.email}</span>
          <span className="text-xs bg-muted px-2 py-1 rounded">{profile.role}</span>
          <Button variant="ghost" size="sm" onClick={() => signOut()}>
            <LogOut className="h-4 w-4 mr-2" />
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
