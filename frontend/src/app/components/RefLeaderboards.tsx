import { Link } from "react-router";

const topRefs = [
  { name: "Sarah Mitchell", sport: "Basketball", league: "NCAA D1", rating: 4.8, trend: "up" },
  { name: "Marcus Chen", sport: "Basketball", league: "EuroLeague", rating: 4.7, trend: "up" },
  { name: "Elena Rodriguez", sport: "Basketball", league: "WNBA", rating: 4.6, trend: "neutral" },
  { name: "James O'Brien", sport: "Basketball", league: "High School", rating: 4.5, trend: "up" },
  { name: "Kenji Tanaka", sport: "Basketball", league: "B.League", rating: 4.4, trend: "down" },
];

const controversialRefs = [
  { name: "David Park", sport: "Basketball", league: "G League", rating: 2.1, disputes: 47 },
  { name: "Ahmad Hassan", sport: "Basketball", league: "FIBA Asia", rating: 2.3, disputes: 42 },
  { name: "Carlos Martinez", sport: "Basketball", league: "Liga ACB", rating: 2.5, disputes: 38 },
  { name: "Mike Johnson", sport: "Basketball", league: "NCAA D2", rating: 2.6, disputes: 35 },
  { name: "Tom Anderson", sport: "Basketball", league: "City League", rating: 2.7, disputes: 31 },
];

export default function RefLeaderboards() {
  return (
    <section className="max-w-7xl mx-auto px-4 py-16">
      <div className="grid md:grid-cols-2 gap-8">
        {/* Top Rated */}
        <div>
          <h2 className="font-marker text-4xl mb-6 transform -rotate-1">
            Top Rated Refs
          </h2>
          <div className="space-y-3">
            {topRefs.map((ref, idx) => (
              <Link
                key={idx}
                to={`/ref/${ref.name.toLowerCase().replace(' ', '-')}`}
                className="bg-white rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.1)] p-4 flex items-center justify-between transform hover:rotate-1 transition-transform block"
              >
                <div className="flex items-center gap-4">
                  <div className="bg-[#2DBF4F] text-white w-10 h-10 rounded-full flex items-center justify-center font-mono">
                    {idx + 1}
                  </div>
                  <div>
                    <div>{ref.name}</div>
                    <div className="text-sm text-gray-500">{ref.league}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <span className="text-xl">⭐</span>
                    <span>{ref.rating}</span>
                  </div>
                  {ref.trend === "up" && <span className="text-[#2DBF4F]">↗</span>}
                  {ref.trend === "down" && <span className="text-[#E63946]">↘</span>}
                  {ref.trend === "neutral" && <span className="text-gray-400">→</span>}
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Most Controversial */}
        <div>
          <h2 className="font-marker text-4xl mb-6 transform rotate-1">
            Most Controversial
          </h2>
          <div className="space-y-3">
            {controversialRefs.map((ref, idx) => (
              <Link
                key={idx}
                to={`/ref/${ref.name.toLowerCase().replace(' ', '-')}`}
                className="bg-white rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.1)] p-4 flex items-center justify-between transform hover:-rotate-1 transition-transform block"
              >
                <div className="flex items-center gap-4">
                  <div className="bg-[#E63946] text-white w-10 h-10 rounded-full flex items-center justify-center font-mono">
                    {idx + 1}
                  </div>
                  <div>
                    <div>{ref.name}</div>
                    <div className="text-sm text-gray-500">{ref.league}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-1">
                    <span className="text-xl">⭐</span>
                    <span>{ref.rating}</span>
                  </div>
                  <div className="text-sm text-[#E63946] font-mono">{ref.disputes} DISPUTES</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* View Full Leaderboard */}
      <div className="text-center mt-8">
        <Link
          to="/leaderboard"
          className="inline-block bg-black text-white px-8 py-3 rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.2)] hover:shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] transition-all transform -rotate-1 hover:rotate-0"
        >
          View Full Leaderboard →
        </Link>
      </div>
    </section>
  );
}
