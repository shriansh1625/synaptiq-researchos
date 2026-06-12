import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import { AiMeshBackground } from "@/components/AiMeshBackground";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SynaptiQ ResearchOS",
  description:
    "Autonomous multi-agent research intelligence — verify claims, detect gaps, map contradictions.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen font-sans`}
      >
        <AiMeshBackground />
        <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-slate-950/70 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
            <Link href="/" className="group">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
                Capgemini Agentify AI · 2026
              </p>
              <h1 className="bg-gradient-to-r from-white via-violet-200 to-cyan-200 bg-clip-text text-xl font-bold text-transparent">
                SynaptiQ ResearchOS
              </h1>
            </Link>
            <nav className="flex items-center gap-3 text-sm">
              <span className="hidden rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400 sm:inline">
                Multi-agent · LangGraph
              </span>
              <Link
                href="/benchmark"
                className="hidden rounded-lg border border-white/10 px-3 py-1.5 text-slate-300 transition hover:border-sky-500/50 hover:text-white sm:inline"
              >
                Benchmarks
              </Link>
              <Link
                href="/"
                className="rounded-lg border border-white/10 px-3 py-1.5 text-slate-300 transition hover:border-sky-500/50 hover:text-white"
              >
                New Query
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
