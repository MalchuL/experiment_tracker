import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"

import { cn } from "@/lib/utils"

type SliderProps = React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root> & {
  /** Evenly spaced tick marks drawn on the track (one per discrete step). */
  markCount?: number
}

function SliderMarks({ markCount }: { markCount: number }) {
  if (markCount < 1) return null

  return (
    <>
      {Array.from({ length: markCount }, (_, index) => (
        <span
          key={index}
          aria-hidden
          className="pointer-events-none absolute top-1/2 z-0 h-1.5 w-px -translate-x-1/2 -translate-y-1/2 bg-muted-foreground/50"
          style={{
            left: markCount === 1 ? "50%" : `${(index / (markCount - 1)) * 100}%`,
          }}
        />
      ))}
    </>
  )
}

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  SliderProps
>(({ className, markCount, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn(
      "relative flex w-full touch-none select-none items-center",
      className
    )}
    {...props}
  >
    <SliderPrimitive.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-secondary">
      {markCount !== undefined ? <SliderMarks markCount={markCount} /> : null}
      <SliderPrimitive.Range className="absolute h-full bg-primary" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb className="relative z-10 block h-5 w-5 rounded-full border-2 border-primary bg-background ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50" />
  </SliderPrimitive.Root>
))
Slider.displayName = SliderPrimitive.Root.displayName

export { Slider }
