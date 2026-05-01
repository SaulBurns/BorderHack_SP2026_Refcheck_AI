import type { Metadata } from "next";

import Footer from "./components/Footer";
import Header from "./components/Header";
import "../styles/index.css";

export const metadata: Metadata = {
  title: "RefCheck AI",
  description: "AI-powered sports officiating analysis.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen bg-[#F5F0E8] flex flex-col">
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
