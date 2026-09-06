import { Menu, ShoppingBag } from "lucide-react"
import { useEffect } from "react"
import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { useCartStore } from "@/lib/cart-store"

export function Navbar() {
  const { cart, open, load } = useCartStore()
  useEffect(() => { void load() }, [load])

  return (
    <header className="border-b border-foreground/10 bg-background/95">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 lg:px-8">
        <Link to="/" className="flex items-center gap-3" aria-label="Common Ground home">
          <span className="grid size-9 place-items-center rounded-full bg-primary text-sm font-black text-primary-foreground">CG</span>
          <span className="font-display text-xl font-semibold tracking-tight">Common Ground</span>
        </Link>
        <nav className="hidden items-center gap-8 text-sm font-medium md:flex" aria-label="Main navigation">
          <Link className="transition-opacity hover:opacity-60" to="/products">Shop</Link>
          <Link className="transition-opacity hover:opacity-60" to="/products?sort=newest">New arrivals</Link>
          <a className="transition-opacity hover:opacity-60" href="#story">Our story</a>
        </nav>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label={`Open cart${cart?.item_count ? `, ${cart.item_count} items` : ""}`} onClick={open} className="relative">
            <ShoppingBag className="size-5" />
            {cart?.item_count ? <span className="absolute right-0 top-0 grid size-5 place-items-center rounded-full bg-accent text-[10px] font-bold text-white">{cart.item_count}</span> : null}
          </Button>
          <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu"><Menu className="size-5" /></Button>
        </div>
      </div>
    </header>
  )
}
