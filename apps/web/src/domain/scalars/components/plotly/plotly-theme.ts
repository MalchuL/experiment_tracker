"use client";

import { useEffect, useState } from "react";
import type { Layout } from "plotly.js";
import { useTheme } from "@/lib/providers";

const PLOTLY_MONO =
  "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace";

/** Resolve whether the document is currently in dark mode (incl. system preference). */
export function useIsDarkMode(): boolean {
  const { theme } = useTheme();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => {
      if (theme === "dark") {
        setIsDark(true);
        return;
      }
      if (theme === "light") {
        setIsDark(false);
        return;
      }
      setIsDark(media.matches);
    };
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [theme]);

  return isDark;
}

/** Base Plotly layout colors that follow the app light/dark theme. */
export function getPlotlyThemeLayout(isDark: boolean): Partial<Layout> {
  if (isDark) {
    return {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#8a8f98" },
      xaxis: {
        gridcolor: "rgba(255, 255, 255, 0.08)",
        linecolor: "#23252a",
        tickfont: { color: "#8a8f98", size: 10 },
        zerolinecolor: "#23252a",
      },
      yaxis: {
        gridcolor: "rgba(255, 255, 255, 0.08)",
        linecolor: "#23252a",
        tickfont: { color: "#8a8f98", size: 10 },
        zerolinecolor: "#23252a",
      },
      hoverlabel: {
        align: "left",
        namelength: -1,
        bgcolor: "#161718",
        bordercolor: "#23252a",
        font: {
          color: "#f7f8f8",
          family: PLOTLY_MONO,
        },
      },
    };
  }

  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    xaxis: {
      gridcolor: "rgba(128, 128, 128, 0.2)",
      tickfont: { size: 10 },
    },
    yaxis: {
      gridcolor: "rgba(128, 128, 128, 0.2)",
      tickfont: { size: 10 },
    },
    hoverlabel: {
      align: "left",
      namelength: -1,
      bgcolor: "rgba(255, 255, 255, 0.95)",
      bordercolor: "rgba(226, 232, 240, 0.9)",
      font: {
        color: "rgba(15, 23, 42, 0.95)",
        family: PLOTLY_MONO,
      },
    },
  };
}
