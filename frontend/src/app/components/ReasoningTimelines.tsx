"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import type { KeyFrame, PossessionSegment, TimelineEvent } from "../../lib/overlay";

const EVENT_COLOR: Record<TimelineEvent["kind"], string> = {
  observation: "#3B82F6",
  moment: "#E63946",
  key: "#F6B40F",
};

// -- Possession timeline ----------------------------------------------------

interface PossessionTimelineProps {
  segments: PossessionSegment[];
  trackingConfidence: number | null | undefined;
  possessionSummary: string | null | undefined;
}

export function PossessionTimeline({
  segments,
  trackingConfidence,
  possessionSummary,
}: PossessionTimelineProps) {
  const confPct =
    typeof trackingConfidence === "number" ? Math.round(trackingConfidence * 100) : null;
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <div className="font-mono text-[11px] uppercase tracking-wide opacity-60">
          Possession timeline
        </div>
        {confPct !== null && (
          <div className="font-mono text-[11px] opacity-60">tracking conf {confPct}%</div>
        )}
      </div>
      <div className="flex h-8 overflow-hidden rounded-md border-2 border-black/10">
        {segments.map((segment, index) => (
          <div
            key={`${segment.label}-${index}`}
            className="flex items-center justify-center text-[11px] font-mono text-white"
            style={{
              width: `${Math.max(0, (segment.end - segment.start) * 100)}%`,
              backgroundColor: index % 2 === 0 ? "#3B82F6" : "#6366F1",
            }}
            title={segment.label}
          >
            {segment.label}
          </div>
        ))}
      </div>
      {possessionSummary && (
        <div className="mt-1 font-mono text-[10px] opacity-50">
          Derived from AI possession read: {possessionSummary.replace(/_/g, " ")}
        </div>
      )}
    </div>
  );
}

// -- Event timeline ---------------------------------------------------------

interface EventTimelineProps {
  events: TimelineEvent[];
  activeSeconds: number | null;
  onSeek: (seconds: number) => void;
}

export function EventTimeline({ events, activeSeconds, onSeek }: EventTimelineProps) {
  if (events.length === 0) return null;
  const maxSeconds = Math.max(1, ...events.map((event) => event.seconds));
  return (
    <div>
      <div className="mb-3 font-mono text-[11px] uppercase tracking-wide opacity-60">
        Event timeline
      </div>
      <div className="relative h-10">
        <div className="absolute left-0 right-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-gray-200" />
        {events.map((event) => {
          const left = `${(event.seconds / maxSeconds) * 100}%`;
          const active =
            activeSeconds != null && Math.abs(activeSeconds - event.seconds) < 0.35;
          return (
            <button
              key={event.id}
              type="button"
              onClick={() => onSeek(event.seconds)}
              title={`${event.label} (~${event.seconds.toFixed(1)}s)`}
              className="group absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
              style={{ left }}
            >
              <span
                className="block rounded-full border-2 border-white shadow transition-transform group-hover:scale-125"
                style={{
                  width: active ? 18 : 12,
                  height: active ? 18 : 12,
                  backgroundColor: EVENT_COLOR[event.kind],
                }}
              />
            </button>
          );
        })}
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] opacity-50">
        <span>0.0s</span>
        <span>{maxSeconds.toFixed(1)}s</span>
      </div>
    </div>
  );
}

// -- Key frame navigation ---------------------------------------------------

interface KeyFrameNavProps {
  frames: KeyFrame[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

export function KeyFrameNav({ frames, activeIndex, onSelect }: KeyFrameNavProps) {
  if (frames.length === 0) return null;
  const go = (delta: number) => {
    const next = Math.max(0, Math.min(frames.length - 1, activeIndex + delta));
    onSelect(next);
  };
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <div className="font-mono text-[11px] uppercase tracking-wide opacity-60">
          Key frame navigation
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => go(-1)}
            disabled={activeIndex <= 0}
            className="rounded border-2 border-black/10 p-1 disabled:opacity-30 hover:bg-gray-50"
            aria-label="Previous key frame"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="font-mono text-xs tabular-nums">
            {activeIndex + 1}/{frames.length}
          </span>
          <button
            type="button"
            onClick={() => go(1)}
            disabled={activeIndex >= frames.length - 1}
            className="rounded border-2 border-black/10 p-1 disabled:opacity-30 hover:bg-gray-50"
            aria-label="Next key frame"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {frames.map((frame, index) => (
          <button
            key={frame.id}
            type="button"
            onClick={() => onSelect(index)}
            className={`shrink-0 rounded-lg border-2 px-3 py-2 text-left transition-colors ${
              index === activeIndex
                ? "border-black bg-black text-white"
                : "border-black/10 bg-white hover:bg-gray-50"
            }`}
            style={{ maxWidth: 190 }}
          >
            <div className="font-mono text-[10px] opacity-70">
              {frame.frameIndex != null ? `frame ${frame.frameIndex}` : "frame"} · ~
              {frame.seconds.toFixed(1)}s
            </div>
            <div className="truncate text-xs">{frame.label}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
