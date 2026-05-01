"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  BookOpen,
  Check,
  CircleHelp,
  Share2,
  Star,
  ThumbsDown,
  ThumbsUp,
  Video,
  X,
} from "lucide-react";
import { getCachedVerdict, getCachedLocalVideoUrl, resolveApiUrl } from "../../lib/api";
import type { AnalyzeResponse, Verdict as VerdictType } from "../../lib/types";
import { VERDICT_COLOR, VERDICT_LABEL } from "../../lib/types";

const clampPercent = (value: unknown, fallback: number) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(0, Math.min(100, number));
};

export default function Verdict() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [showAdjudicators, setShowAdjudicators] = useState(false);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [helpfulVote, setHelpfulVote] = useState<"yes" | "no" | null>(null);
  const [shareStatus, setShareStatus] = useState("");
  const [ratingValues, setRatingValues] = useState<Record<string, number>>({
    Consistency: 0,
    "Game Awareness": 0,
    Communication: 0,
    Fairness: 0,
  });
  const [ratingSaved, setRatingSaved] = useState(false);
  const [localVideoUrl, setLocalVideoUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const cached = getCachedVerdict(id);
    if (cached) setData(cached);
    const localUrl = getCachedLocalVideoUrl(id);
    if (localUrl) setLocalVideoUrl(localUrl);
  }, [id]);

  // Empty state — clip ID is unknown or sessionStorage was cleared
  if (!data) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-12 border-2 border-black/5 transform -rotate-1">
          <CircleHelp className="mx-auto mb-4 h-16 w-16 text-[#F6B40F]" strokeWidth={2.5} />
          <h1 className="font-marker text-3xl mb-4">No verdict found</h1>
          <p className="text-gray-600 mb-6">
            This clip hasn't been analyzed in this session. Upload a video to get a fresh verdict.
          </p>
          <button
            onClick={() => router.push("/upload")}
            className="bg-black text-white px-6 py-3 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Analyze a clip →
          </button>
        </div>
      </div>
    );
  }

  const v = data.verdict;
  const verdictKey: VerdictType = v.verdict;
  const banner = {
    label: VERDICT_LABEL[verdictKey],
    color: VERDICT_COLOR[verdictKey],
  };
  const confidencePct = Math.round(v.confidence * 100);
  const clipSrc = data.clip_url ? resolveApiUrl(data.clip_url) : localVideoUrl;
  const keyMomentFrameSrc = data.key_moment?.frame_url
    ? resolveApiUrl(data.key_moment.frame_url)
    : null;
  const impactZone = v.perception.impact_zone || {
    x_percent: 50,
    y_percent: 50,
    radius_percent: 14,
    label: "Estimated impact zone",
  };
  const impactX = clampPercent(impactZone.x_percent, 50);
  const impactY = clampPercent(impactZone.y_percent, 50);
  const impactRadius = Math.max(5, Math.min(24, clampPercent(impactZone.radius_percent, 14)));
  const reviewChecklist = [
    {
      label: "Contact identified",
      value: v.perception.contact_detected,
      detail: v.perception.contact_detected ? v.perception.contact_location : "No contact detected",
    },
    {
      label: "Ball visible",
      value: v.perception.ball_visible,
      detail: v.perception.ball_state,
    },
    {
      label: "Camera usable",
      value: !["poor", "obstructed"].includes(v.perception.visual_quality),
      detail: v.perception.visual_quality,
    },
    {
      label: "Court zone known",
      value: Boolean(
        v.perception.court_geometry?.key_zone &&
          v.perception.court_geometry.key_zone !== "backcourt_or_unclear",
      ),
      detail: v.perception.court_geometry?.key_zone?.replace(/_/g, " ") || "unclear",
    },
    {
      label: "Defender status",
      value: v.perception.defender_status?.legal_guarding_position !== "unclear",
      detail:
        v.perception.defender_status?.legal_guarding_position?.replace(/_/g, " ") ||
        "unclear",
    },
    {
      label: "Rule cited",
      value: Boolean(v.cited_rule?.rule_id),
      detail: v.cited_rule?.rule_id || "No rule cited",
    },
    {
      label: "Agents agree",
      value: v.adjudicator_a.verdict === v.adjudicator_b.verdict,
      detail:
        v.adjudicator_a.verdict === v.adjudicator_b.verdict
          ? VERDICT_LABEL[v.adjudicator_a.verdict]
          : "Split decision",
    },
  ];

  const handleHelpfulVote = (vote: "yes" | "no") => {
    setHelpfulVote(vote);
    localStorage.setItem(`refcheck:helpful:${id}`, vote);
  };

  const handleShare = async () => {
    const url = window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({
          title: "RefCheck AI verdict",
          text: `${banner.label} · ${confidencePct}% confidence`,
          url,
        });
        setShareStatus("Shared");
        return;
      }
      await navigator.clipboard.writeText(url);
      setShareStatus("Link copied");
    } catch {
      setShareStatus("Share canceled");
    }
  };

  const handleSubmitRating = () => {
    localStorage.setItem(
      `refcheck:rating:${id}`,
      JSON.stringify({
        clip_id: id,
        ratings: ratingValues,
        submitted_at: new Date().toISOString(),
      }),
    );
    setRatingSaved(true);
    setShowRatingModal(false);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      {/* Verdict Banner */}
      <div
        className="rounded-xl shadow-[8px_8px_0_0_rgba(0,0,0,0.2)] p-8 mb-8 border-2 border-black/10 transform -rotate-1 hover:rotate-0 transition-transform"
        style={{ backgroundColor: banner.color }}
      >
        <div className="flex items-center justify-between text-white">
          <div className="flex-1">
            <div className="font-marker text-6xl mb-2">{banner.label}</div>
            <div className="font-mono text-sm opacity-90">
              Basketball · processed in {v.processing_time_seconds.toFixed(1)}s
            </div>
          </div>
          <div className="text-right">
            <div className="font-mono text-5xl">{confidencePct}%</div>
            <div className="text-sm opacity-90">CONFIDENCE</div>
          </div>
        </div>
      </div>

      {/* Video Player */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-8 border-2 border-black/5">
        <div className="aspect-video rounded-lg mb-4 overflow-hidden bg-black relative">
          {clipSrc ? (
            <video
              src={clipSrc}
              controls
              playsInline
              preload="metadata"
              className="h-full w-full object-contain bg-black"
            />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center relative">
              <div className="absolute inset-0 bg-black/20"></div>
              <div className="relative z-10 text-center">
                <Video className="mx-auto mb-3 h-20 w-20 text-white/80" strokeWidth={1.8} />
                <p className="text-gray-600">Clip playback unavailable</p>
              </div>
            </div>
          )}
          <div className="absolute left-3 top-3 bg-black/70 text-white text-xs font-mono px-2 py-1 rounded">
            REVIEW CLIP
          </div>
        </div>
        {v.perception.moment_of_interest_seconds !== null && (
          <div className="h-2 bg-gray-200 rounded-full relative">
            <div
              className="absolute top-0 bottom-0 w-1 rounded-full"
              style={{
                left: `${Math.min(95, v.perception.moment_of_interest_seconds * 10)}%`,
                backgroundColor: banner.color,
              }}
            ></div>
            <div
              className="absolute -top-8 text-white text-xs px-2 py-1 rounded whitespace-nowrap"
              style={{
                left: `${Math.min(85, v.perception.moment_of_interest_seconds * 10)}%`,
                backgroundColor: banner.color,
              }}
            >
              ← Moment of call (~{v.perception.moment_of_interest_seconds.toFixed(1)}s)
            </div>
          </div>
        )}
      </div>

      {/* Key Moment Frame */}
      {data.key_moment && (
        <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-6 border-2 border-black/5 transform -rotate-1">
          <div className="flex flex-col md:flex-row gap-6">
            <div className="md:w-1/2">
              <div className="aspect-video rounded-lg overflow-hidden bg-black relative">
                {keyMomentFrameSrc ? (
                  <img
                    src={keyMomentFrameSrc}
                    alt="Frame closest to the call impact"
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <div className="h-full w-full bg-gray-100 flex items-center justify-center text-gray-500">
                    Frame unavailable
                  </div>
                )}
                <div
                  className="absolute left-3 top-3 text-white text-xs font-mono px-2 py-1 rounded"
                  style={{ backgroundColor: banner.color }}
                >
                  FRAME {data.key_moment.frame_number}
                </div>
                <div
                  className="absolute rounded-full border-4 border-[#F6B40F] bg-[#F6B40F]/10 shadow-[0_0_0_6px_rgba(246,180,15,0.22)] animate-pulse"
                  style={{
                    left: `${impactX}%`,
                    top: `${impactY}%`,
                    width: `${impactRadius * 2}%`,
                    aspectRatio: "1 / 1",
                    transform: "translate(-50%, -50%)",
                  }}
                  aria-label={impactZone.label}
                />
                <div
                  className="absolute rounded-full border-2 border-white/90"
                  style={{
                    left: `${impactX}%`,
                    top: `${impactY}%`,
                    width: `${Math.max(3, impactRadius * 0.45)}%`,
                    aspectRatio: "1 / 1",
                    transform: "translate(-50%, -50%)",
                  }}
                />
              </div>
            </div>
            <div className="md:w-1/2">
              <div className="font-mono text-xs opacity-60 mb-2">
                KEY MOMENT
                {data.key_moment.approximate_seconds !== null &&
                  ` · ~${Number(data.key_moment.approximate_seconds).toFixed(1)}s`}
              </div>
              <h2 className="font-marker text-3xl mb-3">
                Impact Zone
              </h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                {data.key_moment.explanation}
              </p>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-[#FFF9E6] rounded-lg p-3 col-span-2 border-l-4 border-[#F6B40F]">
                  <div className="font-mono text-[11px] opacity-50 mb-1">AGENT MARKER</div>
                  <div>{impactZone.label}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="font-mono text-[11px] opacity-50 mb-1">CONTACT</div>
                  <div>{v.perception.contact_detected ? v.perception.contact_location : "none detected"}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="font-mono text-[11px] opacity-50 mb-1">BALL STATE</div>
                  <div>{v.perception.ball_state}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="font-mono text-[11px] opacity-50 mb-1">QUALITY</div>
                  <div>{v.perception.visual_quality}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="font-mono text-[11px] opacity-50 mb-1">VISION CONF.</div>
                  <div>{Math.round(v.perception.perception_confidence * 100)}%</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Why? Reasoning */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-6 border-2 border-black/5 transform rotate-1">
        <h2 className="font-marker text-3xl mb-4">Why?</h2>
        <p className="leading-relaxed text-gray-700">{v.reasoning}</p>
      </div>

      {/* Review Checklist */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-6 border-2 border-black/5">
        <div className="flex items-center justify-between gap-4 mb-5">
          <h2 className="font-marker text-3xl">Ref Review Checklist</h2>
          <div className="font-mono text-xs rounded bg-black px-3 py-2 text-white">
            {reviewChecklist.filter((item) => item.value).length}/{reviewChecklist.length} checks
          </div>
        </div>
        <div className="grid md:grid-cols-7 gap-3">
          {reviewChecklist.map((item) => (
            <div
              key={item.label}
              className={`rounded-lg border-2 p-3 ${
                item.value
                  ? "border-[#2DBF4F]/30 bg-[#E5FFE5]"
                  : "border-[#E63946]/20 bg-[#FFE5E5]"
              }`}
            >
              <div className="mb-2 flex items-center gap-2 font-mono text-[11px]">
                {item.value ? (
                  <Check className="h-4 w-4 text-[#2DBF4F]" />
                ) : (
                  <X className="h-4 w-4 text-[#E63946]" />
                )}
                {item.label}
              </div>
              <p className="text-sm text-gray-700">{item.detail}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Rule Cited */}
      {v.cited_rule && (
        <div className="bg-[#FFF9E6] rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-6 border-l-8 border-[#F6B40F] transform -rotate-1">
          <div className="flex items-start gap-3 mb-3">
            <BookOpen className="h-8 w-8 text-[#F6B40F]" strokeWidth={2.4} />
            <div>
              <div className="font-mono text-xs opacity-60 mb-1">
                RULE CITED · PAGE {v.cited_rule.page_number}
              </div>
              <h3 className="text-xl mb-1">{v.cited_rule.rule_id}</h3>
              <div className="text-sm text-gray-600 mb-2">
                {v.cited_rule.section_title}
              </div>
            </div>
          </div>
          <div className="bg-white/60 rounded p-4 border-l-4 border-[#F6B40F]">
            <p className="text-sm italic leading-relaxed">"{v.cited_rule.text}"</p>
          </div>
        </div>
      )}

      {/* How We Decided */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] border-2 border-black/5 mb-6">
        <button
          onClick={() => setShowAdjudicators(!showAdjudicators)}
          className="w-full p-6 flex items-center justify-between hover:bg-gray-50 transition-colors rounded-xl"
        >
          <h2 className="font-marker text-3xl">How We Decided</h2>
          <span
            className="text-2xl transform transition-transform"
            style={{ transform: showAdjudicators ? "rotate(180deg)" : "rotate(0)" }}
          >
            ▼
          </span>
        </button>
        {showAdjudicators && (
          <div className="px-6 pb-6 space-y-4">
            <AdjudicatorPanel
              label="ADJUDICATOR A · CONSERVATIVE"
              tint="#E5F3FF"
              border="#3B82F6"
              adj={v.adjudicator_a}
            />
            <AdjudicatorPanel
              label="ADJUDICATOR B · SKEPTICAL"
              tint="#E5FFE5"
              border="#2DBF4F"
              adj={v.adjudicator_b}
            />
            <div className="bg-gray-100 rounded-lg p-4">
              <div className="font-mono text-xs mb-2 opacity-60">RECONCILIATION</div>
              <p className="text-sm">{v.reconciliation_note}</p>
            </div>
            <details className="text-xs font-mono">
              <summary className="cursor-pointer opacity-60 hover:opacity-100">
                What did the AI see?
              </summary>
              <pre className="mt-2 bg-gray-50 p-3 rounded overflow-auto text-[11px] leading-relaxed">
                {JSON.stringify(v.perception, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>

      {/* Feedback & Actions */}
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl shadow-[4px_4px_0_0_rgba(0,0,0,0.1)] p-6 border-2 border-black/5">
          <h3 className="mb-4">Was this analysis helpful?</h3>
          <div className="flex gap-3">
            <button
              onClick={() => handleHelpfulVote("yes")}
              className={`flex-1 text-white py-3 rounded-lg transition-colors ${
                helpfulVote === "yes" ? "bg-[#25a643] ring-4 ring-[#2DBF4F]/20" : "bg-[#2DBF4F] hover:bg-[#25a643]"
              }`}
            >
              <ThumbsUp className="mr-2 inline h-4 w-4" />
              {helpfulVote === "yes" ? "Marked helpful" : "Yes"}
            </button>
            <button
              onClick={() => handleHelpfulVote("no")}
              className={`flex-1 text-white py-3 rounded-lg transition-colors ${
                helpfulVote === "no" ? "bg-[#d1303c] ring-4 ring-[#E63946]/20" : "bg-[#E63946] hover:bg-[#d1303c]"
              }`}
            >
              <ThumbsDown className="mr-2 inline h-4 w-4" />
              {helpfulVote === "no" ? "Feedback saved" : "No"}
            </button>
          </div>
          {helpfulVote && (
            <p className="mt-3 text-xs font-mono text-gray-500">
              Thanks. Your feedback is saved for this session.
            </p>
          )}
        </div>
        <div className="bg-white rounded-xl shadow-[4px_4px_0_0_rgba(0,0,0,0.1)] p-6 border-2 border-black/5">
          <h3 className="mb-4">Rate the ref</h3>
          <button
            onClick={() => setShowRatingModal(true)}
            className="w-full bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Open rating →
          </button>
        </div>
      </div>

      {/* Share */}
      <div className="text-center">
        <button
          onClick={handleShare}
          className="bg-[#3B82F6] text-white px-8 py-4 rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.2)] hover:shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] transition-all transform rotate-1 hover:rotate-0"
        >
          <Share2 className="mr-2 inline h-5 w-5" />
          {shareStatus || "Share This Verdict"}
        </button>
      </div>

      {/* Rating Modal */}
      {showRatingModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-8 transform -rotate-1 shadow-[12px_12px_0_0_rgba(0,0,0,0.3)]">
            <h2 className="font-marker text-3xl mb-6">Rate the ref</h2>
            <div className="space-y-4 mb-6">
              {["Consistency", "Game Awareness", "Communication", "Fairness"].map(
                (dimension) => (
                  <div key={dimension}>
                    <div className="text-sm mb-2">{dimension}</div>
                    <div className="flex gap-2">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() =>
                            setRatingValues((prev) => ({ ...prev, [dimension]: star }))
                          }
                          className={`text-3xl hover:scale-110 transition-transform ${
                            star <= ratingValues[dimension] ? "" : "grayscale opacity-40"
                          }`}
                        >
                          <Star
                            className={`h-8 w-8 ${
                              star <= ratingValues[dimension]
                                ? "fill-[#F6B40F] text-[#F6B40F]"
                                : "text-gray-300"
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                  </div>
                ),
              )}
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowRatingModal(false)}
                className="flex-1 bg-gray-200 py-3 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitRating}
                className="flex-1 bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-colors"
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}
      {ratingSaved && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-black text-white px-5 py-3 rounded-lg shadow-lg font-mono text-sm z-50">
          Ref rating saved
        </div>
      )}
    </div>
  );
}

function AdjudicatorPanel({
  label,
  tint,
  border,
  adj,
}: {
  label: string;
  tint: string;
  border: string;
  adj: AnalyzeResponse["verdict"]["adjudicator_a"];
}) {
  const verdictLabel = VERDICT_LABEL[adj.verdict];
  const verdictColor = VERDICT_COLOR[adj.verdict];
  return (
    <div
      className="rounded-lg p-4 border-l-4"
      style={{ backgroundColor: tint, borderLeftColor: border }}
    >
      <div className="flex items-center justify-between mb-2 gap-2">
        <div className="font-mono text-sm">{label}</div>
        <div
          className="text-white px-3 py-1 rounded text-sm whitespace-nowrap"
          style={{ backgroundColor: verdictColor }}
        >
          {verdictLabel} · {Math.round(adj.confidence * 100)}%
        </div>
      </div>
      <p className="text-sm text-gray-700">{adj.reasoning}</p>
      {adj.flags.length > 0 && (
        <p className="mt-2 text-xs text-red-700 font-mono">
          <AlertTriangle className="mr-1 inline h-3 w-3" />
          {adj.flags.join(" · ")}
        </p>
      )}
    </div>
  );
}
