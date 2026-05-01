"use client";

import { useState } from "react";

const refs = [
  {
    rank: 1,
    name: "Sarah Mitchell",
    league: "NCAA Division I",
    sport: "Basketball",
    years: 12,
    rating: 4.8,
    totalRatings: 1247,
    aiCallsAnalyzed: 89,
    aiAgreement: 87,
    trend: "up",
    photo: "👩‍⚖️"
  },
  {
    rank: 2,
    name: "Marcus Chen",
    league: "EuroLeague",
    sport: "Basketball",
    years: 8,
    rating: 4.7,
    totalRatings: 956,
    aiCallsAnalyzed: 76,
    aiAgreement: 82,
    trend: "up",
    photo: "👨‍⚖️"
  },
  {
    rank: 3,
    name: "Elena Rodriguez",
    league: "WNBA",
    sport: "Basketball",
    years: 15,
    rating: 4.6,
    totalRatings: 1893,
    aiCallsAnalyzed: 134,
    aiAgreement: 79,
    trend: "neutral",
    photo: "👩‍⚖️"
  },
  {
    rank: 4,
    name: "James O'Brien",
    league: "High School",
    sport: "Basketball",
    years: 10,
    rating: 4.5,
    totalRatings: 1124,
    aiCallsAnalyzed: 92,
    aiAgreement: 81,
    trend: "up",
    photo: "👨‍⚖️"
  },
  {
    rank: 5,
    name: "Kenji Tanaka",
    league: "B.League (Japan)",
    sport: "Basketball",
    years: 6,
    rating: 4.4,
    totalRatings: 734,
    aiCallsAnalyzed: 58,
    aiAgreement: 84,
    trend: "down",
    photo: "👨‍⚖️"
  },
  {
    rank: 6,
    name: "David Park",
    league: "NBA G League",
    sport: "Basketball",
    years: 28,
    rating: 2.1,
    totalRatings: 3421,
    aiCallsAnalyzed: 247,
    aiAgreement: 34,
    trend: "down",
    photo: "👨‍⚖️"
  },
  {
    rank: 7,
    name: "Ahmad Hassan",
    league: "FIBA Asia",
    sport: "Basketball",
    years: 27,
    rating: 2.3,
    totalRatings: 2987,
    aiCallsAnalyzed: 213,
    aiAgreement: 41,
    trend: "down",
    photo: "👨‍⚖️"
  },
];

export default function Leaderboard() {
  const [sortBy, setSortBy] = useState("highest");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredRefs = refs.filter(ref =>
    ref.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-16">
      <h1 className="font-marker text-6xl mb-3 text-center transform -rotate-1">
        THE LEADERBOARD
      </h1>
      <p className="text-center text-gray-600 mb-12">See how refs rank across all levels of basketball</p>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-8 border-2 border-black/5">
        <div className="grid md:grid-cols-2 gap-4">
          {/* Level Filter */}
          <div>
            <label className="block mb-2 font-mono text-xs opacity-60">LEVEL</label>
            <div className="flex gap-2 flex-wrap">
              {['All Levels', 'Professional', 'College', 'High School', 'Youth', 'Rec'].map(level => (
                <button
                  key={level}
                  className={`
                    px-4 py-2 rounded-lg border-2 text-sm transition-all
                    ${level === 'All Levels'
                      ? 'bg-black text-white border-black'
                      : 'bg-white border-black/10 hover:border-black/30'
                    }
                  `}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>

          {/* Sort */}
          <div>
            <label className="block mb-2 font-mono text-xs opacity-60">SORT BY</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full px-4 py-2 bg-white border-2 border-black/10 rounded-lg focus:border-black focus:outline-none"
            >
              <option value="highest">Highest Rated</option>
              <option value="active">Most Active</option>
              <option value="controversial">Most Controversial</option>
              <option value="improved">Most Improved</option>
            </select>
          </div>
        </div>

        {/* Search */}
        <div className="mt-4">
          <label className="block mb-2 font-mono text-xs opacity-60">SEARCH REF</label>
          <input
            type="text"
            placeholder="Search by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 bg-white border-2 border-black/10 rounded-lg focus:border-black focus:outline-none"
          />
        </div>
      </div>

      {/* Ref Cards */}
      <div className="space-y-4">
        {filteredRefs.map((ref, idx) => (
          <a
            key={ref.rank}
            href={`/ref/${ref.name.toLowerCase().replace(' ', '-')}`}
            className="block bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 border-2 border-black/5 hover:shadow-[8px_8px_0_0_rgba(0,0,0,0.15)] hover:scale-[1.01] transition-all transform hover:rotate-1"
            style={{ transform: `rotate(${idx % 2 === 0 ? '0.5deg' : '-0.5deg'})` }}
          >
            <div className="flex items-center gap-6">
              {/* Rank */}
              <div
                className={`
                  w-16 h-16 rounded-full flex items-center justify-center font-marker text-2xl text-white
                  ${ref.rating >= 4 ? 'bg-[#2DBF4F]' : 'bg-[#E63946]'}
                `}
              >
                #{ref.rank}
              </div>

              {/* Photo */}
              <div className="text-5xl">{ref.photo}</div>

              {/* Info */}
              <div className="flex-1">
                <h3 className="text-xl mb-1">{ref.name}</h3>
                <div className="flex gap-4 text-sm text-gray-600 font-mono">
                  <span>{ref.league}</span>
                  <span>•</span>
                  <span>{ref.years} years</span>
                </div>
              </div>

              {/* Stats */}
              <div className="text-right space-y-2">
                <div className="flex items-center gap-2 justify-end">
                  <span className="text-3xl">⭐</span>
                  <span className="text-2xl">{ref.rating}</span>
                  {ref.trend === "up" && <span className="text-[#2DBF4F] text-xl">↗</span>}
                  {ref.trend === "down" && <span className="text-[#E63946] text-xl">↘</span>}
                  {ref.trend === "neutral" && <span className="text-gray-400 text-xl">→</span>}
                </div>
                <div className="text-xs text-gray-500 font-mono">{ref.totalRatings} ratings</div>
                <div className="text-xs text-gray-500 font-mono">{ref.aiCallsAnalyzed} AI-analyzed calls</div>
                <div
                  className={`
                    text-xs font-mono px-2 py-1 rounded inline-block
                    ${ref.aiAgreement >= 70 ? 'bg-[#2DBF4F]/20 text-[#2DBF4F]' : 'bg-[#E63946]/20 text-[#E63946]'}
                  `}
                >
                  AI agreement: {ref.aiAgreement}%
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>

      {filteredRefs.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          <div className="text-6xl mb-4">🔍</div>
          <p>No refs found matching "{searchQuery}"</p>
        </div>
      )}
    </div>
  );
}
