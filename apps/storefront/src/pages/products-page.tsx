import { useQuery } from "@tanstack/react-query"
import { Search } from "lucide-react"
import { type FormEvent, useState } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"

import { ProductCard } from "@/components/product-card"
import { Button } from "@/components/ui/button"
import { getCategories, getProducts, type ProductFilters } from "@/lib/api"

const sortOptions: Array<{ value: NonNullable<ProductFilters["sort"]>; label: string }> = [
  { value: "newest", label: "Newest" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "name", label: "Name" },
]

export function ProductsPage() {
  const { slug: categorySlug } = useParams()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get("search") ?? "")
  const sort = (params.get("sort") ?? "newest") as NonNullable<ProductFilters["sort"]>
  const inStock = params.get("stock") === "available"
  const page = Number(params.get("page") ?? "1")

  const categories = useQuery({ queryKey: ["categories"], queryFn: getCategories })
  const products = useQuery({
    queryKey: ["products", categorySlug, params.toString()],
    queryFn: () =>
      getProducts({
        category: categorySlug,
        search: params.get("search") ?? undefined,
        sort,
        inStock,
        page,
        pageSize: 12,
      }),
  })
  const activeCategory = categories.data?.find((category) => category.slug === categorySlug)

  function updateParam(name: string, value?: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(name, value)
    else next.delete(name)
    if (name !== "page") next.delete("page")
    setParams(next)
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault()
    updateParam("search", search.trim() || undefined)
  }

  return (
    <main className="mx-auto min-h-[75vh] max-w-7xl px-5 py-14 lg:px-8 lg:py-20">
      <div className="border-b border-foreground/10 pb-10">
        <p className="text-xs font-bold uppercase tracking-[.2em] text-accent-foreground">The collection</p>
        <div className="mt-4 flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <h1 className="font-display text-5xl font-medium tracking-tight sm:text-6xl">
              {activeCategory?.name ?? "Goods for daily life"}
            </h1>
            {activeCategory?.description && (
              <p className="mt-4 max-w-xl text-muted-foreground">{activeCategory.description}</p>
            )}
          </div>
          <form onSubmit={submitSearch} className="flex w-full max-w-sm items-center border-b border-foreground/30">
            <Search className="size-4 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search the collection"
              aria-label="Search products"
              className="h-11 min-w-0 flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-muted-foreground"
            />
          </form>
        </div>
      </div>

      <div className="flex flex-col gap-5 border-b border-foreground/10 py-5 lg:flex-row lg:items-center lg:justify-between">
        <nav className="flex flex-wrap gap-2" aria-label="Product categories">
          <Button asChild size="sm" variant={categorySlug ? "ghost" : "default"}>
            <Link to="/products">All</Link>
          </Button>
          {categories.data?.map((category) => (
            <Button asChild size="sm" variant={category.slug === categorySlug ? "default" : "ghost"} key={category.id}>
              <Link to={`/categories/${category.slug}`}>{category.name}</Link>
            </Button>
          ))}
        </nav>
        <div className="flex items-center gap-5 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={inStock}
              onChange={(event) => updateParam("stock", event.target.checked ? "available" : undefined)}
              className="size-4 accent-foreground"
            />
            In stock
          </label>
          <select
            value={sort}
            onChange={(event) => updateParam("sort", event.target.value)}
            aria-label="Sort products"
            className="rounded-md border border-foreground/15 bg-transparent px-3 py-2"
          >
            {sortOptions.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
          </select>
        </div>
      </div>

      {products.isPending && (
        <div className="grid gap-x-6 gap-y-10 py-10 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="aspect-[4/5] animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}
      {products.isError && (
        <div className="py-24 text-center">
          <h2 className="font-display text-3xl">The shelves are temporarily out of reach.</h2>
          <Button className="mt-6" onClick={() => products.refetch()}>Try again</Button>
        </div>
      )}
      {products.data && products.data.items.length === 0 && (
        <div className="py-24 text-center">
          <h2 className="font-display text-3xl">Nothing matched that search.</h2>
          <p className="mt-3 text-sm text-muted-foreground">Try another phrase or clear the filters.</p>
        </div>
      )}
      {products.data && products.data.items.length > 0 && (
        <>
          <div className="grid gap-x-6 gap-y-10 py-10 sm:grid-cols-2 lg:grid-cols-3">
            {products.data.items.map((product) => <ProductCard product={product} key={product.id} />)}
          </div>
          <div className="flex items-center justify-between border-t border-foreground/10 py-6 text-sm">
            <span className="text-muted-foreground">
              {products.data.total} {products.data.total === 1 ? "piece" : "pieces"}
            </span>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => updateParam("page", String(page - 1))}>
                Previous
              </Button>
              <span>{page} / {Math.max(products.data.pages, 1)}</span>
              <Button variant="outline" size="sm" disabled={page >= products.data.pages} onClick={() => updateParam("page", String(page + 1))}>
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </main>
  )
}
