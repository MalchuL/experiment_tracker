import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Client-side unique id; falls back when `crypto.randomUUID` is unavailable (e.g. non-secure context). */
export function createClientId(): string {
  const randomUUID = globalThis.crypto?.randomUUID
  if (typeof randomUUID === "function") {
    return randomUUID.call(globalThis.crypto)
  }
  return `${Date.now()}-${Math.floor(Math.random() * 1_000_000)}`
}
