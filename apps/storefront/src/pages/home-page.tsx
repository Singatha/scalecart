import { useQuery } from "@tanstack/react-query"
import { ArrowRight, Check, Database, Leaf, PackageCheck } from "lucide-react"
import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getSystemReadiness } from "@/lib/api"

const principles = [
  { icon: Leaf, title: "Considered materials", body: "Natural, durable, and selected to age beautifully." },
  { icon: PackageCheck, title: "Made to be kept", body: "Every piece earns its place in your everyday rituals." },
  { icon: Database, title: "Built with care", body: "A resilient platform underneath a calm shopping experience." },
]

export function HomePage() {
  const readiness = useQuery({
    queryKey: ["system-readiness"],
    queryFn: getSystemReadiness,
    retry: 2,
    refetchInterval: 30_000,
  })

  const online = readiness.data?.status === "ready"

  return (
    <main>
      <section className="relative overflow-hidden border-b border-foreground/10">
        <div className="absolute -right-24 top-20 size-[28rem] rounded-full border border-foreground/10" />
        <div className="absolute -right-4 top-40 size-72 rounded-full border border-foreground/10" />
        <div className="mx-auto grid min-h-[680px] max-w-7xl items-center px-5 py-20 lg:grid-cols-[1.15fr_.85fr] lg:px-8">
          <div className="relative z-10 max-w-3xl">
            <Badge className="mb-8 gap-2 bg-secondary text-secondary-foreground">
              <span className="size-1.5 rounded-full bg-emerald-700" /> New collection · Autumn 2026
            </Badge>
            <h1 className="font-display text-6xl font-medium leading-[.94] tracking-[-0.045em] sm:text-7xl lg:text-[6.6rem]">
              Useful things,<br /><em className="font-normal text-accent-foreground">thoughtfully made.</em>
            </h1>
            <p className="mt-8 max-w-xl text-lg leading-8 text-muted-foreground">
              Quiet, enduring goods for home and daily life. Sourced with curiosity and chosen for the long haul.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Button asChild size="lg"><Link to="/products">Explore the collection <ArrowRight className="ml-2 size-4" /></Link></Button>
              <Button asChild size="lg" variant="outline"><a href="#story">Meet the makers</a></Button>
            </div>
          </div>
          <div className="relative mt-16 min-h-80 lg:mt-0">
            <div className="absolute left-1/2 top-1/2 aspect-[4/5] w-64 -translate-x-1/2 -translate-y-1/2 rotate-6 rounded-[8rem_8rem_2rem_2rem] bg-[#bd5e3f] shadow-2xl shadow-[#8f422b]/20 sm:w-72" />
            <div className="absolute left-[18%] top-[20%] h-56 w-40 -rotate-12 rounded-[5rem_5rem_1.5rem_1.5rem] border-[18px] border-[#d7c6a1] bg-background shadow-xl" />
            <div className="absolute bottom-[12%] right-[9%] size-44 rounded-full bg-[#73806a] shadow-xl sm:size-52">
              <span className="absolute left-1/2 top-1/2 size-16 -translate-x-1/2 -translate-y-1/2 rounded-full border border-background/50" />
            </div>
          </div>
        </div>
      </section>

      <section id="story" className="mx-auto max-w-7xl px-5 py-24 lg:px-8">
        <div className="grid gap-px overflow-hidden rounded-lg border border-foreground/10 bg-foreground/10 md:grid-cols-3">
          {principles.map(({ icon: Icon, title, body }) => (
            <Card key={title} className="rounded-none border-0 p-3">
              <CardHeader>
                <Icon className="mb-8 size-6" strokeWidth={1.5} />
                <CardTitle>{title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm leading-6 text-muted-foreground">{body}</CardContent>
            </Card>
          ))}
        </div>
        <div className="mt-8 flex items-center justify-between border-t border-foreground/10 pt-5 text-xs text-muted-foreground">
          <span>Platform status</span>
          <span className="flex items-center gap-2" role="status">
            {online ? <Check className="size-3.5 text-emerald-700" /> : <span className="size-2 animate-pulse rounded-full bg-amber-600" />}
            {online ? "Storefront, API gateway, and database are ready" : "Checking services…"}
          </span>
        </div>
      </section>
    </main>
  )
}

