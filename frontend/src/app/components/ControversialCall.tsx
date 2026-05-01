import Link from "next/link";

export default function ControversialCall() {
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
          <div className="absolute inset-0 bg-black/10"></div>
          <div className="relative z-10 text-center">
            <div className="text-6xl mb-2">🏀</div>
            <span className="text-gray-600">Click to watch</span>
          </div>
        </div>
        <div className="flex items-center justify-between mb-6">
          <div className="bg-[#E63946] text-white px-6 py-2 rounded-md inline-block transform rotate-1 shadow-[3px_3px_0_0_rgba(0,0,0,0.2)]">
            BAD CALL
          </div>
          <div className="font-mono bg-black text-white px-4 py-2 rounded">89% CONFIDENCE</div>
        </div>
        <div className="font-mono text-sm mb-2 opacity-60">High School - Division 1 • State Championship • Q4 2:34</div>
        <h3 className="text-xl mb-3">Questionable Offensive Foul Call</h3>
        <p className="text-gray-600 mb-6 leading-relaxed">
          Questionable offensive foul called during crucial possession in the state championship finals.
          AI analysis suggests defensive player was still moving and had not established legal guarding position.
        </p>
        <div className="border-l-4 border-[#F6B40F] pl-4 bg-[#FFF9E6] p-4 rounded transform -rotate-1">
          <p className="font-mono text-xs mb-2 opacity-70">RULE CITED</p>
          <p className="text-sm">NFHS Rule 4-7-2: Blocking Foul vs. Charging</p>
        </div>
        <div className="mt-6 flex gap-4">
          <button className="flex-1 bg-[#2DBF4F] text-white py-3 rounded-lg hover:bg-[#25a643] transition-colors">
            👍 Fair Call (142)
          </button>
          <button className="flex-1 bg-[#E63946] text-white py-3 rounded-lg hover:bg-[#d1303c] transition-colors">
            👎 Bad Call (891)
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
