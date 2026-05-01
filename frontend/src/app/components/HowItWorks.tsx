import { Bot, BookOpen, Scale, Upload } from "lucide-react";

const steps = [
  { number: "01", title: "Upload clip", description: "Submit your controversial call video", Icon: Upload },
  { number: "02", title: "AI analyzes", description: "Our AI reviews the footage frame-by-frame", Icon: Bot },
  { number: "03", title: "Compare rulebook", description: "Cross-reference with official basketball rules", Icon: BookOpen },
  { number: "04", title: "Return verdict", description: "Get AI verdict + community ratings", Icon: Scale },
];

const colors = ["#FFF9C4", "#FFE5E5", "#E5F3FF", "#E5FFE5"];

export default function HowItWorks() {
  return (
    <section className="w-full px-4 py-20 bg-[#e8e3db]">
      <div className="max-w-7xl mx-auto">
        <h2 className="font-marker text-5xl mb-12 text-center transform -rotate-1">
          How It Works
        </h2>
        <div className="grid md:grid-cols-4 gap-6">
          {steps.map((step, idx) => (
            <div
              key={idx}
              className="rounded-lg shadow-[6px_6px_0_0_rgba(0,0,0,0.2)] p-6 hover:scale-105 transition-all border-2 border-black/10"
              style={{
                backgroundColor: colors[idx],
                transform: `rotate(${idx % 2 === 0 ? '1deg' : '-1deg'})`
              }}
            >
              <step.Icon className="mb-3 h-10 w-10" strokeWidth={2.2} />
              <div className="font-mono text-xs mb-3 opacity-60 tracking-wider">STEP {step.number}</div>
              <h3 className="mb-2 text-lg">{step.title}</h3>
              <p className="text-sm text-gray-700 leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
