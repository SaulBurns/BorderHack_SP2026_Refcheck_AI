"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { CircleDot, ThumbsDown, ThumbsUp } from "lucide-react";
import { getFeedItems, type FeedItem } from "../../lib/api";

const verdictStyles = {
  fair_call: { label: "FAIR CALL", color: "#2DBF4F" },
  bad_call: { label: "BAD CALL", color: "#E63946" },
  inconclusive: { label: "INCONCLUSIVE", color: "#F6B40F" },
};

const fallbackCall = {
  videoUrl: null as string | null,
  verdict: "BAD CALL",
  color: "#E63946",
  confidence: "89% CONFIDENCE",
  meta: "High School - Division 1 • State Championship • Q4 2:34",
  title: "Questionable Offensive Foul Call",
  description:
    "Questionable offensive foul called during crucial possession in the state championship finals. AI analysis suggests defensive player was still moving and had not established legal guarding position.",
  rule: "NFHS Rule 4-7-2: Blocking Foul vs. Charging",
  fairVotes: 142,
  badVotes: 891,
};

function callFromFeedItem(item: FeedItem) {
  const display =
    verdictStyles[item.verdict as keyof typeof verdictStyles] ||
    verdictStyles.inconclusive;
  const confidence =
    typeof item.confidence === "number"
      ? `${Math.round(item.confidence * 100)}% CONFIDENCE`
      : "AI REVIEW";

  return {
    videoUrl: item.video_url,
    verdict: display.label,
    color: display.color,
    confidence,
    meta: [
      item.level_of_play,
      item.league,
      item.referee_name ? `Ref: ${item.referee_name}` : null,
    ]
      .filter(Boolean)
      .join(" • "),
    title: item.original_call || item.call_type || "Uploaded Basketball Call",
    description:
      item.reasoning ||
      "This uploaded call was analyzed by RefCheck AI and saved from the live review database.",
    rule: item.rule_id ? `NBA rule cited: ${item.rule_id}` : "Rule cited by AI review",
    fairVotes: item.votes_fair || 0,
    badVotes: item.votes_bad || 0,
  };
}

export default function ControversialCall() {
  const [feedItems, setFeedItems] = useState<FeedItem[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    getFeedItems()
      .then((items) => setFeedItems(items))
      .finally(() => setIsLoaded(true));
  }, []);

  const featuredCall = useMemo(() => {
    const diegoCall = feedItems.find(
      (item) => item.referee_name?.trim().toLowerCase() === "diego martinez",
    );
    return diegoCall ? callFromFeedItem(diegoCall) : fallbackCall;
  }, [feedItems]);

  return (
    <section className="max-w-7xl mx-auto px-4 py-16 relative">
      <div className="flex items-center gap-4 mb-8">
        <h2 className="font-marker text-4xl transform rotate-1">
          Controversial Call of the Day
        </h2>
        <svg width="80" height="40" viewBox="0 0 80 40" className="hidden md:block">
          <path d="M 5 20 Q 20 10, 40 20 T 75 20" stroke="#E63946" strokeWidth="3" fill="none" strokeLinecap="round" />
          <polygon points="75,20 68,16 68,24" fill="#E63946" />
        </svg>
      </div>
      <div className="bg-white rounded-xl shadow-[8px_8px_0_0_rgba(0,0,0,0.15)] p-6 transform -rotate-1 hover:rotate-0 transition-transform border-2 border-black/5">
        <div className="bg-gradient-to-br from-gray-100 to-gray-200 aspect-video rounded-lg mb-6 flex items-center justify-center relative overflow-hidden">
          {featuredCall.videoUrl ? (
            <video
              src={featuredCall.videoUrl}
              controls
              playsInline
              preload="metadata"
              className="absolute inset-0 h-full w-full bg-black object-contain"
            />
          ) : (
            <>
              <div className="absolute inset-0 bg-black/10"></div>
              <div className="relative z-10 text-center">
                <CircleDot className="mx-auto mb-2 h-16 w-16 text-black/40" strokeWidth={1.8} />
                <span className="text-gray-600">
                  {isLoaded ? "Demo preview" : "Loading featured clip..."}
                </span>
              </div>
            </>
          )}
        </div>
        <div className="flex items-center justify-between mb-6">
          <div
            className="text-white px-6 py-2 rounded-md inline-block transform rotate-1 shadow-[3px_3px_0_0_rgba(0,0,0,0.2)]"
            style={{ backgroundColor: featuredCall.color }}
          >
            {featuredCall.verdict}
          </div>
          <div className="font-mono bg-black text-white px-4 py-2 rounded">{featuredCall.confidence}</div>
        </div>
        <div className="font-mono text-sm mb-2 opacity-60">
          {featuredCall.meta || "Uploaded Basketball Clip"}
        </div>
        <h3 className="text-xl mb-3">{featuredCall.title}</h3>
        <p className="text-gray-600 mb-6 leading-relaxed">
          {featuredCall.description}
        </p>
        <div className="border-l-4 border-[#F6B40F] pl-4 bg-[#FFF9E6] p-4 rounded transform -rotate-1">
          <p className="font-mono text-xs mb-2 opacity-70">RULE CITED</p>
          <p className="text-sm">{featuredCall.rule}</p>
        </div>
        <div className="mt-6 flex gap-4">
          <button className="flex-1 bg-[#2DBF4F] text-white py-3 rounded-lg hover:bg-[#25a643] transition-colors">
            <ThumbsUp className="mr-2 inline h-4 w-4" />
            Fair Call ({featuredCall.fairVotes})
          </button>
          <button className="flex-1 bg-[#E63946] text-white py-3 rounded-lg hover:bg-[#d1303c] transition-colors">
            <ThumbsDown className="mr-2 inline h-4 w-4" />
            Bad Call ({featuredCall.badVotes})
          </button>
        </div>
      </div>

      {/* See All Link */}
      <div className="text-center mt-8">
        <Link
          href="/feed"
          className="inline-block bg-black text-white px-8 py-3 rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.2)] hover:shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] transition-all transform rotate-1 hover:rotate-0"
        >
          See All Hot Takes →
        </Link>
      </div>
    </section>
  );
}
