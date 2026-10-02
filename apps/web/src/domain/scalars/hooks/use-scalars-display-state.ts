import { useCallback, useState } from "react";
import type { SyncMode, ScalarHoverMode } from "../types";

export function useScalarsDisplayState() {
  const [syncMode, setSyncMode] = useState<SyncMode>("independent");
  const [hoverMode, setHoverMode] = useState<ScalarHoverMode>("compare");
  const [soloMode, setSoloMode] = useState(false);
  const [chosenExperimentId, setChosenExperimentId] = useState<string | null>(
    null,
  );
  const [experimentsSidebarOpen, setExperimentsSidebarOpen] = useState(true);
  const [settingsSidebarOpen, setSettingsSidebarOpen] = useState(true);
  const [cardHeight, setCardHeight] = useState(440);
  const [cardMinWidth, setCardMinWidth] = useState(640);
  const [hoverNameMaxLength, setHoverNameMaxLength] = useState(50);
  const toggleSettingsSidebar = () => setSettingsSidebarOpen((prev) => !prev);
  const toggleExperimentsSidebar = () =>
    setExperimentsSidebarOpen((prev) => !prev);

  const handleToggleSoloMode = () => {
    setSoloMode((prev) => {
      if (prev) {
        setChosenExperimentId(null);
      }
      return !prev;
    });
  };

  const handleSoloExperimentSelect = useCallback(
    (experimentId: string) => {
      if (soloMode && chosenExperimentId === experimentId) {
        setChosenExperimentId(null);
        return;
      }
      setChosenExperimentId(experimentId);
    },
    [soloMode, chosenExperimentId],
  );

  return {
    sync: { syncMode, setSyncMode },
    hover: {
      hoverMode,
      setHoverMode,
      hoverNameMaxLength,
      setHoverNameMaxLength,
    },
    solo: {
      soloMode,
      chosenExperimentId,
      handleToggleSoloMode,
      handleSoloExperimentSelect,
    },
    size: { cardHeight, setCardHeight, cardMinWidth, setCardMinWidth },
    sidebars: {
      experiments: {
        open: experimentsSidebarOpen,
        setOpen: setExperimentsSidebarOpen,
        toggle: toggleExperimentsSidebar,
      },
      settings: {
        open: settingsSidebarOpen,
        setOpen: setSettingsSidebarOpen,
        toggle: toggleSettingsSidebar,
      },
    },
  };
}
