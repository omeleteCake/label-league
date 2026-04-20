import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-4xl font-semibold tracking-normal text-balance sm:text-5xl">
        Label League
      </h1>
      <Button type="button">Coming soon</Button>
    </main>
  );
}
