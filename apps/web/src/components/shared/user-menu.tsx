import { useAuth } from "@/domain/auth/hooks";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Key, LogOut, UserCircle, Users } from "lucide-react";
import Link from "next/link";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";

export function UserMenu() {
  const { user, logout } = useAuth();

  if (!user) return null;

  const displayLabel = user.displayName ?? user.email;
  const initials = user.displayName
    ? user.displayName.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user.email.slice(0, 2).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="rounded-full" data-testid="button-user-menu">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">{initials}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <div className="px-2 py-1.5">
          <p className="text-sm font-medium">{displayLabel || "User"}</p>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href={FRONTEND_ROUTES.TEAMS} className="cursor-pointer" data-testid="menu-teams">
            <Users className="mr-2 h-4 w-4" />
            Teams
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href={FRONTEND_ROUTES.PROFILE} className="cursor-pointer" data-testid="menu-profile">
            <UserCircle className="mr-2 h-4 w-4" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href={FRONTEND_ROUTES.PROFILE_API_TOKENS} className="cursor-pointer" data-testid="menu-api-tokens">
            <Key className="mr-2 h-4 w-4" />
            API Tokens
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => void logout()} data-testid="menu-logout">
          <LogOut className="mr-2 h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
