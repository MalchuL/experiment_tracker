import Image from "next/image";
import { cn } from "@/lib/utils";

export function AppLogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "relative block h-8 w-8 flex-shrink-0 overflow-hidden rounded-md",
        className,
      )}
    >
      <Image
        src="/logo.png"
        alt=""
        width={32}
        height={32}
        className="h-full w-full object-contain"
        priority
        unoptimized
      />
    </span>
  );
}
