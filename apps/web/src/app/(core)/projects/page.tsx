"use client";

import { useAuth } from "@/domain/auth/guard/provider";

export default function Projects() {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <div>Loading...</div>;
  }
  return (
    <div>
      <h1>Projects</h1>
      <p>Welcome, {user?.display_name}</p>
    </div>
  );
}