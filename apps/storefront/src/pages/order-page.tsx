import { useQuery } from "@tanstack/react-query"
import { CheckCircle2, PackageCheck } from "lucide-react"
import { Link, useLocation, useParams } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { getOrder, type CheckoutResult, type Order } from "@/lib/api"
import { formatMoney } from "@/lib/money"

export function OrderPage() {
  const { number = "" } = useParams()
  const location = useLocation()
  const initial = (location.state as { order?: CheckoutResult } | null)?.order
  const query = useQuery({
    queryKey: ["order", number],
    queryFn: () => getOrder(number),
    initialData: initial as Order | undefined,
    enabled: Boolean(number),
  })

  if (query.isPending) return <main className="min-h-[75vh] px-5 py-24 text-center">Loading your order…</main>
  if (query.isError || !query.data) {
    return <main className="min-h-[75vh] px-5 py-24 text-center"><h1 className="font-display text-5xl">Order not found.</h1></main>
  }
  const order = query.data
  return (
    <main className="mx-auto min-h-[75vh] max-w-3xl px-5 py-16 lg:px-8">
      <div className="text-center">
        <CheckCircle2 className="mx-auto size-12 text-emerald-700" strokeWidth={1.5} />
        <p className="mt-6 text-xs font-bold uppercase tracking-widest text-muted-foreground">Order {order.number}</p>
        <h1 className="mt-3 font-display text-5xl font-medium">Thank you for your order.</h1>
        <p className="mx-auto mt-4 max-w-xl text-muted-foreground">We sent the details to {order.email}. Your order is safely recorded and is awaiting payment.</p>
      </div>
      <section className="mt-12 rounded-lg border border-foreground/10 p-6 sm:p-8">
        <div className="flex items-center gap-3"><PackageCheck className="size-5" /><h2 className="font-display text-2xl">Order summary</h2></div>
        <div className="mt-5 divide-y divide-foreground/10">
          {order.items.map((item) => (
            <div key={item.variant_id} className="flex justify-between gap-4 py-4 text-sm">
              <span>{item.product_name} · {item.variant_name} <span className="text-muted-foreground">× {item.quantity}</span></span>
              <span>{formatMoney(item.line_total_amount, order.currency)}</span>
            </div>
          ))}
        </div>
        <dl className="mt-4 space-y-2 border-t border-foreground/10 pt-4 text-sm">
          <div className="flex justify-between"><dt>Subtotal</dt><dd>{formatMoney(order.subtotal_amount, order.currency)}</dd></div>
          <div className="flex justify-between"><dt>Shipping</dt><dd>{order.shipping_amount ? formatMoney(order.shipping_amount, order.currency) : "Free"}</dd></div>
          <div className="flex justify-between pt-2 font-semibold"><dt>Total</dt><dd className="font-display text-xl">{formatMoney(order.total_amount, order.currency)}</dd></div>
        </dl>
      </section>
      <div className="mt-8 text-center"><Button asChild variant="outline"><Link to="/products">Continue shopping</Link></Button></div>
    </main>
  )
}
