import Link from "next/link";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 bg-[#F5F0E8] border-b-2 border-black shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="font-marker text-3xl hover:opacity-80 transition-opacity">
          REFCHECK AI
        </Link>
        <nav className="flex gap-8 items-center">
          <Link href="/" className="hover:underline transition-all">Home</Link>
          <Link href="/upload" className="hover:underline transition-all">Upload Clip</Link>
          <Link href="/feed" className="hover:underline transition-all">Hot Takes</Link>
          <Link href="/leaderboard" className="hover:underline transition-all">Leaderboard</Link>
        </nav>
      </div>
    </header>
  );
}
