import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, PackageCheck, ShieldCheck } from "lucide-react"
import { useState } from "react"
import { Link, useParams } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { getProduct } from "@/lib/api"
import { formatMoney } from "@/lib/money"

export function ProductDetailPage() {
  const { slug = "" } = useParams()
  const product = useQuery({
    queryKey: ["product", slug],
    queryFn: () => getProduct(slug),
    enabled: Boolean(slug),
  })
  const [selectedVariant, setSelectedVariant] = useState(0)

  if (product.isPending) {
    return <main className="mx-auto min-h-[75vh] max-w-7xl animate-pulse px-5 py-16 lg:px-8"><div className="aspect-[16/7] rounded-lg bg-muted" /></main>
  }
  if (product.isError || !product.data) {
    return (
      <main className="mx-auto min-h-[75vh] max-w-7xl px-5 py-24 text-center lg:px-8">
        <h1 className="font-display text-5xl">This piece could not be found.</h1>
        <Button asChild variant="outline" className="mt-8"><Link to="/products">Return to the collection</Link></Button>
      </main>
    )
  }

  const item = product.data
  const variant = item.variants[selectedVariant] ?? item.variants[0]
  return (
    <main className="mx-auto min-h-[75vh] max-w-7xl px-5 py-10 lg:px-8 lg:py-16">
      <Link to={`/categories/${item.category.slug}`} className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> {item.category.name}
      </Link>
      <div className="mt-8 grid gap-12 lg:grid-cols-[1.08fr_.92fr] lg:gap-20">
        <div className="aspect-[4/5] overflow-hidden rounded-lg bg-muted">
          {item.images[0] ? (
            <img src={item.images[0].url} alt={item.images[0].alt_text} className="size-full object-cover" />
          ) : (
            <div className="grid size-full place-items-center font-display text-8xl text-muted-foreground/30">{item.name[0]}</div>
          )}
        </div>
        <section className="py-3 lg:py-10">
          <div className="flex items-center gap-3">
            {item.featured && <Badge>Featured</Badge>}
            <span className="text-xs uppercase tracking-widest text-muted-foreground">{item.brand}</span>
          </div>
          <h1 className="mt-5 font-display text-5xl font-medium tracking-tight sm:text-6xl">{item.name}</h1>
          {variant && <p className="mt-5 text-xl">{formatMoney(variant.price_amount, variant.currency)}</p>}
          <p className="mt-8 max-w-xl leading-7 text-muted-foreground">{item.description}</p>

          {item.variants.length > 1 && (
            <fieldset className="mt-9">
              <legend className="mb-3 text-xs font-bold uppercase tracking-wider">Choose an option</legend>
              <div className="flex flex-wrap gap-2">
                {item.variants.map((option, index) => (
                  <Button key={option.id} variant={index === selectedVariant ? "default" : "outline"} onClick={() => setSelectedVariant(index)}>
                    {option.name}
                  </Button>
                ))}
              </div>
            </fieldset>
          )}

          <Button size="lg" className="mt-9 w-full" disabled>
            {variant?.stock_quantity ? "Add to bag — Phase 4" : "Currently unavailable"}
          </Button>
          <p className="mt-3 text-center text-xs text-muted-foreground">Bag and checkout arrive in the next delivery phase.</p>

          <div className="mt-10 grid gap-4 border-t border-foreground/10 pt-7 text-sm sm:grid-cols-2">
            <span className="flex items-center gap-2"><PackageCheck className="size-4" /> Carefully packed</span>
            <span className="flex items-center gap-2"><ShieldCheck className="size-4" /> Secure checkout</span>
          </div>
        </section>
      </div>
    </main>
  )
}
