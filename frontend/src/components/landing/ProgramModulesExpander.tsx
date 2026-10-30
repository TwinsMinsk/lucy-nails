"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";

interface ProgramModulesExpanderProps {
  total: number;
  /** Modules shown on phones before "show all"; desktop always shows every module. */
  visibleOnMobile: number;
  children: React.ReactNode;
}

/**
 * Eleven tall module cards pushed the price ~10 000 px down on phones.
 * Hidden cards stay in the markup (search engines and Ctrl+F still see them);
 * only their display is toggled below the md breakpoint.
 */
export function ProgramModulesExpander({ total, visibleOnMobile, children }: ProgramModulesExpanderProps) {
  const [expanded, setExpanded] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const expand = () => {
    setExpanded(true);
    // Keep keyboard and screen-reader users in place: the button disappears,
    // so focus moves to the first card that was revealed.
    requestAnimationFrame(() => {
      const next = rootRef.current?.querySelectorAll<HTMLElement>("article")[visibleOnMobile];
      if (!next) return;
      next.tabIndex = -1;
      next.focus({ preventScroll: true });
    });
  };

  return (
    <div ref={rootRef} data-collapsed={!expanded} className="group/program">
      {children}
      {!expanded && total > visibleOnMobile ? (
        <div className="mt-8 flex justify-center md:hidden">
          <Button
            type="button"
            variant="outline"
            className="h-12 rounded-full px-8 text-base font-semibold border-2 border-[#D4AF37]/40 bg-white"
            onClick={expand}
          >
            Показать все {total} модулей
          </Button>
        </div>
      ) : null}
    </div>
  );
}
