"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

const GO_SHORTCUTS: Record<string, string> = {
  d: "/dashboard",
  l: "/listings",
  a: "/analytics",
  s: "/settings",
  b: "/billing",
};

export function KeyboardNav() {
  const router = useRouter();
  const pendingG = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      // Skip when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === "g" && !pendingG.current) {
        pendingG.current = true;
        timer.current = setTimeout(() => { pendingG.current = false; }, 500);
        return;
      }

      if (pendingG.current && GO_SHORTCUTS[e.key]) {
        e.preventDefault();
        pendingG.current = false;
        clearTimeout(timer.current);
        router.push(GO_SHORTCUTS[e.key]);
      }
    }

    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("keydown", handleKey);
      clearTimeout(timer.current);
    };
  }, [router]);

  return null;
}
