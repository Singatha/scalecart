import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import { CartDrawer } from "@/components/cart-drawer"
import { useCartStore } from "@/lib/cart-store"

test("renders cart contents and reconciled totals", () => {
  useCartStore.setState({
    isOpen: true,
    isLoading: false,
    pendingVariantId: null,
    error: null,
    cart: {
      cart_id: "cart-1",
      item_count: 2,
      subtotal_amount: 259800,
      currency: "ZAR",
      expires_in: 2592000,
      items: [
        {
          variant_id: "variant-1",
          product_id: "product-1",
          product_slug: "woven-linen-throw",
          product_name: "Woven Linen Throw",
          variant_name: "Natural",
          sku: "THROW-LINEN-NATURAL",
          unit_price_amount: 129900,
          currency: "ZAR",
          quantity: 2,
          line_total_amount: 259800,
          available_stock: 8,
          is_available: true,
          price_changed: false,
          image_url: null,
        },
      ],
    },
  })

  render(<MemoryRouter><CartDrawer /></MemoryRouter>)

  expect(screen.getByRole("dialog", { name: "Shopping bag" })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Woven Linen Throw" })).toHaveAttribute(
    "href",
    "/products/woven-linen-throw",
  )
  expect(screen.getByText("(2)")).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Continue to checkout" })).toHaveAttribute(
    "href",
    "/checkout",
  )
})
