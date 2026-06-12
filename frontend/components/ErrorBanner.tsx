"use client";

interface ErrorBannerProps {
  title?: string;
  errors: Array<Record<string, unknown>>;
  sessionStatus?: string;
}

function formatError(error: Record<string, unknown>): string {
  const message = String(error.message || error.detail || "Unknown error");
  const type = error.error_type ? ` (${String(error.error_type)})` : "";
  const agent = error.agent ? `[${String(error.agent)}] ` : "";
  return `${agent}${message}${type}`;
}

export function ErrorBanner({
  title = "Analysis incomplete",
  errors,
  sessionStatus,
}: ErrorBannerProps) {
  if (!errors.length && sessionStatus !== "failed") return null;

  return (
    <section className="rounded-2xl border border-red-500/40 bg-red-950/40 p-5 glow-accent">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-500/20 text-lg text-red-400">
          !
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-red-200">{title}</h3>
          <p className="mt-1 text-sm text-red-200/80">
            {sessionStatus === "failed"
              ? "The pipeline could not produce a full report. Details below."
              : "Some steps completed with warnings."}
          </p>
          {errors.length > 0 && (
            <ul className="mt-3 space-y-2">
              {errors.map((error, index) => (
                <li
                  key={index}
                  className="rounded-lg border border-red-500/20 bg-black/20 px-3 py-2 text-sm text-red-100/90"
                >
                  {formatError(error)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
