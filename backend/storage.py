import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from .schemas import (
    Project, ProjectCreate, ProjectUpdate,
    Experiment, ExperimentCreate, ExperimentUpdate, ExperimentStatus,
    Hypothesis, HypothesisCreate, HypothesisUpdate, HypothesisStatus,
    Metric, MetricCreate, MetricDirection, MetricAggregation,
    ProjectMetric, ProjectSettings, DashboardStats, EXPERIMENT_COLORS
)


class MemStorage:
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.experiments: Dict[str, Experiment] = {}
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.metrics: Dict[str, Metric] = {}
        self.experiment_hypotheses: Dict[str, Set[str]] = {}
        self._seed_data()

    def _get_next_color(self, project_id: str) -> str:
        project_experiments = [e for e in self.experiments.values() if e.projectId == project_id]
        color_index = len(project_experiments) % len(EXPERIMENT_COLORS)
        return EXPERIMENT_COLORS[color_index]

    def _seed_data(self):
        default_metrics = [
            ProjectMetric(name="accuracy", direction=MetricDirection.MAXIMIZE, aggregation=MetricAggregation.BEST),
            ProjectMetric(name="loss", direction=MetricDirection.MINIMIZE, aggregation=MetricAggregation.LAST),
            ProjectMetric(name="f1_score", direction=MetricDirection.MAXIMIZE, aggregation=MetricAggregation.BEST),
        ]

        default_settings = ProjectSettings(
            namingPattern="{num}_from_{parent}_{change}",
            displayMetrics=["accuracy", "loss"],
        )

        project1_id = str(uuid.uuid4())
        project1 = Project(
            id=project1_id,
            name="ViT Training on ImageNet",
            description="Vision Transformer experiments for image classification",
            owner="ML Research Team",
            createdAt=(datetime.now() - timedelta(days=7)).isoformat(),
            experimentCount=0,
            hypothesisCount=0,
            metrics=default_metrics,
            settings=default_settings,
        )

        project2_id = str(uuid.uuid4())
        project2 = Project(
            id=project2_id,
            name="BERT Fine-tuning",
            description="Fine-tuning BERT for domain-specific NLP tasks",
            owner="NLP Team",
            createdAt=(datetime.now() - timedelta(days=14)).isoformat(),
            experimentCount=0,
            hypothesisCount=0,
            metrics=[
                ProjectMetric(name="f1_score", direction=MetricDirection.MAXIMIZE, aggregation=MetricAggregation.BEST),
                ProjectMetric(name="precision", direction=MetricDirection.MAXIMIZE, aggregation=MetricAggregation.LAST),
                ProjectMetric(name="recall", direction=MetricDirection.MAXIMIZE, aggregation=MetricAggregation.LAST),
            ],
            settings=ProjectSettings(namingPattern="{num}_from_{parent}_{change}", displayMetrics=["f1_score", "precision"]),
        )

        self.projects[project1_id] = project1
        self.projects[project2_id] = project2

        exp1_id = str(uuid.uuid4())
        exp1 = Experiment(
            id=exp1_id,
            projectId=project1_id,
            name="baseline_vit_b16",
            description="Baseline Vision Transformer experiment",
            status=ExperimentStatus.COMPLETE,
            parentExperimentId=None,
            rootExperimentId=None,
            features={"model": "ViT-B/16", "optimizer": "AdamW", "lr": 0.001, "batch_size": 256},
            featuresDiff=None,
            gitDiff=None,
            progress=100,
            color=EXPERIMENT_COLORS[0],
            order=0,
            createdAt=(datetime.now() - timedelta(days=5)).isoformat(),
            startedAt=(datetime.now() - timedelta(days=5)).isoformat(),
            completedAt=(datetime.now() - timedelta(days=4)).isoformat(),
        )

        exp2_id = str(uuid.uuid4())
        exp2 = Experiment(
            id=exp2_id,
            projectId=project1_id,
            name="exp_001_lr_sweep",
            description="Learning rate sweep experiment",
            status=ExperimentStatus.RUNNING,
            parentExperimentId=exp1_id,
            rootExperimentId=exp1_id,
            features={"model": "ViT-B/16", "optimizer": "AdamW", "lr": 0.0001, "batch_size": 256},
            featuresDiff={"lr": {"from": 0.001, "to": 0.0001}},
            gitDiff="--- a/train.py\n+++ b/train.py\n@@ -15,7 +15,7 @@ def train():\n-    lr = 0.001\n+    lr = 0.0001",
            progress=65,
            color=EXPERIMENT_COLORS[1],
            order=1,
            createdAt=(datetime.now() - timedelta(days=2)).isoformat(),
            startedAt=(datetime.now() - timedelta(days=2)).isoformat(),
            completedAt=None,
        )

        exp3_id = str(uuid.uuid4())
        exp3 = Experiment(
            id=exp3_id,
            projectId=project1_id,
            name="exp_002_batch_size",
            description="Batch size experiment",
            status=ExperimentStatus.PLANNED,
            parentExperimentId=exp1_id,
            rootExperimentId=exp1_id,
            features={"model": "ViT-B/16", "optimizer": "AdamW", "lr": 0.001, "batch_size": 512},
            featuresDiff={"batch_size": {"from": 256, "to": 512}},
            gitDiff=None,
            progress=0,
            color=EXPERIMENT_COLORS[2],
            order=2,
            createdAt=(datetime.now() - timedelta(days=1)).isoformat(),
            startedAt=None,
            completedAt=None,
        )

        exp4_id = str(uuid.uuid4())
        exp4 = Experiment(
            id=exp4_id,
            projectId=project2_id,
            name="bert_baseline",
            description="BERT baseline experiment",
            status=ExperimentStatus.COMPLETE,
            parentExperimentId=None,
            rootExperimentId=None,
            features={"model": "bert-base-uncased", "epochs": 3, "lr": 2e-5},
            featuresDiff=None,
            gitDiff=None,
            progress=100,
            color=EXPERIMENT_COLORS[0],
            order=0,
            createdAt=(datetime.now() - timedelta(days=10)).isoformat(),
            startedAt=(datetime.now() - timedelta(days=10)).isoformat(),
            completedAt=(datetime.now() - timedelta(days=9)).isoformat(),
        )

        exp5_id = str(uuid.uuid4())
        exp5 = Experiment(
            id=exp5_id,
            projectId=project2_id,
            name="bert_lr_experiment",
            description="BERT learning rate experiment",
            status=ExperimentStatus.FAILED,
            parentExperimentId=exp4_id,
            rootExperimentId=exp4_id,
            features={"model": "bert-base-uncased", "epochs": 3, "lr": 1e-4},
            featuresDiff={"lr": {"from": 2e-5, "to": 1e-4}},
            gitDiff=None,
            progress=45,
            color=EXPERIMENT_COLORS[1],
            order=1,
            createdAt=(datetime.now() - timedelta(days=8)).isoformat(),
            startedAt=(datetime.now() - timedelta(days=8)).isoformat(),
            completedAt=(datetime.now() - timedelta(days=7)).isoformat(),
        )

        self.experiments[exp1_id] = exp1
        self.experiments[exp2_id] = exp2
        self.experiments[exp3_id] = exp3
        self.experiments[exp4_id] = exp4
        self.experiments[exp5_id] = exp5

        hyp1_id = str(uuid.uuid4())
        hyp1 = Hypothesis(
            id=hyp1_id,
            projectId=project1_id,
            title="Lower learning rate improves convergence stability",
            description="We hypothesize that reducing the learning rate from 1e-3 to 1e-4 will result in more stable training and better final accuracy.",
            author="Dr. Smith",
            status=HypothesisStatus.TESTING,
            targetMetrics=["accuracy", "loss"],
            baseline="root",
            createdAt=(datetime.now() - timedelta(days=3)).isoformat(),
            updatedAt=(datetime.now() - timedelta(days=1)).isoformat(),
        )

        hyp2_id = str(uuid.uuid4())
        hyp2 = Hypothesis(
            id=hyp2_id,
            projectId=project1_id,
            title="Larger batch size reduces training time",
            description="Increasing batch size from 256 to 512 should reduce total training time while maintaining accuracy.",
            author="Dr. Johnson",
            status=HypothesisStatus.PROPOSED,
            targetMetrics=["training_time", "accuracy"],
            baseline="root",
            createdAt=(datetime.now() - timedelta(days=2)).isoformat(),
            updatedAt=(datetime.now() - timedelta(days=2)).isoformat(),
        )

        hyp3_id = str(uuid.uuid4())
        hyp3 = Hypothesis(
            id=hyp3_id,
            projectId=project2_id,
            title="Domain-specific pretraining improves F1 score",
            description="Pre-training on domain-specific data before fine-tuning will improve F1 score on the target task.",
            author="Dr. Lee",
            status=HypothesisStatus.SUPPORTED,
            targetMetrics=["f1_score", "precision", "recall"],
            baseline="best",
            createdAt=(datetime.now() - timedelta(days=12)).isoformat(),
            updatedAt=(datetime.now() - timedelta(days=6)).isoformat(),
        )

        self.hypotheses[hyp1_id] = hyp1
        self.hypotheses[hyp2_id] = hyp2
        self.hypotheses[hyp3_id] = hyp3

        metric1 = Metric(id=str(uuid.uuid4()), experimentId=exp1_id, name="accuracy", value=0.8234, step=100, direction=MetricDirection.MAXIMIZE, createdAt=datetime.now().isoformat())
        metric2 = Metric(id=str(uuid.uuid4()), experimentId=exp1_id, name="loss", value=0.3421, step=100, direction=MetricDirection.MINIMIZE, createdAt=datetime.now().isoformat())
        metric3 = Metric(id=str(uuid.uuid4()), experimentId=exp2_id, name="accuracy", value=0.7891, step=65, direction=MetricDirection.MAXIMIZE, createdAt=datetime.now().isoformat())
        metric4 = Metric(id=str(uuid.uuid4()), experimentId=exp2_id, name="loss", value=0.4123, step=65, direction=MetricDirection.MINIMIZE, createdAt=datetime.now().isoformat())
        metric5 = Metric(id=str(uuid.uuid4()), experimentId=exp4_id, name="f1_score", value=0.8912, step=100, direction=MetricDirection.MAXIMIZE, createdAt=datetime.now().isoformat())
        metric6 = Metric(id=str(uuid.uuid4()), experimentId=exp4_id, name="precision", value=0.9021, step=100, direction=MetricDirection.MAXIMIZE, createdAt=datetime.now().isoformat())
        metric7 = Metric(id=str(uuid.uuid4()), experimentId=exp4_id, name="recall", value=0.8804, step=100, direction=MetricDirection.MAXIMIZE, createdAt=datetime.now().isoformat())

        self.metrics[metric1.id] = metric1
        self.metrics[metric2.id] = metric2
        self.metrics[metric3.id] = metric3
        self.metrics[metric4.id] = metric4
        self.metrics[metric5.id] = metric5
        self.metrics[metric6.id] = metric6
        self.metrics[metric7.id] = metric7

        self.experiment_hypotheses[exp2_id] = {hyp1_id}
        self._update_project_counts()

    def _update_project_counts(self):
        for project_id, project in self.projects.items():
            experiment_count = len([e for e in self.experiments.values() if e.projectId == project_id])
            hypothesis_count = len([h for h in self.hypotheses.values() if h.projectId == project_id])
            self.projects[project_id] = project.model_copy(update={
                "experimentCount": experiment_count,
                "hypothesisCount": hypothesis_count,
            })

    def get_all_projects(self) -> List[Project]:
        return sorted(self.projects.values(), key=lambda p: p.createdAt, reverse=True)

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def create_project(self, data: ProjectCreate) -> Project:
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name=data.name,
            description=data.description,
            owner=data.owner,
            createdAt=datetime.now().isoformat(),
            experimentCount=0,
            hypothesisCount=0,
            metrics=data.metrics,
            settings=data.settings,
        )
        self.projects[project_id] = project
        return project

    def update_project(self, project_id: str, data: ProjectUpdate) -> Optional[Project]:
        project = self.projects.get(project_id)
        if not project:
            return None
        update_data = data.model_dump(exclude_unset=True)
        updated = project.model_copy(update=update_data)
        self.projects[project_id] = updated
        return updated

    def delete_project(self, project_id: str) -> bool:
        if project_id not in self.projects:
            return False
        exp_ids = [e.id for e in self.experiments.values() if e.projectId == project_id]
        for exp_id in exp_ids:
            del self.experiments[exp_id]
        hyp_ids = [h.id for h in self.hypotheses.values() if h.projectId == project_id]
        for hyp_id in hyp_ids:
            del self.hypotheses[hyp_id]
        del self.projects[project_id]
        return True

    def get_all_experiments(self) -> List[Experiment]:
        return sorted(self.experiments.values(), key=lambda e: e.createdAt, reverse=True)

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self.experiments.get(experiment_id)

    def get_experiments_by_project(self, project_id: str) -> List[Experiment]:
        exps = [e for e in self.experiments.values() if e.projectId == project_id]
        return sorted(exps, key=lambda e: e.createdAt, reverse=True)

    def get_recent_experiments(self, limit: int) -> List[Experiment]:
        exps = sorted(self.experiments.values(), key=lambda e: e.createdAt, reverse=True)
        return exps[:limit]

    def _compute_features_diff(self, parent_features: Dict, child_features: Dict) -> Dict:
        diff = {}
        for key in child_features:
            if parent_features.get(key) != child_features[key]:
                diff[key] = {"from": parent_features.get(key), "to": child_features[key]}
        return diff

    def create_experiment(self, data: ExperimentCreate) -> Experiment:
        experiment_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        root_experiment_id = None
        if data.parentExperimentId:
            parent = self.experiments.get(data.parentExperimentId)
            if parent:
                root_experiment_id = parent.rootExperimentId or parent.id

        color = data.color or self._get_next_color(data.projectId)
        project_experiments = self.get_experiments_by_project(data.projectId)
        max_order = max([e.order for e in project_experiments], default=-1)

        features_diff = None
        if data.parentExperimentId:
            parent = self.experiments.get(data.parentExperimentId)
            if parent and data.features:
                features_diff = self._compute_features_diff(parent.features, data.features)

        experiment = Experiment(
            id=experiment_id,
            projectId=data.projectId,
            name=data.name,
            description=data.description,
            status=data.status,
            parentExperimentId=data.parentExperimentId,
            rootExperimentId=root_experiment_id,
            features=data.features,
            featuresDiff=features_diff,
            gitDiff=data.gitDiff,
            progress=0,
            color=color,
            order=data.order if data.order is not None else max_order + 1,
            createdAt=now,
            startedAt=now if data.status == ExperimentStatus.RUNNING else None,
            completedAt=None,
        )
        self.experiments[experiment_id] = experiment
        self._update_project_counts()
        return experiment

    def update_experiment(self, experiment_id: str, data: ExperimentUpdate) -> Optional[Experiment]:
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return None

        now = datetime.now().isoformat()
        update_data = data.model_dump(exclude_unset=True)

        if "status" in update_data:
            if update_data["status"] == ExperimentStatus.RUNNING and not experiment.startedAt:
                update_data["startedAt"] = now
            if update_data["status"] in [ExperimentStatus.COMPLETE, ExperimentStatus.FAILED] and not experiment.completedAt:
                update_data["completedAt"] = now
                if update_data["status"] == ExperimentStatus.COMPLETE:
                    update_data["progress"] = 100

        updated = experiment.model_copy(update=update_data)
        self.experiments[experiment_id] = updated
        return updated

    def delete_experiment(self, experiment_id: str) -> bool:
        if experiment_id not in self.experiments:
            return False
        for exp_id, exp in list(self.experiments.items()):
            if exp.parentExperimentId == experiment_id:
                self.experiments[exp_id] = exp.model_copy(update={"parentExperimentId": None})
        del self.experiments[experiment_id]
        self._update_project_counts()
        return True

    def get_all_hypotheses(self) -> List[Hypothesis]:
        return sorted(self.hypotheses.values(), key=lambda h: h.createdAt, reverse=True)

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        return self.hypotheses.get(hypothesis_id)

    def get_hypotheses_by_project(self, project_id: str) -> List[Hypothesis]:
        hyps = [h for h in self.hypotheses.values() if h.projectId == project_id]
        return sorted(hyps, key=lambda h: h.createdAt, reverse=True)

    def get_recent_hypotheses(self, limit: int) -> List[Hypothesis]:
        hyps = sorted(self.hypotheses.values(), key=lambda h: h.createdAt, reverse=True)
        return hyps[:limit]

    def get_hypotheses_by_experiment(self, experiment_id: str) -> List[Hypothesis]:
        hypothesis_ids = self.experiment_hypotheses.get(experiment_id, set())
        return [self.hypotheses[hid] for hid in hypothesis_ids if hid in self.hypotheses]

    def create_hypothesis(self, data: HypothesisCreate) -> Hypothesis:
        hypothesis_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        hypothesis = Hypothesis(
            id=hypothesis_id,
            projectId=data.projectId,
            title=data.title,
            description=data.description,
            author=data.author,
            status=data.status,
            targetMetrics=data.targetMetrics,
            baseline=data.baseline,
            createdAt=now,
            updatedAt=now,
        )
        self.hypotheses[hypothesis_id] = hypothesis
        self._update_project_counts()
        return hypothesis

    def update_hypothesis(self, hypothesis_id: str, data: HypothesisUpdate) -> Optional[Hypothesis]:
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None
        update_data = data.model_dump(exclude_unset=True)
        update_data["updatedAt"] = datetime.now().isoformat()
        updated = hypothesis.model_copy(update=update_data)
        self.hypotheses[hypothesis_id] = updated
        return updated

    def delete_hypothesis(self, hypothesis_id: str) -> bool:
        if hypothesis_id not in self.hypotheses:
            return False
        del self.hypotheses[hypothesis_id]
        self._update_project_counts()
        return True

    def get_metrics_by_experiment(self, experiment_id: str) -> List[Metric]:
        metrics = [m for m in self.metrics.values() if m.experimentId == experiment_id]
        return sorted(metrics, key=lambda m: m.step, reverse=True)

    def create_metric(self, data: MetricCreate) -> Metric:
        metric_id = str(uuid.uuid4())
        metric = Metric(
            id=metric_id,
            experimentId=data.experimentId,
            name=data.name,
            value=data.value,
            step=data.step,
            direction=data.direction,
            createdAt=datetime.now().isoformat(),
        )
        self.metrics[metric_id] = metric
        return metric

    def get_aggregated_metrics_for_project(self, project_id: str) -> Dict[str, Dict[str, Optional[float]]]:
        project = self.projects.get(project_id)
        if not project:
            return {}

        experiments = self.get_experiments_by_project(project_id)
        result: Dict[str, Dict[str, Optional[float]]] = {}

        for experiment in experiments:
            exp_metrics = self.get_metrics_by_experiment(experiment.id)
            metric_values: Dict[str, Optional[float]] = {}

            for project_metric in project.metrics:
                matching = [m for m in exp_metrics if m.name == project_metric.name]
                if not matching:
                    metric_values[project_metric.name] = None
                else:
                    if project_metric.aggregation == MetricAggregation.LAST:
                        metric_values[project_metric.name] = max(matching, key=lambda m: m.step).value
                    elif project_metric.aggregation == MetricAggregation.BEST:
                        if project_metric.direction == MetricDirection.MAXIMIZE:
                            metric_values[project_metric.name] = max(m.value for m in matching)
                        else:
                            metric_values[project_metric.name] = min(m.value for m in matching)
                    else:
                        metric_values[project_metric.name] = sum(m.value for m in matching) / len(matching)

            result[experiment.id] = metric_values

        return result

    def get_dashboard_stats(self) -> DashboardStats:
        experiments = list(self.experiments.values())
        hypotheses = list(self.hypotheses.values())

        return DashboardStats(
            totalProjects=len(self.projects),
            totalExperiments=len(experiments),
            runningExperiments=len([e for e in experiments if e.status == ExperimentStatus.RUNNING]),
            completedExperiments=len([e for e in experiments if e.status == ExperimentStatus.COMPLETE]),
            failedExperiments=len([e for e in experiments if e.status == ExperimentStatus.FAILED]),
            totalHypotheses=len(hypotheses),
            supportedHypotheses=len([h for h in hypotheses if h.status == HypothesisStatus.SUPPORTED]),
            refutedHypotheses=len([h for h in hypotheses if h.status == HypothesisStatus.REFUTED]),
        )


storage = MemStorage()
