"use client";

interface HealthBadgeProps {
  score: number;
  size?: "sm" | "md";
}

function getColor(score: number): { bg: string; text: string; dot: string } {
  if (score >= 80) return { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" };
  if (score >= 60) return { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" };
  return { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" };
}

export function HealthBadge({ score, size = "sm" }: HealthBadgeProps) {
  const { bg, text, dot } = getColor(score);
  const sizeClasses = size === "sm" ? "text-xs px-1.5 py-0.5" : "text-sm px-2 py-1";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${bg} ${text} ${sizeClasses}`}
      title={`Health Score: ${score}/100`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {score}
    </span>
  );
}
