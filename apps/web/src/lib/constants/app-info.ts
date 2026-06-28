import packageJson from "../../../package.json";

export const WEB_APP_NAME = "Experiment Tracker";

export const WEB_APP_DESCRIPTION =
  "ML experiment tracking: projects, experiments, metrics, and file artifacts.";

export const WEB_APP_VERSION = packageJson.version;

export type AboutInfo = {
  service: string;
  version: string;
  description: string;
};
