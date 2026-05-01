"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeClip, cacheVerdict } from "../../lib/api";

const sports = [
  { id: "basketball", name: "Basketball", emoji: "🏀", active: true },
  { id: "soccer", name: "Soccer", emoji: "⚽", active: false },
  { id: "football", name: "Football", emoji: "🏈", active: false },
  { id: "baseball", name: "Baseball", emoji: "⚾", active: false },
  { id: "hockey", name: "Hockey", emoji: "🏒", active: false },
];

const basketballLevels = [
  "Professional",
  "College / University",
  "High School",
  "Youth / AAU",
  "Rec League",
  "Pickup / Street",
  "Other",
];

const loadingSteps = [
  "Extracting frames from video...",
  "Analyzing play mechanics...",
  "Checking basketball rulebook...",
  "Cross-checking with second adjudicator...",
];

export default function Upload() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedSport, setSelectedSport] = useState("basketball");
  const [dragActive, setDragActive] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Form state (replaces uncontrolled inputs)
  const [file, setFile] = useState<File | null>(null);
  const [level, setLevel] = useState("");
  const [league, setLeague] = useState("");
  const [originalCall, setOriginalCall] = useState("");
  const [refName, setRefName] = useState("");

  // Drive the loading-step animation independently of the network request
  useEffect(() => {
    if (!analyzing) return;
    const interval = setInterval(() => {
      setCurrentStep((prev) => Math.min(prev + 1, loadingSteps.length - 1));
    }, 4000); // ~4s per stage; full pipeline ≈ 16s
    return () => clearInterval(interval);
  }, [analyzing]);

  const handleFileSelect = (selectedFile: File | undefined) => {
    if (!selectedFile) return;
    if (!selectedFile.type.startsWith("video/")) {
      setError("Please select a video file.");
      return;
    }
    setError(null);
    setFile(selectedFile);
  };

  const handleSubmit = async () => {
    if (!file) {
      setError("Please choose a video clip first.");
      return;
    }
    setError(null);
    setAnalyzing(true);
    setCurrentStep(0);

    try {
      const response = await analyzeClip({
        file,
        sport: "basketball",
        originalCall: originalCall || undefined,
        refName: refName || undefined,
        league: league || undefined,
        level: level || undefined,
      });
      cacheVerdict(response.clip_id, response);
      router.push(`/verdict/${response.clip_id}`);
    } catch (err) {
      setAnalyzing(false);
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      <h1 className="font-marker text-6xl mb-4 text-center transform -rotate-1">
        ANALYZE A CALL
      </h1>
      <p className="text-center text-lg mb-12 text-gray-600">
        Upload any basketball clip from any level — pro, college, high school, or rec league
      </p>

      {!analyzing ? (
        <div className="space-y-8">
          {/* Sport Selector */}
          <div>
            <label className="block mb-4 font-mono text-sm opacity-60">SELECT SPORT</label>
            <div className="grid grid-cols-5 gap-3">
              {sports.map((sport) => (
                <button
                  key={sport.id}
                  onClick={() => sport.active && setSelectedSport(sport.id)}
                  disabled={!sport.active}
                  className={`
                    relative p-4 rounded-lg border-2 transition-all
                    ${
                      sport.active
                        ? selectedSport === sport.id
                          ? "bg-black text-white border-black shadow-[4px_4px_0_0_rgba(0,0,0,0.3)]"
                          : "bg-white border-black/10 hover:border-black/30"
                        : "bg-gray-100 border-gray-200 opacity-50 cursor-not-allowed"
                    }
                  `}
                >
                  <div className="text-3xl mb-2">{sport.emoji}</div>
                  <div className="text-sm">{sport.name}</div>
                  {!sport.active && (
                    <div className="absolute -top-2 -right-2 bg-[#F6B40F] text-xs px-2 py-1 rounded transform rotate-12 shadow-sm">
                      Soon
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Upload Zone */}
          <div>
            <label className="block mb-4 font-mono text-sm opacity-60">UPLOAD VIDEO</label>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
            />
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragEnter={() => setDragActive(true)}
              onDragLeave={() => setDragActive(false)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                handleFileSelect(e.dataTransfer.files?.[0]);
              }}
              className={`
                bg-white border-4 border-dashed rounded-xl p-16 text-center transition-all cursor-pointer
                ${dragActive
                  ? "border-black bg-gray-50 scale-[1.02]"
                  : "border-black/30 hover:border-black/50"}
              `}
              style={{
                backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.02) 10px, rgba(0,0,0,0.02) 20px)`,
              }}
            >
              <div className="text-6xl mb-4">📹</div>
              {file ? (
                <>
                  <p className="text-xl mb-2">{file.name}</p>
                  <p className="text-sm text-gray-500 mb-4">
                    {(file.size / 1024 / 1024).toFixed(1)} MB · click to change
                  </p>
                </>
              ) : (
                <>
                  <p className="text-xl mb-2">Drop your video here</p>
                  <p className="text-sm text-gray-500 mb-4">or click to browse</p>
                </>
              )}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
                className="bg-black text-white px-6 py-2 rounded-lg hover:bg-gray-800 transition-colors"
              >
                Choose File
              </button>
              <p className="text-xs text-gray-400 mt-4 font-mono">
                Supports MP4, MOV, AVI · Max 500MB
              </p>
            </div>
          </div>

          {/* Level Selector */}
          <div>
            <label className="block mb-3 font-mono text-sm opacity-60">
              LEVEL OF PLAY <span className="text-gray-400">(optional)</span>
            </label>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="w-full px-4 py-3 bg-white border-2 border-black/10 rounded-lg focus:border-black focus:outline-none transition-colors"
            >
              <option value="">Select level...</option>
              {basketballLevels.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </div>

          {/* League/Organization Input */}
          <div>
            <label className="block mb-3 font-mono text-sm opacity-60">
              LEAGUE / ORGANIZATION <span className="text-gray-400">(optional)</span>
            </label>
            <input
              type="text"
              value={league}
              onChange={(e) => setLeague(e.target.value)}
              placeholder="e.g., NBA, NCAA, FIBA, EuroLeague, local rec league"
              className="w-full px-4 py-3 bg-white border-2 border-black/10 rounded-lg focus:border-black focus:outline-none transition-colors"
            />
          </div>

          {/* Original Call Input */}
          <div>
            <label className="block mb-3 font-mono text-sm opacity-60">
              WHAT WAS THE ORIGINAL CALL? <span className="text-gray-400">(optional)</span>
            </label>
            <input
              type="text"
              value={originalCall}
              onChange={(e) => setOriginalCall(e.target.value)}
              placeholder="e.g., Blocking foul, Traveling, Out of bounds"
              className="w-full px-4 py-3 bg-white border-2 border-black/10 rounded-lg focus:border-black focus:outline-none transition-colors"
            />
          </div>

          {/* Ref Name Input */}
          <div>
            <label className="block mb-3 font-mono text-sm opacity-60">
              REFEREE NAME <span className="text-gray-400">(optional)</span>
            </label>
            <input
              type="text"
              value={refName}
              onChange={(e) => setRefName(e.target.value)}
              placeholder="Enter referee name..."
              className="w-full px-4 py-3 bg-white border-2 border-black/10 rounded-lg focus:border-black focus:outline-none transition-colors"
            />
          </div>

          {error && (
            <div className="bg-red-50 border-2 border-red-300 text-red-800 p-4 rounded-lg font-mono text-sm">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={!file}
            className="w-full bg-[#2DBF4F] text-white py-5 rounded-xl shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] hover:shadow-[8px_8px_0_0_rgba(0,0,0,0.2)] hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all transform rotate-1 hover:rotate-0 text-xl font-mono disabled:opacity-50 disabled:cursor-not-allowed"
          >
            GET VERDICT →
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-[8px_8px_0_0_rgba(0,0,0,0.15)] p-12 border-2 border-black/5">
          <div className="text-center mb-8">
            <div className="text-6xl mb-4 animate-bounce">🤖</div>
            <h2 className="text-2xl mb-2">Analyzing Your Clip...</h2>
            <p className="text-gray-500">This usually takes 15-30 seconds</p>
          </div>

          <div className="space-y-4">
            {loadingSteps.map((step, idx) => (
              <div
                key={idx}
                className={`
                  flex items-center gap-4 p-4 rounded-lg border-2 transition-all
                  ${
                    idx < currentStep
                      ? "bg-[#2DBF4F]/10 border-[#2DBF4F]"
                      : idx === currentStep
                      ? "bg-[#F6B40F]/10 border-[#F6B40F] animate-pulse"
                      : "bg-gray-50 border-gray-200"
                  }
                `}
              >
                <div className="text-2xl">
                  {idx < currentStep ? "✓" : idx === currentStep ? "⏳" : "○"}
                </div>
                <div className="font-mono text-sm flex-1">{step}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
