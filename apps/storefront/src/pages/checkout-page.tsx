import { ArrowLeft, LockKeyhole } from "lucide-react"
import { type FormEvent, useEffect, useState } from "react"
import { Link, Navigate, useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { createOrder, type CheckoutDetails } from "@/lib/api"
import { useCartStore } from "@/lib/cart-store"
import { formatMoney } from "@/lib/money"

const fieldClass = "mt-1 h-11 w-full rounded-md border border-foreground/20 bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"

export function CheckoutPage() {
  const { cart, hasLoaded, load, completeCheckout } = useCartStore()
  const [checkoutCart, setCheckoutCart] = useState(cart)
  const navigate = useNavigate()
  const [deliveryMethod, setDeliveryMethod] = useState<"standard" | "express">("standard")
  const [idempotencyKey] = useState(() => crypto.randomUUID())
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!hasLoaded) void load()
  }, [hasLoaded, load])
  useEffect(() => {
    if (!checkoutCart && cart) setCheckoutCart(cart)
  }, [cart, checkoutCart])

  if (!hasLoaded && !checkoutCart) {
    return <main className="min-h-[75vh] px-5 py-24 text-center">Loading checkout…</main>
  }
  if (!checkoutCart?.items.length) return <Navigate to="/products" replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    const data = new FormData(event.currentTarget)
    const details: CheckoutDetails = {
      email: String(data.get("email")),
      delivery_method: deliveryMethod,
      shipping_address: {
        recipient_name: String(data.get("recipient_name")),
        line1: String(data.get("line1")),
        line2: String(data.get("line2")) || null,
        city: String(data.get("city")),
        region: String(data.get("region")),
        postal_code: String(data.get("postal_code")),
        country_code: String(data.get("country_code")),
        phone: String(data.get("phone")) || null,
      },
    }
    try {
      const order = await createOrder(details, idempotencyKey)
      navigate(`/orders/${order.number}`, { state: { order } })
      completeCheckout()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Checkout could not be completed.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto min-h-[75vh] max-w-6xl px-5 py-10 lg:px-8 lg:py-16">
      <Link to="/products" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Continue shopping
      </Link>
      <div className="mt-8 grid gap-12 lg:grid-cols-[1fr_22rem] lg:gap-20">
        <form onSubmit={submit} className="space-y-9">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Secure checkout</p>
            <h1 className="mt-3 font-display text-5xl font-medium">Delivery details</h1>
          </div>
          {error && <p role="alert" className="rounded-md bg-red-100 p-3 text-sm text-red-800">{error}</p>}
          <section className="grid gap-5 sm:grid-cols-2">
            <label className="text-sm sm:col-span-2">Email<input required type="email" name="email" autoComplete="email" className={fieldClass} /></label>
            <label className="text-sm sm:col-span-2">Recipient name<input required name="recipient_name" autoComplete="name" className={fieldClass} /></label>
            <label className="text-sm sm:col-span-2">Address<input required name="line1" autoComplete="address-line1" className={fieldClass} /></label>
            <label className="text-sm sm:col-span-2">Apartment, suite, etc. <span className="text-muted-foreground">(optional)</span><input name="line2" autoComplete="address-line2" className={fieldClass} /></label>
            <label className="text-sm">City<input required name="city" autoComplete="address-level2" className={fieldClass} /></label>
            <label className="text-sm">Province / region<input required name="region" autoComplete="address-level1" className={fieldClass} /></label>
            <label className="text-sm">Postal code<input required name="postal_code" autoComplete="postal-code" className={fieldClass} /></label>
            <label className="text-sm">Country code<input required name="country_code" defaultValue="ZA" minLength={2} maxLength={2} autoComplete="country" className={fieldClass} /></label>
            <label className="text-sm sm:col-span-2">Phone <span className="text-muted-foreground">(optional)</span><input name="phone" type="tel" autoComplete="tel" className={fieldClass} /></label>
          </section>
          <fieldset>
            <legend className="font-display text-2xl">Delivery</legend>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {(["standard", "express"] as const).map((method) => (
                <label key={method} className={`cursor-pointer rounded-lg border p-4 ${deliveryMethod === method ? "border-primary ring-1 ring-primary" : "border-foreground/15"}`}>
                  <input className="sr-only" type="radio" name="delivery_method" value={method} checked={deliveryMethod === method} onChange={() => setDeliveryMethod(method)} />
                  <span className="block text-sm font-semibold capitalize">{method} delivery</span>
                  <span className="mt-1 block text-xs text-muted-foreground">{method === "standard" ? "Free over R1,500 · otherwise R99" : "R199"}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <Button type="submit" size="lg" className="w-full" disabled={submitting || checkoutCart.items.some((item) => !item.is_available)}>
            <LockKeyhole className="mr-2 size-4" /> {submitting ? "Placing order…" : "Place order"}
          </Button>
          <p className="text-center text-xs text-muted-foreground">Payment authorization is introduced in Phase 6. This order will await payment.</p>
        </form>

        <aside className="h-fit rounded-lg border border-foreground/10 bg-secondary/35 p-6 lg:sticky lg:top-8">
          <h2 className="font-display text-2xl">Order summary</h2>
          <div className="mt-5 divide-y divide-foreground/10">
            {checkoutCart.items.map((item) => (
              <div key={item.variant_id} className="flex justify-between gap-4 py-3 text-sm">
                <span>{item.product_name} <span className="text-muted-foreground">× {item.quantity}</span></span>
                <span>{formatMoney(item.line_total_amount, item.currency)}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-between border-t border-foreground/10 pt-4 font-semibold">
            <span>Cart subtotal</span><span>{formatMoney(checkoutCart.subtotal_amount, checkoutCart.currency ?? "ZAR")}</span>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Shipping is finalized when the order is placed. Product prices include applicable taxes.</p>
        </aside>
      </div>
    </main>
  )
}
