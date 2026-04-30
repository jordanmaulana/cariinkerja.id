import { createFileRoute } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <main className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">cariinkerja.id</h1>
      <Button>Hello</Button>
    </main>
  );
}
