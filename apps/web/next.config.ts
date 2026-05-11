import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  output: "standalone",
  // Monorepo: trace from repo root (`pnpm` runs Next with cwd `apps/web`, so parent is `apps/`).
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
};

export default nextConfig;
