"use client";

import { useEffect, useMemo, useState } from "react";
import { Calendar, Check, CircleHelp, Flame, MessageCircle, Play, ThumbsDown, ThumbsUp, Trophy, X, Zap } from "lucide-react";
import { getFeedItems, type FeedItem } from "../../lib/api";

const clips = [
  {
    id: 1,
    game: "State Championship Finals",
    league: "High School - D1",
    quarter: "Q4 2:34",
    ref: "John Smith",
    call: "Offensive foul",
    aiVerdict: "BAD CALL",
    aiColor: "#E63946",
    fairPercent: 13,
    badPercent: 81,
    inconclusivePercent: 6,
    aiVsCrowd: "AGREE",
    comments: 247,
  },
  {
    id: 2,
    game: "Conference Finals",
    league: "NCAA Division II",
    quarter: "Q2 8:15",
    ref: "Sarah Williams",
    call: "Out of bounds",
    aiVerdict: "FAIR CALL",
    aiColor: "#2DBF4F",
    fairPercent: 81,
    badPercent: 14,
    inconclusivePercent: 5,
    aiVsCrowd: "AGREE",
    comments: 89,
  },
  {
    id: 3,
    game: "EuroLeague Playoff Game 3",
    league: "EuroLeague",
    quarter: "Q3 5:42",
    ref: "Marcus Chen",
    call: "Traveling",
    aiVerdict: "FAIR CALL",
    aiColor: "#2DBF4F",
    fairPercent: 28,
    badPercent: 67,
    inconclusivePercent: 5,
    aiVsCrowd: "DISAGREE",
    comments: 412,
  },
  {
    id: 4,
    game: "City League Finals",
    league: "Rec League",
    quarter: "Q1 11:03",
    ref: "Lisa Chen",
    call: "Blocking foul",
    aiVerdict: "INCONCLUSIVE",
    aiColor: "#F6B40F",
    fairPercent: 41,
    badPercent: 35,
    inconclusivePercent: 24,
    aiVsCrowd: "AGREE",
    comments: 156,
  },
  {
    id: 5,
    game: "AAU National Tournament",
    league: "Youth - U17",
    quarter: "Q4 0:14",
    ref: "David Brown",
    call: "Goaltending",
    aiVerdict: "BAD CALL",
    aiColor: "#E63946",
    fairPercent: 52,
    badPercent: 31,
    inconclusivePercent: 17,
    aiVsCrowd: "DISAGREE",
    comments: 634,
  },
];

type FeedClip = {
  id: number;
  clipId?: string;
  videoUrl?: string | null;
  isLiveUpload?: boolean;
  hasCrowdVotes?: boolean;
  game: string;
  league: string;
  quarter: string;
  ref: string;
  call: string;
  aiVerdict: string;
  aiColor: string;
  fairPercent: number;
  badPercent: number;
  inconclusivePercent: number;
  aiVsCrowd: string;
  comments: number;
  reasoning?: string | null;
  summary?: string | null;
  ruleId?: string | null;
  visualQuality?: string | null;
  confidence?: number | null;
  keyMomentSeconds?: number | null;
};

const verdictDisplay = {
  fair_call: { label: "FAIR CALL", color: "#2DBF4F" },
  bad_call: { label: "BAD CALL", color: "#E63946" },
  inconclusive: { label: "INCONCLUSIVE", color: "#F6B40F" },
};

const refSlug = (name: string) => name.toLowerCase().replace(/\s+/g, "-");

const formatCallType = (value: string | null | undefined) =>
  (value || "Reviewed play")
    .replace(/^possible_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const formatDateTime = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));

const percentagesFromVotes = (fair: number, bad: number, inconclusive: number) => {
  const total = fair + bad + inconclusive;
  if (total <= 0) {
    return { fairPercent: 0, badPercent: 0, inconclusivePercent: 0 };
  }
  const fairPercent = Math.round((fair / total) * 100);
  const badPercent = Math.round((bad / total) * 100);
  return {
    fairPercent,
    badPercent,
    inconclusivePercent: Math.max(0, 100 - fairPercent - badPercent),
  };
};

