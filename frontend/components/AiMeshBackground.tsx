"use client";

export function AiMeshBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="ai-orb ai-orb-1" />
      <div className="ai-orb ai-orb-2" />
      <div className="ai-orb ai-orb-3" />
      <div className="ai-grid absolute inset-0 opacity-[0.35]" />
    </div>
  );
}
