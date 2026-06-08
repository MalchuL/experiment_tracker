export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

export type HparamsDocument = Record<string, JsonValue>;

export interface ExperimentHparams {
  experimentId: string;
  type: "hparams";
  hparams: HparamsDocument | null;
  dataId: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}
