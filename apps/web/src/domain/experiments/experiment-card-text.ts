/** Max length for experiment name/description on compact surfaces (kanban, table name cell). */
export const EXPERIMENT_CARD_TEXT_MAX_LENGTH = 100;

export type TruncatedExperimentCardText = {
  display: string;
  full: string;
  truncated: boolean;
};

export function truncateExperimentCardText(text: string): TruncatedExperimentCardText {
  const full = text;
  if (full.length <= EXPERIMENT_CARD_TEXT_MAX_LENGTH) {
    return { display: full, full, truncated: false };
  }
  return {
    display: `${full.slice(0, EXPERIMENT_CARD_TEXT_MAX_LENGTH)}…`,
    full,
    truncated: true,
  };
}
