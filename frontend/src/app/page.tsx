"use client";

import { useState } from "react";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function handleAnalyze() {
    if (!file) return alert("Please upload a video first.");

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      setResult(data);
    } catch (err) {
      alert("Error analyzing video.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-neutral-950 text-white p-8">
      <section className="max-w-3xl mx-auto space-y-6">
        <div>
          <p className="text-sm text-red-400 font-mono">REFCHECK AI</p>
          <h1 className="text-5xl font-bold">Basketball Call Analyzer</h1>
          <p className="text-neutral-300 mt-3">
            Upload a short basketball clip and get a rule-based verdict.
          </p>
        </div>

        <div className="border border-neutral-700 rounded-xl p-6 space-y-4 bg-neutral-900">
          <input
            type="file"
            accept="video/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />

          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="bg-red-500 hover:bg-red-600 disabled:bg-neutral-600 px-5 py-3 rounded-lg font-semibold"
          >
            {loading ? "Analyzing..." : "Analyze Clip"}
          </button>
        </div>

        {result && (
          <div className="rounded-xl p-6 bg-neutral-900 border border-neutral-700 space-y-3">
            <h2 className="text-3xl font-bold">{result.verdict}</h2>
            <p><strong>Confidence:</strong> {result.confidence}</p>
            <p><strong>Call Type:</strong> {result.call_type}</p>
            <p><strong>Rule Applied:</strong> {result.rule_applied}</p>
            <p>{result.reasoning}</p>

            <ul className="list-disc pl-6 text-neutral-300">
              {result.evidence.map((item: string, index: number) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </main>
  );
}