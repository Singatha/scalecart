import { ArrowUpRight } from "lucide-react"
import { Link } from "react-router-dom"

import type { ProductSummary } from "@/lib/api"
import { formatMoney } from "@/lib/money"

export function ProductCard({ product }: { product: ProductSummary }) {
  return (
    <article className="group">
      <Link to={`/products/${product.slug}`} className="block" aria-label={`View ${product.name}`}>
        <div className="relative aspect-[4/5] overflow-hidden rounded-lg bg-muted">
          {product.primary_image ? (
            <img
              src={product.primary_image}
              alt=""
              className="size-full object-cover transition duration-500 group-hover:scale-[1.025]"
            />
          ) : (
            <div className="grid size-full place-items-center bg-secondary font-display text-5xl text-muted-foreground/35">
              {product.name.slice(0, 1)}
            </div>
          )}
          {product.featured && (
            <span className="absolute left-3 top-3 rounded-full bg-background/90 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider">
              Featured
            </span>
          )}
          {!product.in_stock && (
            <span className="absolute bottom-3 left-3 rounded-full bg-foreground px-3 py-1 text-[11px] font-semibold text-background">
              Out of stock
            </span>
          )}
        </div>
        <div className="flex items-start justify-between gap-4 py-4">
          <div>
            <p className="text-xs text-muted-foreground">{product.category.name}</p>
            <h2 className="mt-1 font-display text-xl font-medium">{product.name}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {formatMoney(product.minimum_price_amount, product.currency)}
            </p>
          </div>
          <ArrowUpRight className="mt-1 size-4 opacity-0 transition group-hover:opacity-100" />
        </div>
      </Link>
    </article>
  )
}
