const SDK_CONFIG_PATH = "~/.experiment-tracker/config.json";

export interface SdkInitConfigInput {
  baseUrl: string;
  apiPrefix: string;
  apiToken: string;
}

export function getSdkConfigPath(): string {
  return SDK_CONFIG_PATH;
}

export function buildSdkInitConfigObject({
  baseUrl,
  apiPrefix,
  apiToken,
}: SdkInitConfigInput): Record<string, string> {
  return {
    base_url: baseUrl,
    api_token: apiToken,
    api_prefix: apiPrefix,
  };
}

export function formatSdkInitConfigJson(input: SdkInitConfigInput): string {
  return JSON.stringify(buildSdkInitConfigObject(input), null, 2);
}

export function buildExperimentTrackerInitCommand(input: SdkInitConfigInput): string {
  const { base_url, api_prefix, api_token } = buildSdkInitConfigObject(input);
  return [
    "experiment-tracker init",
    `--base-url ${JSON.stringify(base_url)}`,
    `--api-prefix ${JSON.stringify(api_prefix)}`,
    `--api-token ${JSON.stringify(api_token)}`,
  ].join(" ");
}
