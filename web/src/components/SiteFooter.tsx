export function SiteFooter() {
  return (
    <footer className="relative z-10 w-full border-t border-white/[0.06] bg-surface-container-lowest/90 py-space-lg backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-shell flex-col items-center justify-between gap-space-md px-margin text-center md:flex-row md:px-margin-tablet md:text-left lg:px-margin-desktop">
        <div className="flex items-center gap-space-sm">
          <span className="text-primary">✦</span>
          <p className="text-body-sm text-on-surface-variant">
            TasteRank AI Recommendation Engine • Grounded semantic ranking based
            on local culinary reviews and real-time preferences
          </p>
        </div>
        <span className="text-label-sm text-on-surface-variant">
          © 2025 TasteRank Tech Inc.
        </span>
      </div>
    </footer>
  );
}
