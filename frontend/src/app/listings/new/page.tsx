import Link from "next/link";
import { WizardContainer } from "@/components/listings/creation-wizard/wizard-container";

export default function NewListingPage() {
  return (
    <main className="min-h-screen bg-[var(--color-background)]">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <Link
          href="/listings"
          className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        >
          &larr; Back to Listings
        </Link>
      </div>
      <WizardContainer />
    </main>
  );
}
