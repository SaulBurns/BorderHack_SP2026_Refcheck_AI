import Link from "next/link";

const topRefs = [
  { name: "Zach Zarba", sport: "Basketball", league: "NBA", rating: 4.8, trend: "up" },
  { name: "Marc Davis", sport: "Basketball", league: "NBA", rating: 4.7, trend: "up" },
  { name: "John Goble", sport: "Basketball", league: "NBA", rating: 4.6, trend: "neutral" },
  { name: "Ed Malloy", sport: "Basketball", league: "NBA", rating: 4.5, trend: "up" },
  { name: "James Capers", sport: "Basketball", league: "NBA", rating: 4.4, trend: "neutral" },
];

const controversialRefs = [
  { name: "Scott Foster", sport: "Basketball", league: "NBA", rating: 3.1, disputes: 53 },
  { name: "Tony Brothers", sport: "Basketball", league: "NBA", rating: 3.3, disputes: 49 },
  { name: "Sean Corbin", sport: "Basketball", league: "NBA", rating: 3.5, disputes: 41 },
  { name: "Courtney Kirkland", sport: "Basketball", league: "NBA", rating: 3.6, disputes: 38 },
  { name: "Ben Taylor", sport: "Basketball", league: "NBA", rating: 3.7, disputes: 34 },
];

const refSlug = (name: string) => name.toLowerCase().replace(/\s+/g, "-");

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
                href={`/ref/${refSlug(ref.name)}`}
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
                href={`/ref/${refSlug(ref.name)}`}
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
          href="/leaderboard"
          className="inline-block bg-black text-white px-8 py-3 rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,0.2)] hover:shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] transition-all transform -rotate-1 hover:rotate-0"
        >
          View Full Leaderboard →
        </Link>
      </div>
    </section>
  );
}
