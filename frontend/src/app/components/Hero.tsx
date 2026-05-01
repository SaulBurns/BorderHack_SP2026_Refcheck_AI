import Link from "next/link";
import { CircleDot, Target, Trophy, Upload, Waves } from "lucide-react";

export default function Hero() {
  return (
    <section className="max-w-7xl mx-auto px-4 py-20 text-center relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 opacity-70">
        {[
          { left: "8%", top: "18%", delay: "0s", color: "#2DBF4F" },
          { left: "18%", top: "74%", delay: "0.8s", color: "#F6B40F" },
          { left: "80%", top: "20%", delay: "0.35s", color: "#E63946" },
          { left: "90%", top: "64%", delay: "1.1s", color: "#3B82F6" },
          { left: "48%", top: "86%", delay: "0.55s", color: "#111111" },
        ].map((particle, index) => (
          <span
            key={index}
            className="absolute h-3 w-3 rounded-full border-2 border-black bg-white shadow-[2px_2px_0_0_rgba(0,0,0,0.28)] animate-bounce"
            style={{
              left: particle.left,
              top: particle.top,
              animationDelay: particle.delay,
              backgroundColor: particle.color,
            }}
          />
        ))}
        <Waves className="absolute left-[12%] top-[36%] h-12 w-12 rotate-12 text-black/10" />
        <Target className="absolute right-[12%] bottom-[24%] h-14 w-14 -rotate-12 text-black/10" />
      </div>
      <div className="absolute top-10 left-10 opacity-20 transform rotate-12">
        <CircleDot className="h-14 w-14" />
      </div>
      <div className="absolute top-20 right-20 opacity-20 transform -rotate-12">
        <Target className="h-14 w-14" />
      </div>
      <h1 className="font-marker text-7xl mb-6 transform -rotate-1 relative inline-block">
        REFCHECK AI
        <svg className="absolute -bottom-2 left-0 w-full" height="8" viewBox="0 0 400 8">
          <path d="M 0 4 Q 100 0, 200 4 T 400 4" stroke="#F6B40F" strokeWidth="6" fill="none" strokeLinecap="round" />
        </svg>
      </h1>
      <p className="text-2xl mb-10 max-w-2xl mx-auto">
        From NBA to rec league — was the call fair? Let the AI and the crowd decide.
      </p>
      <Link
        href="/upload"
        className="inline-block bg-black text-white px-10 py-4 rounded-lg shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-[6px_6px_0_0_rgba(0,0,0,1)] hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all text-lg"
      >
        <Upload className="mr-2 inline h-5 w-5" />
        Upload a Clip
      </Link>
      <div className="mt-16 flex justify-center gap-8 font-mono text-sm opacity-60">
        <div className="flex items-center gap-2">
          <Trophy className="h-4 w-4" /> Basketball
        </div>
        <div className="flex items-center gap-2">
          <CircleDot className="h-4 w-4" /> Tennis coming soon
        </div>
      </div>
    </section>
  );
}
