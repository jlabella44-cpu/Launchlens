import Link from "next/link";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  if (items.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] mb-4">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && (
            <svg className="w-3.5 h-3.5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          )}
          {item.href && i < items.length - 1 ? (
            <Link href={item.href} className="hover:text-[var(--color-primary)] transition-colors">
              {item.label}
            </Link>
          ) : (
            <span className={i === items.length - 1 ? "text-[var(--color-text)] font-medium" : ""}>
              {item.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
