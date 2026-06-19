import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"

import { cn } from "@/lib/utils"

/** Matches Radix `@radix-ui/react-slider` thumb width (`h-5 w-5`). */
const SLIDER_THUMB_SIZE_PX = 20

type SliderProps = React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root> & {
  /** Evenly spaced tick marks drawn on the track (one per discrete step). */
  markCount?: number
}

function linearScale(
  input: readonly [number, number],
  output: readonly [number, number],
) {
  return (value: number) => {
    if (input[0] === input[1] || output[0] === output[1]) return output[0]
    const ratio = (output[1] - output[0]) / (input[1] - input[0])
    return output[0] + ratio * (value - input[0])
  }
}

/** Same inset math Radix uses so tick centers match thumb centers. */
function getThumbInBoundsOffset(width: number, percent: number, direction = 1) {
  const halfWidth = width / 2
  const offset = linearScale([0, 50], [0, halfWidth])
  return (halfWidth - offset(percent) * direction) * direction
}

function getMarkLeftStyle(
  index: number,
  markCount: number,
  min: number,
  max: number,
  thumbWidth: number,
): React.CSSProperties {
  const value =
    markCount <= 1 ? min : min + (index / (markCount - 1)) * (max - min)
  const percent = max === min ? 0 : ((value - min) / (max - min)) * 100
  const offset = getThumbInBoundsOffset(thumbWidth, percent, 1)
  return { left: `calc(${percent}% + ${offset}px)` }
}

function SliderMarks({
  markCount,
  min,
  max,
}: {
  markCount: number
  min: number
  max: number
}) {
  if (markCount < 1) return null

  return (
    <>
      {Array.from({ length: markCount }, (_, index) => (
        <span
          key={index}
          aria-hidden
          className="pointer-events-none absolute top-1/2 z-[1] h-2 w-px -translate-x-1/2 -translate-y-1/2 bg-background shadow-[0_0_0_1px_hsl(var(--foreground)/0.4)]"
          style={getMarkLeftStyle(index, markCount, min, max, SLIDER_THUMB_SIZE_PX)}
        />
      ))}
    </>
  )
}

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  SliderProps
>(({ className, markCount, min = 0, max = 100, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    min={min}
    max={max}
    className={cn(
      "relative flex w-full touch-none select-none items-center",
      className
    )}
    {...props}
  >
    <SliderPrimitive.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-secondary">
      <SliderPrimitive.Range className="absolute h-full bg-primary" />
    </SliderPrimitive.Track>
    {markCount !== undefined ? (
      <SliderMarks markCount={markCount} min={min} max={max} />
    ) : null}
    <SliderPrimitive.Thumb className="relative z-10 block h-5 w-5 rounded-full border-2 border-primary bg-background ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50" />
  </SliderPrimitive.Root>
))
Slider.displayName = SliderPrimitive.Root.displayName

export { Slider }
