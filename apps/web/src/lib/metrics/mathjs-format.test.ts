import { describe, expect, it } from "vitest";
import { METRIC_FORMAT_OPTIONS, formatValue } from "@/lib/metrics/mathjs-metric-format";

type FormatSample = {
  label: string;
  value: number;
  /** If non-null, assert `formatValue(value)` equals this. */
  required?: string | null;
};

const SAMPLE_VALUES: FormatSample[] = [
  { label: "integer -1", value: -1, required: "-1" },
  { label: "integer 0", value: 0, required: "0" },
  { label: "integer 1", value: 1, required: "1" },
  { label: "integer 10", value: 10, required: "10" },
  { label: "integer -10", value: -10, required: "-10" },
  { label: "integer 100", value: 100, required: "100" },
  { label: "integer -100", value: -100, required: "-100" },
  { label: "integer 1e3", value: 1e3, required: "1000" },
  { label: "integer -1e3", value: -1e3, required: "-1000" },
  { label: "integer 1e4", value: 1e4, required: "10000" },
  { label: "integer -1e4", value: -1e4, required: "-10000" },
  { label: "integer 1e5", value: 1e5, required: "100000" },
  { label: "integer -1e5", value: -1e5, required: "-100000" },
  { label: "integer 1e6", value: 1e6, required: "1e+6" },
  { label: "integer 1e+6 +1", value: 1001011, required: "1.001011e+6" },
  { label: "integer -1e6", value: -1e6, required: "-1e+6" },
  { label: "integer 1e7", value: 1e7, required: "1e+7" },
  { label: "integer -1e7", value: -1e7, required: "-1e+7" },
  { label: "integer 1e8", value: 1e8, required: "1e+8" },
  { label: "integer -1e8", value: -1e8, required: "-1e+8" },
  { label: "integer 1e9", value: 1e9, required: "1e+9" },
  { label: "integer -1e9", value: -1e9, required: "-1e+9" },
  { label: "integer 1e10", value: 1e10, required: "1e+10" },
  { label: "integer -1e10", value: -1e10, required: "-1e+10" },
  { label: "integer 1e11", value: 1e11, required: "1e+11" },
  { label: "integer -1e11", value: -1e11, required: "-1e+11" },
  { label: "integer 1e12", value: 1e12, required: "1e+12" },
  { label: "integer -1e12", value: -1e12, required: "-1e+12" },

  { label: "float 1.0", value: 1.0, required: "1" },
  { label: "float 1.1", value: 1.1, required: "1.1" },
  { label: "small decimal", value: 0.05, required: "0.05" },
  {
    label: "long decimal",
    value: 0.012312312312312312,
    required: "0.01231231",
  },
  { label: "tiny", value: 1e-12, required: "1e-12" },
  { label: "very small", value: 1e-21, required: "1e-21" },
  { label: "smoke π", value: 3.14159, required: "3.14159" },
  { label: "smoke many digits", value: 0.000000812312312, required: "8.123123e-7" },
  { label: "small many digits", value: 0.0081234567891234, required: "0.008123457" },
];

/**
 * Exercises {@link formatValue} / {@link METRIC_FORMAT_OPTIONS} (shared with `MetricValueDisplayFormatter`).
 */
describe("mathjs format (metric display alignment)", () => {
  it("logs sample formatValue() strings to stdout for inspection", () => {
    // eslint-disable-next-line no-console -- intentional: this test is for visible output
    console.log("\n========== formatValue() samples ==========\n");
    // eslint-disable-next-line no-console
    console.log(`METRIC_FORMAT_OPTIONS: ${JSON.stringify(METRIC_FORMAT_OPTIONS)}\n`);

    for (const s of SAMPLE_VALUES) {
      const out = formatValue(s.value);
      expect(typeof out).toBe("string");
      if (s.required != null) {
        expect(out, s.label).toBe(s.required);
      }
      // eslint-disable-next-line no-console
      console.log(
        `  ${s.label.padEnd(42)}  value=${String(s.value).padEnd(26)}  =>  ${JSON.stringify(out)}`
      );
    }

    // eslint-disable-next-line no-console
    console.log("\n==========================================\n");

    expect(SAMPLE_VALUES.length).toBeGreaterThan(0);
  });

  it("formatValue(0) is 0 (including -0)", () => {
    expect(formatValue(0)).toBe("0");
    expect(formatValue(-0)).toBe("0");
  });
});
