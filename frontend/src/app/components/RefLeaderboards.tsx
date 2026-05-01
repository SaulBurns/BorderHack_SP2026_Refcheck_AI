import Link from "next/link";
import Image, { type StaticImageData } from "next/image";
import { Star } from "lucide-react";
import edMalloyPhoto from "../../images/ed_malloy.jpg";
import jamesCapersPhoto from "../../images/james_capers.jpg";
import johnGoblePhoto from "../../images/john_goble.jpg";
import marcDavisPhoto from "../../images/marc_davis.jpg";
import scottFosterPhoto from "../../images/scott_foster.jpg";
import tonyBrothersPhoto from "../../images/Tony-Brothers-scaled.jpg";
import zachZarbaPhoto from "../../images/zach_zarba.jpg";

type RefWithPhoto = {
  name: string;
  sport: string;
  league: string;
  rating: number;
  trend?: "up" | "neutral" | "down";
  disputes?: number;
  photo: StaticImageData;
};

const topRefs: RefWithPhoto[] = [
  { name: "Zach Zarba", sport: "Basketball", league: "NBA", rating: 4.8, trend: "up", photo: zachZarbaPhoto },
  { name: "Marc Davis", sport: "Basketball", league: "NBA", rating: 4.7, trend: "up", photo: marcDavisPhoto },
  { name: "John Goble", sport: "Basketball", league: "NBA", rating: 4.6, trend: "neutral", photo: johnGoblePhoto },
  { name: "Ed Malloy", sport: "Basketball", league: "NBA", rating: 4.5, trend: "up", photo: edMalloyPhoto },
  { name: "James Capers", sport: "Basketball", league: "NBA", rating: 4.4, trend: "neutral", photo: jamesCapersPhoto },
];

const controversialRefs: RefWithPhoto[] = [
  { name: "Scott Foster", sport: "Basketball", league: "NBA", rating: 3.1, disputes: 53, photo: scottFosterPhoto },
  { name: "Tony Brothers", sport: "Basketball", league: "NBA", rating: 3.3, disputes: 49, photo: tonyBrothersPhoto },
  { name: "James Capers", sport: "Basketball", league: "NBA", rating: 4.4, disputes: 36, photo: jamesCapersPhoto },
  { name: "Ed Malloy", sport: "Basketball", league: "NBA", rating: 4.5, disputes: 31, photo: edMalloyPhoto },
  { name: "John Goble", sport: "Basketball", league: "NBA", rating: 4.6, disputes: 27, photo: johnGoblePhoto },
];

const refSlug = (name: string) => name.toLowerCase().replace(/\s+/g, "-");

function RefAvatar({ official }: { official: RefWithPhoto }) {
  return (
    <div className="relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-full border-2 border-black/10 bg-gray-100">
      <Image
        src={official.photo}
        alt={`${official.name} profile`}
        fill
        sizes="48px"
        className="object-cover"
        placeholder="blur"
      />
    </div>
  );
}

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
                  <RefAvatar official={ref} />
                  <div>
                    <div>{ref.name}</div>
                    <div className="text-sm text-gray-500">{ref.league}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <Star className="h-5 w-5 fill-[#F6B40F] text-[#F6B40F]" />
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
                  <RefAvatar official={ref} />
                  <div>
                    <div>{ref.name}</div>
                    <div className="text-sm text-gray-500">{ref.league}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-1">
                    <Star className="h-5 w-5 fill-[#F6B40F] text-[#F6B40F]" />
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
