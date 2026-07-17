"use client";

import { useMemo, useRef, useState } from "react";
import { Layers, Video } from "lucide-react";
import type { AnalyzeResponse } from "../../lib/types";
import {
  buildEventTimeline,
  buildKeyFrames,
  buildOverlayMarkers,
  possessionSegments,
  type ImpactZone,
} from "../../lib/overlay";
import { overlayVocab } from "../../lib/sports";
import ReasoningOverlay, { type OverlayLayers } from "./ReasoningOverlay";
import { EventTimeline, KeyFrameNav, PossessionTimeline } from "./ReasoningTimelines";

interface AiReasoningPanelProps {
  data: AnalyzeResponse;
  clipSrc: string | null;
  fallbackImageSrc: string | null;
  verdictColor: string;
}

const DEFAULT_LAYERS: OverlayLayers = {
  impact: true,
  heatmap: true,
  offense: true,
  defender: true,
  ball: true,
  arrows: true,
};

const layerOptions = (objectLabel: string): Array<{ key: keyof OverlayLayers; label: string }> => [
  { key: "offense", label: "Offense" },
  { key: "defender", label: "Defender" },
  { key: "ball", label: objectLabel },
  { key: "arrows", label: "Movement" },
  { key: "impact", label: "Impact zone" },
  { key: "heatmap", label: "Confidence heat" },
];

export default function AiReasoningPanel({
  data,
  clipSrc,
  fallbackImageSrc,
  verdictColor,
}: AiReasoningPanelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [layers, setLayers] = useState<OverlayLayers>(DEFAULT_LAYERS);
  const [activeFrame, setActiveFrame] = useState(0);
  const [currentTime, setCurrentTime] = useState<number | null>(null);

  const perception = data.verdict.perception;
  const diagnostics = data.diagnostics;
  const confidence = data.verdict.confidence;
  const sport = perception.sport;
  const vocab = overlayVocab(sport);

  const impact: ImpactZone = perception.impact_zone ?? {
    x_percent: 50,
    y_percent: 50,
    radius_percent: 14,
    label: "Estimated impact zone",
  };

  const markers = useMemo(
    () => buildOverlayMarkers(perception, impact, sport),
    [perception, impact, sport],
  );
  const events = useMemo(
    () => buildEventTimeline(perception, data.key_moment?.approximate_seconds),
    [perception, data.key_moment?.approximate_seconds],
  );
  const keyFrames = useMemo(
    () => buildKeyFrames(perception, data.key_moment),
    [perception, data.key_moment],
  );
  // Possession comes from the sport-agnostic tracked-evidence diagnostics; the
  // basketball offensive_control_status (when present) is a graceful fallback for
  // the Claude-only path. Reading it by sport key avoids assuming basketball.
  const sportBlock = perception.sport_details?.[sport] as
    | { offensive_control_status?: string }
    | undefined;
  const offensiveControl =
    sportBlock?.offensive_control_status ?? perception.offensive_control_status;
  const segments = useMemo(
    () => possessionSegments(diagnostics?.possession_summary, offensiveControl),
    [diagnostics?.possession_summary, offensiveControl],
  );

  const seekTo = (seconds: number) => {
    const video = videoRef.current;
    if (video && Number.isFinite(seconds)) {
      video.currentTime = seconds;
      void video.play().catch(() => undefined);
    }
    setCurrentTime(seconds);
  };

  const selectFrame = (index: number) => {
    setActiveFrame(index);
    const frame = keyFrames[index];
    if (frame) seekTo(frame.seconds);
  };

  const toggleLayer = (key: keyof OverlayLayers) =>
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));

  const playerCount = diagnostics?.player_count ?? markers.filter((m) => m.kind !== "ball").length;
  const ballTracked = diagnostics?.ball_present ?? markers.some((m) => m.kind === "ball");
  const stats: Array<{ label: string; value: string }> = [
    { label: "Players tracked", value: String(playerCount) },
    { label: vocab.object, value: ballTracked ? "tracked" : "not seen" },
    {
      label: "Possession",
      value: (diagnostics?.possession_summary ?? offensiveControl ?? "unclear").replace(/_/g, " "),
    },
    {
      label: "Tracking",
      value:
        typeof diagnostics?.tracking_confidence === "number"
          ? `${Math.round(diagnostics.tracking_confidence * 100)}% conf`
          : diagnostics?.tracking_present
            ? "on"
            : "reasoning-only",
    },
  ];

  return (
    <div className="mb-8 rounded-xl border-2 border-black/5 bg-white p-6 shadow-[6px_6px_0_0_rgba(0,0,0,0.1)]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-marker text-3xl">AI Reasoning Overlay</h2>
        <div className="flex items-center gap-2 font-mono text-xs opacity-60">
          <Layers className="h-4 w-4" />
          Toggle layers
        </div>
      </div>

      {/* Layer toggles */}
      <div className="mb-4 flex flex-wrap gap-2">
        {layerOptions(vocab.object).map((option) => {
          const on = layers[option.key];
          return (
            <button
              key={option.key}
              type="button"
              onClick={() => toggleLayer(option.key)}
              className={`rounded-full border-2 px-3 py-1 font-mono text-xs transition-colors ${
                on ? "border-black bg-black text-white" : "border-black/15 bg-white text-gray-500"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {/* Video / frame with the overlay */}
      <div className="relative mb-4 aspect-video overflow-hidden rounded-lg bg-black">
        {clipSrc ? (
          <video
            ref={videoRef}
            src={clipSrc}
            controls
            playsInline
            preload="metadata"
            onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
            className="h-full w-full object-contain bg-black"
          />
        ) : fallbackImageSrc ? (
          <img
            src={fallbackImageSrc}
            alt="Key frame with AI reasoning overlay"
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 text-gray-500">
            <div className="text-center">
              <Video className="mx-auto mb-2 h-16 w-16 text-white/80" strokeWidth={1.8} />
              Clip playback unavailable — overlay shown on layout
            </div>
          </div>
        )}
        <ReasoningOverlay
          markers={markers}
          impact={impact}
          confidence={confidence}
          verdictColor={verdictColor}
          layers={layers}
        />
        <div className="pointer-events-none absolute left-3 top-3 rounded bg-black/70 px-2 py-1 font-mono text-xs text-white">
          REVIEW CLIP
        </div>
      </div>

      {/* Tracking stats */}
      <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-lg bg-gray-50 p-3">
            <div className="font-mono text-[10px] uppercase tracking-wide opacity-50">
              {stat.label}
            </div>
            <div className="text-sm capitalize">{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="space-y-5">
        <KeyFrameNav frames={keyFrames} activeIndex={activeFrame} onSelect={selectFrame} />
        <PossessionTimeline
          segments={segments}
          trackingConfidence={diagnostics?.tracking_confidence}
          possessionSummary={diagnostics?.possession_summary}
        />
        <EventTimeline events={events} activeSeconds={currentTime} onSeek={seekTo} />
      </div>

      <p className="mt-4 font-mono text-[10px] leading-relaxed opacity-40">
        Player and ball markers are placed by the AI's reasoning layout anchored on the detected
        impact zone; movement arrows, possession, and tracking stats come from the analysis. Exact
        pixel positions depend on the detector and are approximate.
      </p>
    </div>
  );
}
