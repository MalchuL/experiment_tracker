import { redirect } from "next/navigation";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";

export default function ChangePasswordRedirectPage() {
  redirect(FRONTEND_ROUTES.PROFILE);
}
