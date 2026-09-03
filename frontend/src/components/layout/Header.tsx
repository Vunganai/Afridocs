import { NavLink, Link } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useSignOut } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { LogOut, FileText, LayoutDashboard, Files, CheckSquare, Upload } from "lucide-react";

export function Header() {
  const { profile } = useAuthStore();
  const signOut = useSignOut();

  if (!profile) return null;

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="container flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-primary">
            <FileText className="h-5 w-5 text-green-600" />
            <span>AfriDocs</span>
          </Link>

          {/* Main Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 text-sm">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`
              }
            >
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </NavLink>

            <NavLink
              to="/documents"
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`
              }
            >
              <Files className="h-4 w-4" />
              Invoices
            </NavLink>

            <NavLink
              to="/review"
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`
              }
            >
              <CheckSquare className="h-4 w-4" />
              Review Queue
            </NavLink>

            <NavLink
              to="/upload"
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`
              }
            >
              <Upload className="h-4 w-4" />
              Upload
            </NavLink>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex flex-col items-end text-right">
            <span className="text-xs font-medium text-foreground truncate max-w-[180px]">
              {profile.email}
            </span>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
              {profile.role}
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => signOut()}>
            <LogOut className="h-4 w-4 sm:mr-1.5" />
            <span className="hidden sm:inline">Sign out</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
