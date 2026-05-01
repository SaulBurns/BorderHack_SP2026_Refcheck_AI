import Link from "next/link";

export default function Hero() {
  return (
    <section className="max-w-7xl mx-auto px-4 py-20 text-center relative">
      <div className="absolute top-10 left-10 text-6xl opacity-20 transform rotate-12">✓</div>
      <div className="absolute top-20 right-20 text-6xl opacity-20 transform -rotate-12">✗</div>
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
        Upload a Clip 📹
      </Link>
      <div className="mt-16 flex justify-center gap-8 font-mono text-sm opacity-60">
        <div>🏀 Basketball</div>
        <div>⚽ Soccer (coming soon)</div>
        <div>🏈 Football (coming soon)</div>
      </div>
    </section>
  );
}
