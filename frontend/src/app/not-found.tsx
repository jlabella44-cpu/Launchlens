import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F5F7FA] px-4">
      <div className="text-center max-w-md">
        <p className="text-8xl font-bold text-[#F97316] mb-4" style={{ fontFamily: "var(--font-heading)" }}>
          404
        </p>
        <h1
          className="text-2xl font-bold text-[var(--color-text)] mb-3"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Page not found
        </h1>
        <p className="text-[var(--color-text-secondary)] mb-8">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            href="/"
            className="px-6 py-2.5 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white font-semibold text-sm transition-colors shadow-lg shadow-orange-200"
          >
            Go home
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-2.5 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-[var(--color-text)] font-semibold text-sm transition-colors"
          >
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
