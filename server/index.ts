import express, { type Request, Response, NextFunction } from "express";
import { serveStatic } from "./static";
import { createServer } from "http";
import { createProxyMiddleware } from "http-proxy-middleware";
import { spawn, type ChildProcess } from "child_process";

const app = express();
const httpServer = createServer(app);

declare module "http" {
  interface IncomingMessage {
    rawBody: unknown;
  }
}

export function log(message: string, source = "express") {
  const formattedTime = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  console.log(`${formattedTime} [${source}] ${message}`);
}

let fastapiProcess: ChildProcess | null = null;

function startFastAPI(): Promise<void> {
  return new Promise((resolve, reject) => {
    log("Starting FastAPI backend...", "fastapi");
    
    fastapiProcess = spawn("python", ["-c", `
import uvicorn
uvicorn.run('backend.main:app', host='127.0.0.1', port=8000, reload=False, log_level='info')
    `], {
      stdio: ["pipe", "pipe", "pipe"],
      cwd: process.cwd(),
    });

    fastapiProcess.stdout?.on("data", (data) => {
      const output = data.toString().trim();
      if (output) log(output, "fastapi");
      if (output.includes("Application startup complete")) {
        resolve();
      }
    });

    fastapiProcess.stderr?.on("data", (data) => {
      const output = data.toString().trim();
      if (output) log(output, "fastapi");
      if (output.includes("Application startup complete")) {
        resolve();
      }
    });

    fastapiProcess.on("error", (err) => {
      log(`FastAPI error: ${err.message}`, "fastapi");
      reject(err);
    });

    fastapiProcess.on("exit", (code) => {
      log(`FastAPI exited with code ${code}`, "fastapi");
    });

    setTimeout(() => resolve(), 3000);
  });
}

process.on("SIGINT", () => {
  if (fastapiProcess) fastapiProcess.kill();
  process.exit(0);
});

process.on("SIGTERM", () => {
  if (fastapiProcess) fastapiProcess.kill();
  process.exit(0);
});

app.use("/api", createProxyMiddleware({
  target: "http://127.0.0.1:8000",
  changeOrigin: true,
  on: {
    proxyReq: (proxyReq, req) => {
      log(`Proxying ${req.method} ${req.url} to FastAPI`, "proxy");
    },
    error: (err, req, res) => {
      log(`Proxy error: ${err.message}`, "proxy");
      if (res && 'writeHead' in res) {
        (res as any).writeHead(502, { 'Content-Type': 'application/json' });
        (res as any).end(JSON.stringify({ error: 'FastAPI backend unavailable' }));
      }
    },
  },
}));

(async () => {
  await startFastAPI();
  log("FastAPI backend started", "fastapi");

  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";
    log(`Error: ${status} - ${message}`, "error");
    res.status(status).json({ message });
  });

  // importantly only setup vite in development and after
  // setting up all the other routes so the catch-all route
  // doesn't interfere with the other routes
  if (process.env.NODE_ENV === "production") {
    serveStatic(app);
  } else {
    const { setupVite } = await import("./vite");
    await setupVite(httpServer, app);
  }

  // ALWAYS serve the app on the port specified in the environment variable PORT
  // Other ports are firewalled. Default to 5000 if not specified.
  // this serves both the API and the client.
  // It is the only port that is not firewalled.
  const port = parseInt(process.env.PORT || "5000", 10);
  httpServer.listen(
    {
      port,
      host: "0.0.0.0",
      reusePort: true,
    },
    () => {
      log(`Frontend server on port ${port}, proxying /api to FastAPI on port 8000`);
    },
  );
})();
