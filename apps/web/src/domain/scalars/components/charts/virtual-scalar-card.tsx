"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

// One observer per scroll container/overscan size, shared by every card on the page.
const observers = new WeakMap<Element, Map<number, { observer: IntersectionObserver; listeners: Map<Element, (visible: boolean) => void> }>>();

export function VirtualScalarCard({ name, height, width, onVisibilityChange, children }: {
  name: string;
  height: number;
  width: number;
  onVisibilityChange?: (name: string, visible: boolean) => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const element = ref.current!;
    const root = element.closest("[data-scalar-scroll-root]") ?? document.documentElement;
    let sizes = observers.get(root);
    if (!sizes) { sizes = new Map(); observers.set(root, sizes); }
    let shared = sizes.get(height);
    if (!shared) {
      const listeners = new Map<Element, (visible: boolean) => void>();
      const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) listeners.get(entry.target)?.(entry.isIntersecting);
      }, { root: root === document.documentElement ? null : root, rootMargin: `${height}px 0px` });
      shared = { observer, listeners };
      sizes.set(height, shared);
    }
    shared.listeners.set(element, setVisible);
    shared.observer.observe(element);
    return () => {
      shared.listeners.delete(element);
      shared.observer.unobserve(element);
      if (shared.listeners.size === 0) { shared.observer.disconnect(); sizes.delete(height); }
    };
  }, [height]);
  useEffect(() => {
    onVisibilityChange?.(name, visible);
    return () => onVisibilityChange?.(name, false);
  }, [name, visible, onVisibilityChange]);
  return (
    <div ref={ref} style={{ height, width }} data-scalar-placeholder={name}>
      {visible ? children : <div className="h-full rounded-lg border p-3 text-sm text-muted-foreground" aria-label={`${name}: scroll to load`}>{name}</div>}
    </div>
  );
}