function realItemToClip(item: FeedItem): FeedClip {
  const fair = item.votes_fair || 0;
  const bad = item.votes_bad || 0;
  const unclear = item.votes_inconclusive || 0;
  const hasCrowdVotes = fair + bad + unclear > 0;
  const votePercentages = percentagesFromVotes(fair, bad, unclear);
  const display =
    verdictDisplay[item.verdict as keyof typeof verdictDisplay] ||
    verdictDisplay.inconclusive;
  const storedVerdict = item.verdict_json?.verdict;
  const perception = storedVerdict?.perception;
  const rule = storedVerdict?.cited_rule;
  const displayLeague = item.league || item.level_of_play || "Uploaded Basketball Clip";
  const displayLevel = item.level_of_play || item.league || "Basketball";

  return {
    id: Number.parseInt(item.clip_id.slice(0, 8), 16) || item.clip_id.length,
    clipId: item.clip_id,
    videoUrl: item.video_url,
    isLiveUpload: true,
    hasCrowdVotes,
    game: displayLeague,
    league: displayLevel,
    quarter: formatDateTime(item.created_at),
    ref: item.referee_name || "Unknown Ref",
    call: item.original_call || formatCallType(item.call_type || perception?.event_type),
    aiVerdict: display.label,
    aiColor: display.color,
    ...votePercentages,
    aiVsCrowd: hasCrowdVotes ? "LIVE" : "AWAITING CROWD",
    comments: fair + bad + unclear,
    reasoning: item.reasoning || storedVerdict?.reasoning,
    summary: perception?.summary || null,
    ruleId: item.rule_id || rule?.rule_id || null,
    visualQuality: perception?.visual_quality || null,
    confidence: item.confidence ?? storedVerdict?.confidence ?? null,
    keyMomentSeconds: perception?.moment_of_interest_seconds ?? null,
  };
}

