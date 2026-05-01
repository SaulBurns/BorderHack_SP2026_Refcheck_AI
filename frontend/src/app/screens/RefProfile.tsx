"use client";

import { useState } from "react";

const recentCalls = [
  {
    id: 1,
    game: "State Championship Finals",
    league: "High School - Division 1",
    quarter: "Q4 2:34",
    call: "Offensive foul",
    aiVerdict: "BAD CALL",
    aiColor: "#E63946",
    fairVotes: 142,
    badVotes: 891,
    inconclusiveVotes: 67,
  },
  {
    id: 2,
    game: "Regional Tournament",
    league: "NCAA Division II",
    quarter: "Q2 8:15",
    call: "Out of bounds",
    aiVerdict: "FAIR CALL",
    aiColor: "#2DBF4F",
    fairVotes: 523,
    badVotes: 89,
    inconclusiveVotes: 34,
  },
  {
    id: 3,
    game: "League Finals",
    league: "City Rec League",
    quarter: "Q3 5:42",
    call: "Traveling",
    aiVerdict: "INCONCLUSIVE",
    aiColor: "#F6B40F",
    fairVotes: 234,
    badVotes: 198,
    inconclusiveVotes: 142,
  },
];

export default function RefProfile() {
  const [showRatingForm, setShowRatingForm] = useState(false);

  const ref = {
    name: "John Smith",
    photo: "👨‍⚖️",
    league: "High School - Division 1",
    sport: "Basketball",
    years: 12,
    hometown: "Austin, TX",
    gamesOfficiated: 847,
    overallRating: 3.8,
    dimensions: {
      consistency: 4.1,
      gameAwareness: 3.9,
      communication: 3.2,
      fairness: 4.0,
    },
    strengths: ["Out of bounds calls", "Clock management", "Player communication"],
    weaknesses: ["Charging/blocking decisions", "Late-game pressure situations"],
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* Hero Header */}
      <div className="bg-white rounded-xl shadow-[8px_8px_0_0_rgba(0,0,0,0.15)] p-8 mb-8 border-2 border-black/5 transform -rotate-1">
        <div className="flex items-start gap-8">
          <div className="text-8xl">{ref.photo}</div>
          <div className="flex-1">
            <h1 className="font-marker text-5xl mb-3">{ref.name}</h1>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-x-8 gap-y-2 text-sm font-mono text-gray-600">
              <div><span className="opacity-60">LEAGUE:</span> {ref.league}</div>
              <div><span className="opacity-60">SPORT:</span> {ref.sport}</div>
              <div><span className="opacity-60">YEARS:</span> {ref.years}</div>
              <div><span className="opacity-60">HOMETOWN:</span> {ref.hometown}</div>
              <div><span className="opacity-60">GAMES:</span> {ref.gamesOfficiated}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2 justify-end mb-2">
              <span className="text-5xl">⭐</span>
              <span className="text-5xl">{ref.overallRating}</span>
            </div>
            <div className="text-sm text-gray-500">Overall Rating</div>
          </div>
        </div>
      </div>

      {/* Dimensions Breakdown */}
      <div className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-8 mb-8 border-2 border-black/5 transform rotate-1">
        <h2 className="font-marker text-3xl mb-6">Rating Breakdown</h2>
        <div className="space-y-4">
          {Object.entries(ref.dimensions).map(([dimension, rating]) => (
            <div key={dimension}>
              <div className="flex justify-between mb-2">
                <span className="capitalize">{dimension.replace(/([A-Z])/g, ' $1').trim()}</span>
                <span className="font-mono">{rating} ⭐</span>
              </div>
              <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${rating >= 3 ? 'bg-[#2DBF4F]' : 'bg-[#E63946]'}`}
                  style={{ width: `${(rating / 5) * 100}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Strengths & Weaknesses */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <div className="bg-[#E5FFE5] rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 border-l-4 border-[#2DBF4F]">
          <h3 className="font-marker text-2xl mb-4">Strengths</h3>
          <div className="flex flex-wrap gap-2">
            {ref.strengths.map(strength => (
              <span
                key={strength}
                className="bg-[#2DBF4F] text-white px-3 py-2 rounded-lg text-sm transform rotate-1 hover:rotate-0 transition-transform"
              >
                {strength}
              </span>
            ))}
          </div>
        </div>

        <div className="bg-[#FFE5E5] rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 border-l-4 border-[#E63946]">
          <h3 className="font-marker text-2xl mb-4">Weaknesses</h3>
          <div className="flex flex-wrap gap-2">
            {ref.weaknesses.map(weakness => (
              <span
                key={weakness}
                className="bg-[#E63946] text-white px-3 py-2 rounded-lg text-sm transform -rotate-1 hover:rotate-0 transition-transform"
              >
                {weakness}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Analyzed Calls */}
      <div className="mb-8">
        <h2 className="font-marker text-4xl mb-6 transform -rotate-1">Recent Analyzed Calls</h2>
        <div className="space-y-4">
          {recentCalls.map(call => {
            const totalVotes = call.fairVotes + call.badVotes + call.inconclusiveVotes;
            return (
              <div
                key={call.id}
                className="bg-white rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.1)] p-6 border-2 border-black/5"
              >
                <div className="flex gap-6">
                  {/* Thumbnail */}
                  <div className="bg-gray-200 w-48 h-28 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-4xl">▶️</span>
                  </div>

                  {/* Details */}
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="mb-1">{call.game}</h3>
                        <div className="text-sm text-gray-600 font-mono">{call.league} • {call.quarter} • {call.call}</div>
                      </div>
                      <div
                        className="px-4 py-2 rounded-lg text-white transform rotate-1"
                        style={{ backgroundColor: call.aiColor }}
                      >
                        {call.aiVerdict}
                      </div>
                    </div>

                    {/* Crowd Votes */}
                    <div className="mb-3">
                      <div className="text-xs font-mono mb-1 opacity-60">CROWD VERDICT</div>
                      <div className="flex gap-2 text-sm">
                        <div className="flex items-center gap-1">
                          <span className="text-[#2DBF4F]">👍 Fair:</span>
                          <span>{Math.round((call.fairVotes / totalVotes) * 100)}%</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-[#E63946]">👎 Bad:</span>
                          <span>{Math.round((call.badVotes / totalVotes) * 100)}%</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-[#F6B40F]">❓ Unclear:</span>
                          <span>{Math.round((call.inconclusiveVotes / totalVotes) * 100)}%</span>
                        </div>
                      </div>
                    </div>

                    <button className="bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm">
                      Watch & Vote →
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Rate This Ref */}
      <div className="bg-[#FFF9E6] rounded-xl shadow-[8px_8px_0_0_rgba(0,0,0,0.15)] p-8 border-2 border-[#F6B40F] transform rotate-1 mb-8">
        <h2 className="font-marker text-3xl mb-6">Rate This Ref</h2>
        {!showRatingForm ? (
          <button
            onClick={() => setShowRatingForm(true)}
            className="bg-black text-white px-8 py-4 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Submit Your Rating →
          </button>
        ) : (
          <div className="space-y-6">
            {Object.keys(ref.dimensions).map(dimension => (
              <div key={dimension}>
                <label className="block mb-2 capitalize">
                  {dimension.replace(/([A-Z])/g, ' $1').trim()}
                </label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map(star => (
                    <button key={star} className="text-4xl hover:scale-110 transition-transform">
                      ⭐
                    </button>
                  ))}
                </div>
              </div>
            ))}

            <div>
              <label className="block mb-2">Strengths (optional)</label>
              <input
                type="text"
                placeholder="e.g., Quick decisions, Clear communication"
                className="w-full px-4 py-2 bg-white border-2 border-black/10 rounded-lg"
              />
            </div>

            <div>
              <label className="block mb-2">Weaknesses (optional)</label>
              <input
                type="text"
                placeholder="e.g., Inconsistent calls, Poor positioning"
                className="w-full px-4 py-2 bg-white border-2 border-black/10 rounded-lg"
              />
            </div>

            <div>
              <label className="block mb-2">Written Review (optional)</label>
              <textarea
                rows={4}
                placeholder="Share your thoughts..."
                className="w-full px-4 py-2 bg-white border-2 border-black/10 rounded-lg"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowRatingForm(false)}
                className="flex-1 bg-gray-200 py-3 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button className="flex-1 bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-colors">
                Submit Rating
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
