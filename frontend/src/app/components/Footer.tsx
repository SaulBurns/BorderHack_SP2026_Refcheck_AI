import { Trophy } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t-4 border-black mt-20 py-10 bg-white">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="font-marker text-3xl transform -rotate-1">REFCHECK AI</div>
          <div className="flex gap-6 items-center font-mono text-sm">
            <span className="opacity-60">SPONSORED BY DROPDEV</span>
            <span className="bg-black text-white px-4 py-2 rounded transform rotate-1">BORDERHACK '26</span>
          </div>
        </div>
        <div className="mt-8 text-center text-sm text-gray-500">
          <p className="inline-flex items-center gap-2">
            Any level. Any league. Fair calls for everyone.
            <Trophy className="h-4 w-4" />
          </p>
        </div>
      </div>
    </footer>
  );
}
