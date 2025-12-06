"use client";

import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";
import { Loader } from "./ai-elements/loader";
import { Shimmer } from "./ai-elements/shimmer";

const LOADING_MESSAGES = [
  "Thinking...",
  "Analyzing market data...",
  "Gathering data...",
  "Consulting macro analyst...",
  "Running technical analysis...",
  "Checking sentiment indicators...",
  "Synthesizing insights...",
  "Almost done...",
  "Preparing recommendations...",
] as const;

export type LoadingAnalysisProps = {
  className?: string;
  interval?: number;
};

export const CustomLoader = ({
  className,
  interval = 10000,
}: LoadingAnalysisProps) => {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length);
    }, interval);

    return () => clearInterval(timer);
  }, [interval]);

  return (
    <div className={cn("flex justify-start", className)}>
      <div className="bg-zinc-200 rounded-lg text-white border border-neutral-700 px-4 py-3 shadow-sm">
        <div className="flex items-center gap-3 font-mono">
          <Loader className="size-4" />
          <Shimmer className="text-sm" duration={1.5} spread={3}>
            {LOADING_MESSAGES[messageIndex]}
          </Shimmer>
        </div>
      </div>
    </div>
  );
};
