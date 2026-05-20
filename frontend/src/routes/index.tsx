import { createFileRoute } from "@tanstack/react-router";

import { BottomCta } from "@/features/landing/components/bottom-cta";
import { FeatureList } from "@/features/landing/components/feature-list";
import { Hero } from "@/features/landing/components/hero";
import { LandingStats } from "@/features/landing/components/landing-stats";
import { SiteFooter } from "@/features/landing/components/site-footer";
import { SiteHeader } from "@/features/landing/components/site-header";

export const Route = createFileRoute("/")({
  component: WelcomePage,
});

function WelcomePage() {
  return (
    <main className="relative min-h-svh w-full bg-background text-foreground">
      <SiteHeader />
      <Hero />
      <LandingStats />
      <FeatureList />
      <BottomCta />
      <SiteFooter />
    </main>
  );
}
