import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { 
  insertProjectSchema, 
  insertExperimentSchema, 
  insertHypothesisSchema,
  insertMetricSchema 
} from "@shared/schema";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.get("/api/dashboard/stats", async (req, res) => {
    try {
      const stats = await storage.getDashboardStats();
      res.json(stats);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch dashboard stats" });
    }
  });

  app.get("/api/projects", async (req, res) => {
    try {
      const projects = await storage.getAllProjects();
      res.json(projects);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch projects" });
    }
  });

  app.get("/api/projects/:id", async (req, res) => {
    try {
      const project = await storage.getProject(req.params.id);
      if (!project) {
        return res.status(404).json({ error: "Project not found" });
      }
      res.json(project);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch project" });
    }
  });

  app.get("/api/projects/:id/experiments", async (req, res) => {
    try {
      const experiments = await storage.getExperimentsByProject(req.params.id);
      res.json(experiments);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch project experiments" });
    }
  });

  app.get("/api/projects/:id/hypotheses", async (req, res) => {
    try {
      const hypotheses = await storage.getHypothesesByProject(req.params.id);
      res.json(hypotheses);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch project hypotheses" });
    }
  });

  app.post("/api/projects", async (req, res) => {
    try {
      const parsed = insertProjectSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ error: parsed.error.errors });
      }
      const project = await storage.createProject(parsed.data);
      res.status(201).json(project);
    } catch (error) {
      res.status(500).json({ error: "Failed to create project" });
    }
  });

  app.patch("/api/projects/:id", async (req, res) => {
    try {
      const project = await storage.updateProject(req.params.id, req.body);
      if (!project) {
        return res.status(404).json({ error: "Project not found" });
      }
      res.json(project);
    } catch (error) {
      res.status(500).json({ error: "Failed to update project" });
    }
  });

  app.delete("/api/projects/:id", async (req, res) => {
    try {
      const deleted = await storage.deleteProject(req.params.id);
      if (!deleted) {
        return res.status(404).json({ error: "Project not found" });
      }
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: "Failed to delete project" });
    }
  });

  app.get("/api/experiments", async (req, res) => {
    try {
      const experiments = await storage.getAllExperiments();
      res.json(experiments);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch experiments" });
    }
  });

  app.get("/api/experiments/recent", async (req, res) => {
    try {
      const limit = parseInt(req.query.limit as string) || 10;
      const experiments = await storage.getRecentExperiments(limit);
      res.json(experiments);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch recent experiments" });
    }
  });

  app.get("/api/experiments/:id", async (req, res) => {
    try {
      const experiment = await storage.getExperiment(req.params.id);
      if (!experiment) {
        return res.status(404).json({ error: "Experiment not found" });
      }
      res.json(experiment);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch experiment" });
    }
  });

  app.get("/api/experiments/:id/metrics", async (req, res) => {
    try {
      const metrics = await storage.getMetricsByExperiment(req.params.id);
      res.json(metrics);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch experiment metrics" });
    }
  });

  app.post("/api/experiments", async (req, res) => {
    try {
      const parsed = insertExperimentSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ error: parsed.error.errors });
      }
      const experiment = await storage.createExperiment(parsed.data);
      res.status(201).json(experiment);
    } catch (error) {
      res.status(500).json({ error: "Failed to create experiment" });
    }
  });

  app.patch("/api/experiments/:id", async (req, res) => {
    try {
      const experiment = await storage.updateExperiment(req.params.id, req.body);
      if (!experiment) {
        return res.status(404).json({ error: "Experiment not found" });
      }
      res.json(experiment);
    } catch (error) {
      res.status(500).json({ error: "Failed to update experiment" });
    }
  });

  app.delete("/api/experiments/:id", async (req, res) => {
    try {
      const deleted = await storage.deleteExperiment(req.params.id);
      if (!deleted) {
        return res.status(404).json({ error: "Experiment not found" });
      }
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: "Failed to delete experiment" });
    }
  });

  app.get("/api/hypotheses", async (req, res) => {
    try {
      const hypotheses = await storage.getAllHypotheses();
      res.json(hypotheses);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch hypotheses" });
    }
  });

  app.get("/api/hypotheses/recent", async (req, res) => {
    try {
      const limit = parseInt(req.query.limit as string) || 10;
      const hypotheses = await storage.getRecentHypotheses(limit);
      res.json(hypotheses);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch recent hypotheses" });
    }
  });

  app.get("/api/hypotheses/:id", async (req, res) => {
    try {
      const hypothesis = await storage.getHypothesis(req.params.id);
      if (!hypothesis) {
        return res.status(404).json({ error: "Hypothesis not found" });
      }
      res.json(hypothesis);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch hypothesis" });
    }
  });

  app.get("/api/hypotheses/:id/experiments", async (req, res) => {
    try {
      const experiments = await storage.getHypothesesByExperiment(req.params.id);
      res.json(experiments);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch linked experiments" });
    }
  });

  app.post("/api/hypotheses", async (req, res) => {
    try {
      const parsed = insertHypothesisSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ error: parsed.error.errors });
      }
      const hypothesis = await storage.createHypothesis(parsed.data);
      res.status(201).json(hypothesis);
    } catch (error) {
      res.status(500).json({ error: "Failed to create hypothesis" });
    }
  });

  app.patch("/api/hypotheses/:id", async (req, res) => {
    try {
      const hypothesis = await storage.updateHypothesis(req.params.id, req.body);
      if (!hypothesis) {
        return res.status(404).json({ error: "Hypothesis not found" });
      }
      res.json(hypothesis);
    } catch (error) {
      res.status(500).json({ error: "Failed to update hypothesis" });
    }
  });

  app.delete("/api/hypotheses/:id", async (req, res) => {
    try {
      const deleted = await storage.deleteHypothesis(req.params.id);
      if (!deleted) {
        return res.status(404).json({ error: "Hypothesis not found" });
      }
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ error: "Failed to delete hypothesis" });
    }
  });

  app.post("/api/metrics", async (req, res) => {
    try {
      const parsed = insertMetricSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ error: parsed.error.errors });
      }
      const metric = await storage.createMetric(parsed.data);
      res.status(201).json(metric);
    } catch (error) {
      res.status(500).json({ error: "Failed to create metric" });
    }
  });

  app.get("/api/projects/:id/metrics", async (req, res) => {
    try {
      const metricsMap = await storage.getAggregatedMetricsForProject(req.params.id);
      const result: Record<string, Record<string, number | null>> = {};
      metricsMap.forEach((metricValues, experimentId) => {
        result[experimentId] = Object.fromEntries(metricValues);
      });
      res.json(result);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch project metrics" });
    }
  });

  return httpServer;
}
