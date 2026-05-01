import { useState } from "react";

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

export default function Feed() {
  const [filter, setFilter] = useState("all-time");

  return (
    <div className="max-w-5xl mx-auto px-4 py-16">
      <h1 className="font-marker text-6xl mb-3 text-center transform -rotate-1">
        HOT TAKES
      </h1>
      <p className="text-center text-gray-600 mb-12">
        The most debated calls across the league
      </p>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-8 border-2 border-black/5">
        <div className="flex flex-wrap gap-3">
          {[
            { id: 'today', label: 'Today', emoji: '📅' },
            { id: 'week', label: 'This Week', emoji: '📆' },
            { id: 'all-time', label: 'All Time', emoji: '🏆' },
            { id: 'professional', label: 'Professional', emoji: '🏆' },
            { id: 'college', label: 'College', emoji: '🎓' },
            { id: 'high-school', label: 'High School', emoji: '🏫' },
            { id: 'disagreement', label: 'Most Disagreement', emoji: '⚡' },
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
              {f.emoji} {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Feed */}
      <div className="space-y-6">
        {clips.map((clip, idx) => (
          <div
            key={clip.id}
            className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] overflow-hidden border-2 border-black/5 transform hover:scale-[1.01] transition-all"
            style={{ transform: `rotate(${idx % 2 === 0 ? '0.5deg' : '-0.5deg'})` }}
          >
            <div className="p-6">
              <div className="flex gap-6">
                {/* Video Thumbnail */}
                <div className="bg-gradient-to-br from-gray-100 to-gray-200 w-64 h-36 rounded-lg flex items-center justify-center flex-shrink-0 relative group cursor-pointer">
                  <div className="absolute inset-0 bg-black/20 group-hover:bg-black/30 transition-colors"></div>
                  <div className="relative z-10 text-5xl group-hover:scale-110 transition-transform">
                    ▶️
                  </div>
                </div>

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
                        href={`/ref/${clip.ref.toLowerCase().replace(' ', '-')}`}
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
                    <div className="text-xs font-mono mb-2 opacity-60">CROWD VERDICT</div>
                    <div className="flex h-8 rounded-lg overflow-hidden border-2 border-black/10">
                      <div
                        className="bg-[#2DBF4F] flex items-center justify-center text-white text-xs font-mono"
                        style={{ width: `${clip.fairPercent}%` }}
                      >
                        {clip.fairPercent > 10 && `Fair ${clip.fairPercent}%`}
                      </div>
                      <div
                        className="bg-[#E63946] flex items-center justify-center text-white text-xs font-mono"
                        style={{ width: `${clip.badPercent}%` }}
                      >
                        {clip.badPercent > 10 && `Bad ${clip.badPercent}%`}
                      </div>
                      <div
                        className="bg-[#F6B40F] flex items-center justify-center text-white text-xs font-mono"
                        style={{ width: `${clip.inconclusivePercent}%` }}
                      >
                        {clip.inconclusivePercent > 10 && `? ${clip.inconclusivePercent}%`}
                      </div>
                    </div>
                  </div>

                  {/* AI vs Crowd Stamp */}
                  <div className="mb-4">
                    <div
                      className={`
                        inline-block px-4 py-2 rounded-lg border-3 transform -rotate-2 text-sm font-mono
                        ${clip.aiVsCrowd === 'AGREE'
                          ? 'bg-[#2DBF4F]/20 border-[#2DBF4F] text-[#2DBF4F]'
                          : 'bg-[#E63946]/20 border-[#E63946] text-[#E63946]'
                        }
                      `}
                      style={{ borderWidth: '3px' }}
                    >
                      AI vs CROWD: {clip.aiVsCrowd} {clip.aiVsCrowd === 'AGREE' ? '✓' : '✗'}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-3">
                    <div className="flex gap-2 flex-1">
                      <button className="flex-1 bg-[#2DBF4F] text-white py-2 px-3 rounded-lg hover:bg-[#25a643] transition-colors text-sm">
                        👍 Fair
                      </button>
                      <button className="flex-1 bg-[#E63946] text-white py-2 px-3 rounded-lg hover:bg-[#d1303c] transition-colors text-sm">
                        👎 Bad
                      </button>
                      <button className="flex-1 bg-[#F6B40F] text-white py-2 px-3 rounded-lg hover:bg-[#e0a20e] transition-colors text-sm">
                        ❓ Unclear
                      </button>
                    </div>
                    <button className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors text-sm">
                      💬 {clip.comments}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Load More */}
      <div className="text-center mt-12">
        <button className="bg-black text-white px-8 py-4 rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.2)] hover:shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] transition-all transform rotate-1 hover:rotate-0">
          Load More Clips ↓
        </button>
      </div>
    </div>
  );
}
