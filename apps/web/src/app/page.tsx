import { redirect } from "next/navigation";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";

export default function Home() {
  redirect(FRONTEND_ROUTES.PROJECTS);
}
