"use client";

import type { ImpactZone, OverlayMarker } from "../../lib/overlay";

export interface OverlayLayers {
  impact: boolean;
  heatmap: boolean;
  offense: boolean;
  defender: boolean;
  ball: boolean;
  arrows: boolean;
}

interface ReasoningOverlayProps {
  markers: OverlayMarker[];
  impact: ImpactZone;
  /** Final verdict confidence, 0-1. Drives the heatmap intensity/spread. */
  confidence: number;
  verdictColor: string;
  layers: OverlayLayers;
}

const KIND_COLOR: Record<OverlayMarker["kind"], string> = {
  offense: "#3B82F6",
  defense: "#E63946",
  ball: "#F6B40F",
};

const clampPct = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, Number.isFinite(value) ? value : (min + max) / 2));

function markerVisible(kind: OverlayMarker["kind"], layers: OverlayLayers): boolean {
  if (kind === "offense") return layers.offense;
  if (kind === "defense") return layers.defender;
  return layers.ball;
}

export default function ReasoningOverlay({
  markers,
  impact,
  confidence,
  verdictColor,
  layers,
}: ReasoningOverlayProps) {
  const ix = clampPct(impact.x_percent, 4, 96);
  const iy = clampPct(impact.y_percent, 4, 96);
  const radius = clampPct(impact.radius_percent, 5, 24);
  // Confident verdicts glow tighter and brighter; low confidence spreads and fades.
  const heatSpread = 26 + (1 - confidence) * 22;
  const heatAlpha = 0.18 + confidence * 0.4;

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {layers.heatmap && (
        <div
          className="absolute inset-0"
          style={{
            background: `radial-gradient(circle at ${ix}% ${iy}%, ${verdictColor}${Math.round(
              heatAlpha * 255,
            )
              .toString(16)
              .padStart(2, "0")} 0%, transparent ${heatSpread}%)`,
          }}
          aria-hidden
        />
      )}

      {layers.impact && (
        <>
          <div
            className="absolute rounded-full border-4 border-[#F6B40F] bg-[#F6B40F]/10 shadow-[0_0_0_6px_rgba(246,180,15,0.22)] animate-pulse"
            style={{
              left: `${ix}%`,
              top: `${iy}%`,
              width: `${radius * 2}%`,
              aspectRatio: "1 / 1",
              transform: "translate(-50%, -50%)",
            }}
            aria-label={impact.label}
          />
          <div
            className="absolute rounded-full border-2 border-white/90"
            style={{
              left: `${ix}%`,
              top: `${iy}%`,
              width: `${Math.max(3, radius * 0.45)}%`,
              aspectRatio: "1 / 1",
              transform: "translate(-50%, -50%)",
            }}
          />
        </>
      )}

      {markers.map((marker) => {
        if (!markerVisible(marker.kind, layers)) return null;
        const color = KIND_COLOR[marker.kind];
        const size = marker.primary ? 18 : 13;
        return (
          <div key={marker.id}>
            {layers.arrows && marker.movement && (
              <div
                className="absolute"
                style={{
                  left: `${marker.x}%`,
                  top: `${marker.y}%`,
                  transform: `translate(-50%, -50%) rotate(${marker.movement.angleDeg}deg)`,
                }}
                aria-hidden
              >
                <svg width="52" height="16" viewBox="0 0 52 16" style={{ overflow: "visible" }}>
                  <defs>
                    <marker
                      id={`arrow-${marker.id}`}
                      markerWidth="6"
                      markerHeight="6"
                      refX="5"
                      refY="3"
                      orient="auto"
                    >
                      <path d="M0,0 L6,3 L0,6 Z" fill={color} />
                    </marker>
                  </defs>
                  <line
                    x1="18"
                    y1="8"
                    x2="46"
                    y2="8"
                    stroke={color}
                    strokeWidth="3"
                    markerEnd={`url(#arrow-${marker.id})`}
                    opacity="0.9"
                  />
                </svg>
              </div>
            )}
            <div
              className="absolute rounded-full border-2 border-white shadow"
              style={{
                left: `${marker.x}%`,
                top: `${marker.y}%`,
                width: size,
                height: size,
                backgroundColor: color,
                transform: "translate(-50%, -50%)",
                boxShadow: marker.primary ? `0 0 0 5px ${color}33` : undefined,
              }}
              aria-label={`${marker.label}: ${marker.sublabel}`}
            />
            <div
              className="absolute whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-mono text-white"
              style={{
                left: `${marker.x}%`,
                top: `calc(${marker.y}% + ${size / 2 + 4}px)`,
                transform: "translate(-50%, 0)",
                backgroundColor: `${color}E6`,
              }}
            >
              {marker.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
