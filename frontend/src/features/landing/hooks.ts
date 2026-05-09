import { useEffect, useRef, useState } from "react";

export function useInView<T extends HTMLElement>(
  options?: IntersectionObserverInit,
): { ref: React.RefObject<T | null>; show: boolean } {
  const ref = useRef<T | null>(null);
  const [show, setShow] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setShow(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShow(true);
            io.disconnect();
            break;
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -10% 0px", ...options },
    );
    io.observe(node);
    return () => io.disconnect();
  }, [options]);
  return { ref, show };
}
