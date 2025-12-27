import { 
  type User, 
  type InsertUser,
  type Project,
  type InsertProject,
  type Experiment,
  type InsertExperiment,
  type Hypothesis,
  type InsertHypothesis,
  type Metric,
  type InsertMetric,
  type DashboardStats,
  type ProjectMetric,
  EXPERIMENT_COLORS
} from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  getAllProjects(): Promise<Project[]>;
  getProject(id: string): Promise<Project | undefined>;
  createProject(project: InsertProject): Promise<Project>;
  updateProject(id: string, updates: Partial<Project>): Promise<Project | undefined>;
  deleteProject(id: string): Promise<boolean>;

  getAllExperiments(): Promise<Experiment[]>;
  getExperiment(id: string): Promise<Experiment | undefined>;
  getExperimentsByProject(projectId: string): Promise<Experiment[]>;
  getRecentExperiments(limit: number): Promise<Experiment[]>;
  createExperiment(experiment: InsertExperiment): Promise<Experiment>;
  updateExperiment(id: string, updates: Partial<Experiment>): Promise<Experiment | undefined>;
  deleteExperiment(id: string): Promise<boolean>;

  getAllHypotheses(): Promise<Hypothesis[]>;
  getHypothesis(id: string): Promise<Hypothesis | undefined>;
  getHypothesesByProject(projectId: string): Promise<Hypothesis[]>;
  getRecentHypotheses(limit: number): Promise<Hypothesis[]>;
  getHypothesesByExperiment(experimentId: string): Promise<Hypothesis[]>;
  createHypothesis(hypothesis: InsertHypothesis): Promise<Hypothesis>;
  updateHypothesis(id: string, updates: Partial<Hypothesis>): Promise<Hypothesis | undefined>;
  deleteHypothesis(id: string): Promise<boolean>;

  getMetricsByExperiment(experimentId: string): Promise<Metric[]>;
  createMetric(metric: InsertMetric): Promise<Metric>;
  getAggregatedMetricsForProject(projectId: string): Promise<Map<string, Map<string, number | null>>>;

  getDashboardStats(): Promise<DashboardStats>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private projects: Map<string, Project>;
  private experiments: Map<string, Experiment>;
  private hypotheses: Map<string, Hypothesis>;
  private metrics: Map<string, Metric>;
  private experimentHypotheses: Map<string, Set<string>>;

  constructor() {
    this.users = new Map();
    this.projects = new Map();
    this.experiments = new Map();
    this.hypotheses = new Map();
    this.metrics = new Map();
    this.experimentHypotheses = new Map();

    this.seedData();
  }

  private getNextColor(projectId: string): string {
    const projectExperiments = Array.from(this.experiments.values())
      .filter(e => e.projectId === projectId);
    const colorIndex = projectExperiments.length % EXPERIMENT_COLORS.length;
    return EXPERIMENT_COLORS[colorIndex];
  }

  private seedData() {
    const defaultMetrics: ProjectMetric[] = [
      { name: "accuracy", direction: "maximize", aggregation: "best" },
      { name: "loss", direction: "minimize", aggregation: "last" },
      { name: "f1_score", direction: "maximize", aggregation: "best" },
    ];

    const defaultSettings = {
      namingPattern: "{num}_from_{parent}_{change}",
      displayMetrics: ["accuracy", "loss"],
    };

    const project1: Project = {
      id: randomUUID(),
      name: "ViT Training on ImageNet",
      description: "Vision Transformer experiments for image classification",
      owner: "ML Research Team",
      createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      experimentCount: 0,
      hypothesisCount: 0,
      metrics: defaultMetrics,
      settings: defaultSettings,
    };

    const project2: Project = {
      id: randomUUID(),
      name: "BERT Fine-tuning",
      description: "Fine-tuning BERT for domain-specific NLP tasks",
      owner: "NLP Team",
      createdAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      experimentCount: 0,
      hypothesisCount: 0,
      metrics: [
        { name: "f1_score", direction: "maximize", aggregation: "best" },
        { name: "precision", direction: "maximize", aggregation: "last" },
        { name: "recall", direction: "maximize", aggregation: "last" },
      ],
      settings: {
        namingPattern: "{num}_from_{parent}_{change}",
        displayMetrics: ["f1_score", "precision"],
      },
    };

    this.projects.set(project1.id, project1);
    this.projects.set(project2.id, project2);

    const exp1: Experiment = {
      id: randomUUID(),
      projectId: project1.id,
      name: "baseline_vit_b16",
      description: "Baseline Vision Transformer experiment",
      status: "complete",
      parentExperimentId: null,
      rootExperimentId: null,
      features: { model: "ViT-B/16", optimizer: "AdamW", lr: 0.001, batch_size: 256 },
      featuresDiff: null,
      gitDiff: null,
      progress: 100,
      color: EXPERIMENT_COLORS[0],
      order: 0,
      createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      startedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      completedAt: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    };

    const exp2: Experiment = {
      id: randomUUID(),
      projectId: project1.id,
      name: "exp_001_lr_sweep",
      description: "Learning rate sweep experiment",
      status: "running",
      parentExperimentId: exp1.id,
      rootExperimentId: exp1.id,
      features: { model: "ViT-B/16", optimizer: "AdamW", lr: 0.0001, batch_size: 256 },
      featuresDiff: { lr: { from: 0.001, to: 0.0001 } },
      gitDiff: "--- a/train.py\n+++ b/train.py\n@@ -15,7 +15,7 @@ def train():\n-    lr = 0.001\n+    lr = 0.0001",
      progress: 65,
      color: EXPERIMENT_COLORS[1],
      order: 1,
      createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      startedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      completedAt: null,
    };

    const exp3: Experiment = {
      id: randomUUID(),
      projectId: project1.id,
      name: "exp_002_batch_size",
      description: "Batch size experiment",
      status: "planned",
      parentExperimentId: exp1.id,
      rootExperimentId: exp1.id,
      features: { model: "ViT-B/16", optimizer: "AdamW", lr: 0.001, batch_size: 512 },
      featuresDiff: { batch_size: { from: 256, to: 512 } },
      gitDiff: null,
      progress: 0,
      color: EXPERIMENT_COLORS[2],
      order: 2,
      createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      startedAt: null,
      completedAt: null,
    };

    const exp4: Experiment = {
      id: randomUUID(),
      projectId: project2.id,
      name: "bert_baseline",
      description: "BERT baseline experiment",
      status: "complete",
      parentExperimentId: null,
      rootExperimentId: null,
      features: { model: "bert-base-uncased", epochs: 3, lr: 2e-5 },
      featuresDiff: null,
      gitDiff: null,
      progress: 100,
      color: EXPERIMENT_COLORS[0],
      order: 0,
      createdAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
      startedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
      completedAt: new Date(Date.now() - 9 * 24 * 60 * 60 * 1000).toISOString(),
    };

    const exp5: Experiment = {
      id: randomUUID(),
      projectId: project2.id,
      name: "bert_lr_experiment",
      description: "BERT learning rate experiment",
      status: "failed",
      parentExperimentId: exp4.id,
      rootExperimentId: exp4.id,
      features: { model: "bert-base-uncased", epochs: 3, lr: 1e-4 },
      featuresDiff: { lr: { from: 2e-5, to: 1e-4 } },
      gitDiff: null,
      progress: 45,
      color: EXPERIMENT_COLORS[1],
      order: 1,
      createdAt: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
      startedAt: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
      completedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    };

    this.experiments.set(exp1.id, exp1);
    this.experiments.set(exp2.id, exp2);
    this.experiments.set(exp3.id, exp3);
    this.experiments.set(exp4.id, exp4);
    this.experiments.set(exp5.id, exp5);

    const hyp1: Hypothesis = {
      id: randomUUID(),
      projectId: project1.id,
      title: "Lower learning rate improves convergence stability",
      description: "We hypothesize that reducing the learning rate from 1e-3 to 1e-4 will result in more stable training and better final accuracy.",
      author: "Dr. Smith",
      status: "testing",
      targetMetrics: ["accuracy", "loss"],
      baseline: "root",
      createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    };

    const hyp2: Hypothesis = {
      id: randomUUID(),
      projectId: project1.id,
      title: "Larger batch size reduces training time",
      description: "Increasing batch size from 256 to 512 should reduce total training time while maintaining accuracy.",
      author: "Dr. Johnson",
      status: "proposed",
      targetMetrics: ["training_time", "accuracy"],
      baseline: "root",
      createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      updatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    };

    const hyp3: Hypothesis = {
      id: randomUUID(),
      projectId: project2.id,
      title: "Domain-specific pretraining improves F1 score",
      description: "Pre-training on domain-specific data before fine-tuning will improve F1 score on the target task.",
      author: "Dr. Lee",
      status: "supported",
      targetMetrics: ["f1_score", "precision", "recall"],
      baseline: "best",
      createdAt: new Date(Date.now() - 12 * 24 * 60 * 60 * 1000).toISOString(),
      updatedAt: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    };

    this.hypotheses.set(hyp1.id, hyp1);
    this.hypotheses.set(hyp2.id, hyp2);
    this.hypotheses.set(hyp3.id, hyp3);

    const metric1: Metric = {
      id: randomUUID(),
      experimentId: exp1.id,
      name: "accuracy",
      value: 0.8234,
      step: 100,
      direction: "maximize",
      createdAt: new Date().toISOString(),
    };

    const metric2: Metric = {
      id: randomUUID(),
      experimentId: exp1.id,
      name: "loss",
      value: 0.3421,
      step: 100,
      direction: "minimize",
      createdAt: new Date().toISOString(),
    };

    const metric3: Metric = {
      id: randomUUID(),
      experimentId: exp2.id,
      name: "accuracy",
      value: 0.7891,
      step: 65,
      direction: "maximize",
      createdAt: new Date().toISOString(),
    };

    const metric4: Metric = {
      id: randomUUID(),
      experimentId: exp2.id,
      name: "loss",
      value: 0.4123,
      step: 65,
      direction: "minimize",
      createdAt: new Date().toISOString(),
    };

    const metric5: Metric = {
      id: randomUUID(),
      experimentId: exp4.id,
      name: "f1_score",
      value: 0.8912,
      step: 100,
      direction: "maximize",
      createdAt: new Date().toISOString(),
    };

    const metric6: Metric = {
      id: randomUUID(),
      experimentId: exp4.id,
      name: "precision",
      value: 0.9021,
      step: 100,
      direction: "maximize",
      createdAt: new Date().toISOString(),
    };

    const metric7: Metric = {
      id: randomUUID(),
      experimentId: exp4.id,
      name: "recall",
      value: 0.8804,
      step: 100,
      direction: "maximize",
      createdAt: new Date().toISOString(),
    };

    this.metrics.set(metric1.id, metric1);
    this.metrics.set(metric2.id, metric2);
    this.metrics.set(metric3.id, metric3);
    this.metrics.set(metric4.id, metric4);
    this.metrics.set(metric5.id, metric5);
    this.metrics.set(metric6.id, metric6);
    this.metrics.set(metric7.id, metric7);

    this.experimentHypotheses.set(exp2.id, new Set([hyp1.id]));

    this.updateProjectCounts();
  }

  private updateProjectCounts() {
    this.projects.forEach((project, projectId) => {
      const experimentCount = Array.from(this.experiments.values())
        .filter(e => e.projectId === projectId).length;
      const hypothesisCount = Array.from(this.hypotheses.values())
        .filter(h => h.projectId === projectId).length;
      
      this.projects.set(projectId, {
        ...project,
        experimentCount,
        hypothesisCount,
      });
    });
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = randomUUID();
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  async getAllProjects(): Promise<Project[]> {
    return Array.from(this.projects.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  }

  async getProject(id: string): Promise<Project | undefined> {
    return this.projects.get(id);
  }

  async createProject(insertProject: InsertProject): Promise<Project> {
    const id = randomUUID();
    const project: Project = {
      ...insertProject,
      id,
      createdAt: new Date().toISOString(),
      experimentCount: 0,
      hypothesisCount: 0,
      metrics: insertProject.metrics || [],
      settings: insertProject.settings || {
        namingPattern: "{num}_from_{parent}_{change}",
        displayMetrics: [],
      },
    };
    this.projects.set(id, project);
    return project;
  }

  async updateProject(id: string, updates: Partial<Project>): Promise<Project | undefined> {
    const project = this.projects.get(id);
    if (!project) return undefined;

    const updated = { ...project, ...updates };
    this.projects.set(id, updated);
    return updated;
  }

  async deleteProject(id: string): Promise<boolean> {
    const experiments = await this.getExperimentsByProject(id);
    experiments.forEach(exp => this.experiments.delete(exp.id));

    const hypotheses = await this.getHypothesesByProject(id);
    hypotheses.forEach(hyp => this.hypotheses.delete(hyp.id));

    return this.projects.delete(id);
  }

  async getAllExperiments(): Promise<Experiment[]> {
    return Array.from(this.experiments.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  }

  async getExperiment(id: string): Promise<Experiment | undefined> {
    return this.experiments.get(id);
  }

  async getExperimentsByProject(projectId: string): Promise<Experiment[]> {
    return Array.from(this.experiments.values())
      .filter(e => e.projectId === projectId)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }

  async getRecentExperiments(limit: number): Promise<Experiment[]> {
    return Array.from(this.experiments.values())
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, limit);
  }

  async createExperiment(insertExperiment: InsertExperiment): Promise<Experiment> {
    const id = randomUUID();
    const now = new Date().toISOString();

    let rootExperimentId = null;
    if (insertExperiment.parentExperimentId) {
      const parent = this.experiments.get(insertExperiment.parentExperimentId);
      rootExperimentId = parent?.rootExperimentId || parent?.id || null;
    }

    const color = insertExperiment.color || this.getNextColor(insertExperiment.projectId);

    const projectExperiments = await this.getExperimentsByProject(insertExperiment.projectId);
    const maxOrder = projectExperiments.reduce((max, e) => Math.max(max, e.order), -1);

    const experiment: Experiment = {
      id,
      projectId: insertExperiment.projectId,
      name: insertExperiment.name,
      description: insertExperiment.description || "",
      status: insertExperiment.status || "planned",
      parentExperimentId: insertExperiment.parentExperimentId || null,
      rootExperimentId,
      features: insertExperiment.features || {},
      featuresDiff: null,
      gitDiff: insertExperiment.gitDiff || null,
      progress: 0,
      color,
      order: insertExperiment.order ?? maxOrder + 1,
      createdAt: now,
      startedAt: insertExperiment.status === "running" ? now : null,
      completedAt: null,
    };

    if (insertExperiment.parentExperimentId) {
      const parent = this.experiments.get(insertExperiment.parentExperimentId);
      if (parent && insertExperiment.features) {
        experiment.featuresDiff = this.computeFeaturesDiff(parent.features, insertExperiment.features);
      }
    }

    this.experiments.set(id, experiment);
    this.updateProjectCounts();
    return experiment;
  }

  private computeFeaturesDiff(
    parentFeatures: Record<string, unknown>,
    childFeatures: Record<string, unknown>
  ): Record<string, unknown> {
    const diff: Record<string, unknown> = {};

    for (const key of Object.keys(childFeatures)) {
      if (parentFeatures[key] !== childFeatures[key]) {
        diff[key] = {
          from: parentFeatures[key],
          to: childFeatures[key],
        };
      }
    }

    return diff;
  }

  async updateExperiment(id: string, updates: Partial<Experiment>): Promise<Experiment | undefined> {
    const experiment = this.experiments.get(id);
    if (!experiment) return undefined;

    const now = new Date().toISOString();
    const updated = { ...experiment, ...updates };

    if (updates.status === "running" && !experiment.startedAt) {
      updated.startedAt = now;
    }
    if ((updates.status === "complete" || updates.status === "failed") && !experiment.completedAt) {
      updated.completedAt = now;
      updated.progress = updates.status === "complete" ? 100 : experiment.progress;
    }

    this.experiments.set(id, updated);
    return updated;
  }

  async deleteExperiment(id: string): Promise<boolean> {
    this.experiments.forEach((exp, expId) => {
      if (exp.parentExperimentId === id) {
        this.experiments.set(expId, { ...exp, parentExperimentId: null });
      }
    });

    const deleted = this.experiments.delete(id);
    this.updateProjectCounts();
    return deleted;
  }

  async getAllHypotheses(): Promise<Hypothesis[]> {
    return Array.from(this.hypotheses.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  }

  async getHypothesis(id: string): Promise<Hypothesis | undefined> {
    return this.hypotheses.get(id);
  }

  async getHypothesesByProject(projectId: string): Promise<Hypothesis[]> {
    return Array.from(this.hypotheses.values())
      .filter(h => h.projectId === projectId)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }

  async getRecentHypotheses(limit: number): Promise<Hypothesis[]> {
    return Array.from(this.hypotheses.values())
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, limit);
  }

  async getHypothesesByExperiment(experimentId: string): Promise<Hypothesis[]> {
    const hypothesisIds = this.experimentHypotheses.get(experimentId);
    if (!hypothesisIds) return [];

    return Array.from(hypothesisIds)
      .map(id => this.hypotheses.get(id))
      .filter((h): h is Hypothesis => h !== undefined);
  }

  async createHypothesis(insertHypothesis: InsertHypothesis): Promise<Hypothesis> {
    const id = randomUUID();
    const now = new Date().toISOString();

    const hypothesis: Hypothesis = {
      id,
      projectId: insertHypothesis.projectId,
      title: insertHypothesis.title,
      description: insertHypothesis.description,
      author: insertHypothesis.author,
      status: insertHypothesis.status || "proposed",
      targetMetrics: insertHypothesis.targetMetrics || [],
      baseline: insertHypothesis.baseline || "root",
      createdAt: now,
      updatedAt: now,
    };

    this.hypotheses.set(id, hypothesis);
    this.updateProjectCounts();
    return hypothesis;
  }

  async updateHypothesis(id: string, updates: Partial<Hypothesis>): Promise<Hypothesis | undefined> {
    const hypothesis = this.hypotheses.get(id);
    if (!hypothesis) return undefined;

    const updated = { 
      ...hypothesis, 
      ...updates,
      updatedAt: new Date().toISOString(),
    };
    this.hypotheses.set(id, updated);
    return updated;
  }

  async deleteHypothesis(id: string): Promise<boolean> {
    const deleted = this.hypotheses.delete(id);
    this.updateProjectCounts();
    return deleted;
  }

  async getMetricsByExperiment(experimentId: string): Promise<Metric[]> {
    return Array.from(this.metrics.values())
      .filter(m => m.experimentId === experimentId)
      .sort((a, b) => b.step - a.step);
  }

  async createMetric(insertMetric: InsertMetric): Promise<Metric> {
    const id = randomUUID();
    const metric: Metric = {
      id,
      experimentId: insertMetric.experimentId,
      name: insertMetric.name,
      value: insertMetric.value,
      step: insertMetric.step || 0,
      direction: insertMetric.direction || "minimize",
      createdAt: new Date().toISOString(),
    };
    this.metrics.set(id, metric);
    return metric;
  }

  async getAggregatedMetricsForProject(projectId: string): Promise<Map<string, Map<string, number | null>>> {
    const project = this.projects.get(projectId);
    if (!project) return new Map();

    const experiments = await this.getExperimentsByProject(projectId);
    const result = new Map<string, Map<string, number | null>>();

    for (const experiment of experiments) {
      const experimentMetrics = await this.getMetricsByExperiment(experiment.id);
      const metricValues = new Map<string, number | null>();

      for (const projectMetric of project.metrics) {
        const matchingMetrics = experimentMetrics.filter(m => m.name === projectMetric.name);
        
        if (matchingMetrics.length === 0) {
          metricValues.set(projectMetric.name, null);
        } else {
          let value: number;
          switch (projectMetric.aggregation) {
            case "last":
              value = matchingMetrics.sort((a, b) => b.step - a.step)[0].value;
              break;
            case "best":
              if (projectMetric.direction === "maximize") {
                value = Math.max(...matchingMetrics.map(m => m.value));
              } else {
                value = Math.min(...matchingMetrics.map(m => m.value));
              }
              break;
            case "average":
              value = matchingMetrics.reduce((sum, m) => sum + m.value, 0) / matchingMetrics.length;
              break;
            default:
              value = matchingMetrics[0].value;
          }
          metricValues.set(projectMetric.name, value);
        }
      }

      result.set(experiment.id, metricValues);
    }

    return result;
  }

  async getDashboardStats(): Promise<DashboardStats> {
    const experiments = Array.from(this.experiments.values());
    const hypotheses = Array.from(this.hypotheses.values());

    return {
      totalProjects: this.projects.size,
      totalExperiments: experiments.length,
      runningExperiments: experiments.filter(e => e.status === "running").length,
      completedExperiments: experiments.filter(e => e.status === "complete").length,
      failedExperiments: experiments.filter(e => e.status === "failed").length,
      totalHypotheses: hypotheses.length,
      supportedHypotheses: hypotheses.filter(h => h.status === "supported").length,
      refutedHypotheses: hypotheses.filter(h => h.status === "refuted").length,
    };
  }
}

export const storage = new MemStorage();
