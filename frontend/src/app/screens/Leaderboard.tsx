"use client";

import Image, { type StaticImageData } from "next/image";
import { useState } from "react";
import { Search, Star } from "lucide-react";
import edMalloyPhoto from "../../images/ed_malloy.jpg";
import jamesCapersPhoto from "../../images/james_capers.jpg";
import johnGoblePhoto from "../../images/john_goble.jpg";
import marcDavisPhoto from "../../images/marc_davis.jpg";
import scottFosterPhoto from "../../images/scott_foster.jpg";
import tonyBrothersPhoto from "../../images/Tony-Brothers-scaled.jpg";
import zachZarbaPhoto from "../../images/zach_zarba.jpg";

type Referee = {
  rank: number;
  name: string;
  league: string;
  sport: string;
  years: number;
  rating: number;
  totalRatings: number;
  aiCallsAnalyzed: number;
  aiAgreement: number;
  trend: "up" | "neutral" | "down";
  photo: StaticImageData;
};

const refs: Referee[] = [
  {
    rank: 1,
    name: "Zach Zarba",
    league: "NBA",
    sport: "Basketball",
    years: 22,
    rating: 4.8,
    totalRatings: 2418,
    aiCallsAnalyzed: 173,
    aiAgreement: 86,
    trend: "up",
    photo: zachZarbaPhoto,
  },
  {
    rank: 2,
    name: "Marc Davis",
    league: "NBA",
    sport: "Basketball",
    years: 27,
    rating: 4.7,
    totalRatings: 2675,
    aiCallsAnalyzed: 218,
    aiAgreement: 84,
    trend: "up",
    photo: marcDavisPhoto,
  },
  {
    rank: 3,
    name: "John Goble",
    league: "NBA",
    sport: "Basketball",
    years: 17,
    rating: 4.6,
    totalRatings: 1984,
    aiCallsAnalyzed: 151,
    aiAgreement: 82,
    trend: "neutral",
    photo: johnGoblePhoto,
  },
  {
    rank: 4,
    name: "Ed Malloy",
    league: "NBA",
    sport: "Basketball",
    years: 23,
    rating: 4.5,
    totalRatings: 2261,
    aiCallsAnalyzed: 150,
    aiAgreement: 80,
    trend: "up",
    photo: edMalloyPhoto,
  },
  {
    rank: 5,
    name: "James Capers",
    league: "NBA",
    sport: "Basketball",
    years: 30,
    rating: 4.4,
    totalRatings: 2517,
    aiCallsAnalyzed: 204,
    aiAgreement: 79,
    trend: "neutral",
    photo: jamesCapersPhoto,
  },
  {
    rank: 6,
    name: "Tony Brothers",
    league: "NBA",
    sport: "Basketball",
    years: 27,
    rating: 3.3,
    totalRatings: 3142,
    aiCallsAnalyzed: 216,
    aiAgreement: 64,
    trend: "down",
    photo: tonyBrothersPhoto,
  },
  {
    rank: 7,
    name: "Scott Foster",
    league: "NBA",
    sport: "Basketball",
    years: 31,
    rating: 3.1,
    totalRatings: 3898,
    aiCallsAnalyzed: 262,
    aiAgreement: 61,
    trend: "down",
    photo: scottFosterPhoto,
  },
];

const refSlug = (name: string) => name.toLowerCase().replace(/\s+/g, "-");

export default function Leaderboard() {
  const [sortBy, setSortBy] = useState("highest");
  const [searchQuery, setSearchQuery] = useState("");
  const [levelFilter, setLevelFilter] = useState("All Levels");

  const filteredRefs = refs
    .filter((ref) =>
      ref.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .filter((ref) => {
      if (levelFilter === "All Levels") return true;
      if (levelFilter === "Professional") {
        return /NBA/.test(ref.league);
      }
      return ref.league.includes(levelFilter);
    })
    .sort((a, b) => {
      if (sortBy === "active") return b.aiCallsAnalyzed - a.aiCallsAnalyzed;
      if (sortBy === "controversial") return a.aiAgreement - b.aiAgreement;
      if (sortBy === "improved") {
        const trendScore = { up: 2, neutral: 1, down: 0 };
        return trendScore[b.trend as keyof typeof trendScore] - trendScore[a.trend as keyof typeof trendScore];
      }
      return b.rating - a.rating;
    });

  return (
    <div className="max-w-6xl mx-auto px-4 py-16">
      <h1 className="font-marker text-6xl mb-3 text-center transform -rotate-1">
        THE LEADERBOARD
      </h1>
      <p className="text-center text-gray-600 mb-12">See how NBA officials rank across community ratings and AI-reviewed calls</p>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 mb-8 border-2 border-black/5">
        <div className="grid md:grid-cols-2 gap-4">
          {/* Level Filter */}
          <div>
            <label className="block mb-2 font-mono text-xs opacity-60">LEVEL</label>
            <div className="flex gap-2 flex-wrap">
              {['All Levels', 'Professional'].map(level => (
                <button
                  key={level}
                  onClick={() => setLevelFilter(level)}
                  className={`
                    px-4 py-2 rounded-lg border-2 text-sm transition-all
                    ${level === levelFilter
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
            href={`/ref/${refSlug(ref.name)}`}
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
              <div className="relative h-20 w-20 flex-shrink-0 overflow-hidden rounded-full border-2 border-black/10 bg-gray-100 shadow-[3px_3px_0_0_rgba(0,0,0,0.1)]">
                <Image
                  src={ref.photo}
                  alt={`${ref.name} profile`}
                  fill
                  sizes="80px"
                  className="object-cover"
                  placeholder="blur"
                />
              </div>

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
                  <Star className="h-8 w-8 fill-[#F6B40F] text-[#F6B40F]" />
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
          <Search className="mx-auto mb-4 h-16 w-16 text-gray-400" />
          <p>No refs found matching "{searchQuery}"</p>
        </div>
      )}
    </div>
  );
}
