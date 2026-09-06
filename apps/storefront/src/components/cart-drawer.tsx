import { Minus, Plus, ShoppingBag, Trash2, X } from "lucide-react"
import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { useCartStore } from "@/lib/cart-store"
import { formatMoney } from "@/lib/money"

export function CartDrawer() {
  const { cart, isOpen, isLoading, pendingVariantId, error, close, update, remove, clear } = useCartStore()

  if (!isOpen) return null
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Shopping bag">
      <button className="absolute inset-0 bg-foreground/35" onClick={close} aria-label="Close shopping bag" />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col bg-background shadow-2xl">
        <header className="flex h-20 items-center justify-between border-b border-foreground/10 px-6">
          <div className="flex items-center gap-3">
            <ShoppingBag className="size-5" />
            <h2 className="font-display text-2xl">Your bag</h2>
            {cart?.item_count ? <span className="text-sm text-muted-foreground">({cart.item_count})</span> : null}
          </div>
          <Button variant="ghost" size="icon" onClick={close} aria-label="Close shopping bag"><X className="size-5" /></Button>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error && <p role="alert" className="mb-4 rounded-md bg-red-100 p-3 text-sm text-red-800">{error}</p>}
          {isLoading && !cart && <p className="py-16 text-center text-sm text-muted-foreground">Loading your bag…</p>}
          {cart && cart.items.length === 0 && (
            <div className="grid min-h-80 place-items-center text-center">
              <div>
                <ShoppingBag className="mx-auto size-8 text-muted-foreground" strokeWidth={1.25} />
                <p className="mt-5 font-display text-2xl">Your bag is waiting.</p>
                <Button asChild variant="outline" className="mt-6"><Link to="/products" onClick={close}>Browse the collection</Link></Button>
              </div>
            </div>
          )}
          <div className="divide-y divide-foreground/10">
            {cart?.items.map((item) => {
              const pending = pendingVariantId === item.variant_id
              return (
                <article key={item.variant_id} className="grid grid-cols-[5.5rem_1fr] gap-4 py-5">
                  <Link to={`/products/${item.product_slug}`} onClick={close} className="aspect-[4/5] overflow-hidden rounded-md bg-muted">
                    {item.image_url ? <img src={item.image_url} alt="" className="size-full object-cover" /> : null}
                  </Link>
                  <div className="min-w-0">
                    <div className="flex justify-between gap-3">
                      <div>
                        <Link to={`/products/${item.product_slug}`} onClick={close} className="font-display text-lg font-medium hover:opacity-60">{item.product_name}</Link>
                        <p className="mt-1 text-xs text-muted-foreground">{item.variant_name}</p>
                      </div>
                      <button onClick={() => remove(item.variant_id)} disabled={pending} aria-label={`Remove ${item.product_name}`} className="self-start p-1 text-muted-foreground hover:text-foreground disabled:opacity-40">
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                    {!item.is_available && <p className="mt-2 text-xs font-semibold text-red-700">Only {item.available_stock} currently available</p>}
                    {item.price_changed && <p className="mt-2 text-xs font-semibold text-amber-700">Price updated since it was added</p>}
                    <div className="mt-4 flex items-center justify-between">
                      <div className="flex items-center rounded-full border border-foreground/15">
                        <button disabled={pending || item.quantity <= 1} onClick={() => update(item.variant_id, item.quantity - 1)} className="grid size-8 place-items-center disabled:opacity-30" aria-label={`Decrease ${item.product_name} quantity`}><Minus className="size-3" /></button>
                        <span className="w-7 text-center text-xs">{item.quantity}</span>
                        <button disabled={pending || item.quantity >= item.available_stock} onClick={() => update(item.variant_id, item.quantity + 1)} className="grid size-8 place-items-center disabled:opacity-30" aria-label={`Increase ${item.product_name} quantity`}><Plus className="size-3" /></button>
                      </div>
                      <span className="text-sm font-medium">{formatMoney(item.line_total_amount, item.currency)}</span>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        </div>

        {cart && cart.items.length > 0 && (
          <footer className="border-t border-foreground/10 px-6 py-6">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Subtotal</span>
              <strong className="font-display text-2xl">{formatMoney(cart.subtotal_amount, cart.currency ?? "ZAR")}</strong>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">Shipping and taxes are calculated at checkout.</p>
            {cart.items.every((item) => item.is_available) ? (
              <Button asChild className="mt-5 w-full" size="lg">
                <Link to="/checkout" onClick={close}>Continue to checkout</Link>
              </Button>
            ) : (
              <Button className="mt-5 w-full" size="lg" disabled>Resolve unavailable items</Button>
            )}
            <button onClick={clear} className="mt-4 w-full text-center text-xs text-muted-foreground underline-offset-4 hover:underline">Clear bag</button>
          </footer>
        )}
      </aside>
    </div>
  )
}
