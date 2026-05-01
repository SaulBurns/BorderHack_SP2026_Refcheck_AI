import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router";
import { getCachedVerdict } from "@/lib/api";
import type { AnalyzeResponse, Verdict as VerdictType } from "@/lib/types";
import { VERDICT_COLOR, VERDICT_LABEL } from "@/lib/types";

export default function Verdict() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [showAdjudicators, setShowAdjudicators] = useState(false);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [data, setData] = useState<AnalyzeResponse | null>(null);

  useEffect(() => {
    if (!id) return;
    const cached = getCachedVerdict(id);
    if (cached) setData(cached);
  }, [id]);

  // Empty state — clip ID is unknown or sessionStorage was cleared
  if (!data) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-12 border-2 border-black/5 transform -rotate-1">
          <div className="text-6xl mb-4">🤔</div>
          <h1 className="font-marker text-3xl mb-4">No verdict found</h1>
          <p className="text-gray-600 mb-6">
            This clip hasn't been analyzed in this session. Upload a video to get a fresh verdict.
          </p>
          <button
            onClick={() => navigate("/upload")}
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

      {/* Video Player placeholder */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-8 border-2 border-black/5">
        <div className="bg-gradient-to-br from-gray-100 to-gray-200 aspect-video rounded-lg mb-4 flex items-center justify-center relative">
          <div className="absolute inset-0 bg-black/20"></div>
          <div className="relative z-10 text-center">
            <div className="text-7xl mb-3">▶️</div>
            <p className="text-gray-600">Clip playback (coming soon)</p>
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

      {/* Why? Reasoning */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-6 border-2 border-black/5 transform rotate-1">
        <h2 className="font-marker text-3xl mb-4">Why?</h2>
        <p className="leading-relaxed text-gray-700">{v.reasoning}</p>
      </div>

      {/* Rule Cited */}
      {v.cited_rule && (
        <div className="bg-[#FFF9E6] rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-6 border-l-8 border-[#F6B40F] transform -rotate-1">
          <div className="flex items-start gap-3 mb-3">
            <div className="text-3xl">📖</div>
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
            <button className="flex-1 bg-[#2DBF4F] text-white py-3 rounded-lg hover:bg-[#25a643] transition-colors">
              👍 Yes
            </button>
            <button className="flex-1 bg-[#E63946] text-white py-3 rounded-lg hover:bg-[#d1303c] transition-colors">
              👎 No
            </button>
          </div>
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
        <button className="bg-[#3B82F6] text-white px-8 py-4 rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.2)] hover:shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] transition-all transform rotate-1 hover:rotate-0">
          Share This Verdict 📤
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
                          className="text-3xl hover:scale-110 transition-transform"
                        >
                          ⭐
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
              <button className="flex-1 bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-colors">
                Submit
              </button>
            </div>
          </div>
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
          ⚠ {adj.flags.join(" · ")}
        </p>
      )}
    </div>
  );
}