export default function Feed() {
  const [filter, setFilter] = useState("all-time");
  const [visibleCount, setVisibleCount] = useState(3);
  const [selectedClipId, setSelectedClipId] = useState<number | null>(null);
  const [realFeedItems, setRealFeedItems] = useState<FeedItem[]>([]);
  const [feedLoaded, setFeedLoaded] = useState(false);
  const [votes, setVotes] = useState<
    Record<number, { fair: number; bad: number; inconclusive: number; userVote?: "fair" | "bad" | "inconclusive" }>
  >({});

  useEffect(() => {
    getFeedItems()
      .then((items) => setRealFeedItems(items))
      .finally(() => setFeedLoaded(true));
  }, []);

  const feedClips = useMemo<FeedClip[]>(() => {
    const realClips = realFeedItems.map(realItemToClip);
    return realClips.length > 0 ? [...realClips, ...clips] : clips;
  }, [realFeedItems]);

  const displayedClips = useMemo(() => {
    let next = feedClips;
    if (filter === "professional") {
      next = feedClips.filter((clip) => /EuroLeague|Conference/.test(clip.game) || /EuroLeague|Professional/.test(clip.league));
    } else if (filter === "college") {
      next = feedClips.filter((clip) => /NCAA|College/.test(clip.league));
    } else if (filter === "high-school") {
      next = feedClips.filter((clip) => /High School/.test(clip.league));
    } else if (filter === "disagreement") {
      next = [...feedClips].sort((a, b) => (a.aiVsCrowd === "DISAGREE" ? -1 : 1) - (b.aiVsCrowd === "DISAGREE" ? -1 : 1));
    } else if (filter === "today") {
      next = feedClips.slice(0, 2);
    } else if (filter === "week") {
      next = feedClips.slice(0, 4);
    }
    return next.slice(0, visibleCount);
  }, [feedClips, filter, visibleCount]);

  const getVoteTotals = (clip: FeedClip) => {
    const override = votes[clip.id];
    if (override) return override;
    return {
      fair: clip.fairPercent,
      bad: clip.badPercent,
      inconclusive: clip.inconclusivePercent,
    };
  };

  const handleVote = (clip: FeedClip, vote: "fair" | "bad" | "inconclusive") => {
    const current = getVoteTotals(clip);
    const previousVote = votes[clip.id]?.userVote;
    const next = {
      fair: current.fair,
      bad: current.bad,
      inconclusive: current.inconclusive,
      userVote: vote,
    };
    if (previousVote && previousVote !== vote) {
      next[previousVote] = Math.max(0, next[previousVote] - 4);
    }
    if (previousVote !== vote) {
      next[vote] = next[vote] + 4;
    }
    const total = next.fair + next.bad + next.inconclusive;
    setVotes((prev) => ({
      ...prev,
      [clip.id]: {
        fair: Math.round((next.fair / total) * 100),
        bad: Math.round((next.bad / total) * 100),
        inconclusive: Math.max(1, 100 - Math.round((next.fair / total) * 100) - Math.round((next.bad / total) * 100)),
        userVote: vote,
      },
    }));
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-16">
      <h1 className="font-marker text-6xl mb-3 text-center transform -rotate-1">
        HOT TAKES
      </h1>
      <p className="text-center text-gray-600 mb-12">
        {realFeedItems.length > 0
          ? "Recent uploaded calls plus demo debates"
          : "The most debated calls across the league"}
      </p>
      {!feedLoaded && (
        <div className="mb-6 bg-white border-2 border-black/5 rounded-lg p-4 text-sm font-mono text-gray-500">
          Loading live uploads...
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-8 border-2 border-black/5">
        <div className="flex flex-wrap gap-3">
          {[
            { id: 'today', label: 'Today', Icon: Calendar },
            { id: 'week', label: 'This Week', Icon: Flame },
            { id: 'all-time', label: 'All Time', Icon: Trophy },
            { id: 'professional', label: 'Professional', Icon: Trophy },
            { id: 'college', label: 'College', Icon: Trophy },
            { id: 'high-school', label: 'High School', Icon: Trophy },
            { id: 'disagreement', label: 'Most Disagreement', Icon: Zap },
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`
                px-4 py-2 rounded-lg border-2 text-sm transition-all transform hover:rotate-1
                ${filter === f.id
                  ? 'bg-black text-white border-black shadow-[3px_3px_0_0_rgba(0,0,0,0.2)]'
                  : 'bg-white border-black/10 hover:border-black/30'
                }
              `}
            >
              <f.Icon className="mr-2 inline h-4 w-4" />
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Feed */}
      <div className="space-y-6">
        {displayedClips.map((clip, idx) => {
          const voteTotals = getVoteTotals(clip);
          const userVote = votes[clip.id]?.userVote;
          return (
          <div
            key={clip.id}
            className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] overflow-hidden border-2 border-black/5 transform hover:scale-[1.01] transition-all"
            style={{ transform: `rotate(${idx % 2 === 0 ? '0.5deg' : '-0.5deg'})` }}
          >
            <div className="p-6">
              <div className="flex gap-6">
                {/* Video Thumbnail */}
                <button
                  onClick={() => setSelectedClipId(clip.id)}
                  className="bg-gradient-to-br from-gray-100 to-gray-200 w-64 h-36 rounded-lg flex items-center justify-center flex-shrink-0 relative group cursor-pointer overflow-hidden"
                  aria-label={`Preview ${clip.game}`}
                >
                  {clip.videoUrl ? (
                    <video
                      src={clip.videoUrl}
                      muted
                      playsInline
                      preload="metadata"
                      className="absolute inset-0 h-full w-full object-cover"
                    />
                  ) : (
                    <div className="absolute inset-0 bg-gradient-to-br from-gray-100 to-gray-300" />
                  )}
                  <div className="absolute inset-0 bg-black/25 group-hover:bg-black/35 transition-colors"></div>
                  <Play className="relative z-10 h-14 w-14 fill-white text-white transition-transform group-hover:scale-110" />
                  <span className="absolute bottom-2 left-2 bg-black/75 text-white text-xs font-mono px-2 py-1 rounded">
                    {clip.isLiveUpload ? "Uploaded Clip" : "Demo Preview"}
                  </span>
                </button>

                {/* Content */}
                <div className="flex-1">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-xl mb-1">{clip.game}</h3>
                      <div className="flex gap-3 text-sm text-gray-600 font-mono">
                        <span>{clip.league}</span>
                        <span>•</span>
                        <span>{clip.quarter}</span>
                        <span>•</span>
                        <span>{clip.call}</span>
                      </div>
                      <a
                        href={`/ref/${refSlug(clip.ref)}`}
                        className="text-sm text-blue-600 hover:underline mt-1 inline-block"
                      >
                        Ref: {clip.ref}
                      </a>
                    </div>

                    {/* AI Verdict Badge */}
                    <div
                      className="px-4 py-2 rounded-lg text-white text-sm transform rotate-1 shadow-[3px_3px_0_0_rgba(0,0,0,0.2)]"
                      style={{ backgroundColor: clip.aiColor }}
                    >
                      AI: {clip.aiVerdict}
                    </div>
                  </div>

                  {/* Crowd Verdict Bar */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between text-xs font-mono mb-2 opacity-60">
                      <span>CROWD VERDICT</span>
                      {clip.confidence !== null && clip.confidence !== undefined && (
                        <span>AI CONF. {Math.round(clip.confidence * 100)}%</span>
                      )}
                    </div>
                    {clip.hasCrowdVotes || votes[clip.id] ? (
                      <div className="flex h-8 rounded-lg overflow-hidden border-2 border-black/10">
                        <div
                          className="bg-[#2DBF4F] flex items-center justify-center text-white text-xs font-mono"
                          style={{ width: `${voteTotals.fair}%` }}
                        >
                          {voteTotals.fair > 10 && `Fair ${voteTotals.fair}%`}
                        </div>
                        <div
                          className="bg-[#E63946] flex items-center justify-center text-white text-xs font-mono"
                          style={{ width: `${voteTotals.bad}%` }}
                        >
                          {voteTotals.bad > 10 && `Bad ${voteTotals.bad}%`}
                        </div>
                        <div
                          className="bg-[#F6B40F] flex items-center justify-center text-white text-xs font-mono"
                          style={{ width: `${voteTotals.inconclusive}%` }}
                        >
                          {voteTotals.inconclusive > 10 && `? ${voteTotals.inconclusive}%`}
                        </div>
                      </div>
                    ) : (
                      <div className="h-8 rounded-lg border-2 border-dashed border-black/20 bg-gray-50 flex items-center justify-center text-xs font-mono text-gray-500">
                        No crowd votes yet
                      </div>
                    )}
                  </div>

                  {(clip.ruleId || clip.visualQuality || clip.keyMomentSeconds !== null) && (
                    <div className="mb-4 flex flex-wrap gap-2 text-xs font-mono">
                      {clip.ruleId && (
                        <span className="rounded bg-[#FFF9E6] px-2 py-1 text-[#8A5D00]">
                          Rule {clip.ruleId}
                        </span>
                      )}
                      {clip.visualQuality && (
                        <span className="rounded bg-gray-100 px-2 py-1 text-gray-600">
                          View {clip.visualQuality}
                        </span>
                      )}
                      {clip.keyMomentSeconds !== null && clip.keyMomentSeconds !== undefined && (
                        <span className="rounded bg-gray-100 px-2 py-1 text-gray-600">
                          Key moment ~{Number(clip.keyMomentSeconds).toFixed(1)}s
                        </span>
                      )}
                    </div>
                  )}

                  {/* AI vs Crowd Stamp */}
                  <div className="mb-4">
                    <div
                      className={`
                        inline-block px-4 py-2 rounded-lg border-3 transform -rotate-2 text-sm font-mono
                        ${clip.aiVsCrowd === 'AGREE'
                          ? 'bg-[#2DBF4F]/20 border-[#2DBF4F] text-[#2DBF4F]'
                          : clip.aiVsCrowd === 'AWAITING CROWD'
                          ? 'bg-[#F6B40F]/20 border-[#F6B40F] text-[#8A5D00]'
                          : 'bg-[#E63946]/20 border-[#E63946] text-[#E63946]'
                        }
                      `}
                      style={{ borderWidth: '3px' }}
                    >
                      AI vs CROWD: {clip.aiVsCrowd}
                      {clip.aiVsCrowd === 'AGREE' ? (
                        <Check className="ml-2 inline h-4 w-4" />
                      ) : clip.aiVsCrowd === 'AWAITING CROWD' ? (
                        <CircleHelp className="ml-2 inline h-4 w-4" />
                      ) : (
                        <X className="ml-2 inline h-4 w-4" />
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-3">
                    <div className="flex gap-2 flex-1">
                      <button
                        onClick={() => handleVote(clip, "fair")}
                        className={`flex-1 text-white py-2 px-3 rounded-lg transition-colors text-sm ${userVote === "fair" ? "bg-[#25a643] ring-4 ring-[#2DBF4F]/20" : "bg-[#2DBF4F] hover:bg-[#25a643]"}`}
                      >
                        <ThumbsUp className="mr-2 inline h-4 w-4" /> Fair
                      </button>
                      <button
                        onClick={() => handleVote(clip, "bad")}
                        className={`flex-1 text-white py-2 px-3 rounded-lg transition-colors text-sm ${userVote === "bad" ? "bg-[#d1303c] ring-4 ring-[#E63946]/20" : "bg-[#E63946] hover:bg-[#d1303c]"}`}
                      >
                        <ThumbsDown className="mr-2 inline h-4 w-4" /> Bad
                      </button>
                      <button
                        onClick={() => handleVote(clip, "inconclusive")}
                        className={`flex-1 text-white py-2 px-3 rounded-lg transition-colors text-sm ${userVote === "inconclusive" ? "bg-[#e0a20e] ring-4 ring-[#F6B40F]/20" : "bg-[#F6B40F] hover:bg-[#e0a20e]"}`}
                      >
                        <CircleHelp className="mr-2 inline h-4 w-4" /> Unclear
                      </button>
                    </div>
                    <button
                      onClick={() => setSelectedClipId(clip.id)}
                      className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors text-sm"
                    >
                      <MessageCircle className="h-4 w-4" /> {clip.comments}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )})}
      </div>

      {/* Load More */}
      <div className="text-center mt-12">
        <button
          onClick={() => setVisibleCount((count) => Math.min(feedClips.length, count + 2))}
          disabled={visibleCount >= feedClips.length}
          className="bg-black text-white px-8 py-4 rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.2)] hover:shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] transition-all transform rotate-1 hover:rotate-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {visibleCount >= feedClips.length ? "All Clips Loaded" : "Load More Clips ↓"}
        </button>
      </div>
      {selectedClipId !== null && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-[12px_12px_0_0_rgba(0,0,0,0.3)]">
            {(() => {
              const clip = feedClips.find((item) => item.id === selectedClipId);
              if (!clip) return null;
              return (
                <>
                  {clip.videoUrl ? (
                    <video
                      src={clip.videoUrl}
                      controls
                      playsInline
                      className="aspect-video w-full bg-black rounded-lg mb-4"
                    />
                  ) : (
                    <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-300 rounded-lg flex items-center justify-center mb-4">
                      <Play className="h-16 w-16 fill-black/60 text-black/60" />
                    </div>
                  )}
            <h2 className="font-marker text-3xl mb-2">
                    {clip.game}
            </h2>
            <p className="text-sm text-gray-600 mb-4">
                    {clip.summary ||
                      clip.reasoning ||
                      "Demo feed clips are community examples. Upload your own clip for real AI playback and analysis."}
            </p>
                  <div className="mb-4 grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="rounded bg-gray-50 p-2">
                      Verdict: {clip.aiVerdict}
                    </div>
                    <div className="rounded bg-gray-50 p-2">
                      {clip.confidence !== null && clip.confidence !== undefined
                        ? `Confidence: ${Math.round(clip.confidence * 100)}%`
                        : "Confidence: pending"}
                    </div>
                    <div className="rounded bg-gray-50 p-2">
                      {clip.ruleId ? `Rule: ${clip.ruleId}` : "Rule: not cited"}
                    </div>
                    <div className="rounded bg-gray-50 p-2">
                      {clip.visualQuality ? `View: ${clip.visualQuality}` : "View: unknown"}
                    </div>
                  </div>
                </>
              );
            })()}
            <div className="flex gap-3">
              <button
                onClick={() => setSelectedClipId(null)}
                className="flex-1 bg-gray-200 py-3 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Close
              </button>
              <a
                href="/upload"
                className="flex-1 bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-colors text-center"
              >
                Analyze a Clip
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
