import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { vi } from "vitest"

import { createOrder } from "@/lib/api"
import { useCartStore } from "@/lib/cart-store"
import { CheckoutPage } from "@/pages/checkout-page"

vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  createOrder: vi.fn(),
}))

test("submits delivery details and completes the cart", async () => {
  useCartStore.setState({
    hasLoaded: true,
    cart: {
      cart_id: "20000000-0000-0000-0000-000000000001",
      item_count: 1,
      subtotal_amount: 129900,
      currency: "ZAR",
      expires_in: 2592000,
      items: [{
        variant_id: "variant-1",
        product_id: "product-1",
        product_slug: "woven-linen-throw",
        product_name: "Woven Linen Throw",
        variant_name: "Natural",
        sku: "THROW-LINEN-NATURAL",
        unit_price_amount: 129900,
        currency: "ZAR",
        quantity: 1,
        line_total_amount: 129900,
        available_stock: 8,
        is_available: true,
        price_changed: false,
        image_url: null,
      }],
    },
  })
  vi.mocked(createOrder).mockResolvedValue({
    id: "order-id",
    number: "SC-20260906-ABC12345",
    customer_id: null,
    email: "buyer@example.com",
    status: "pending_payment",
    currency: "ZAR",
    subtotal_amount: 129900,
    shipping_amount: 9900,
    total_amount: 139800,
    delivery_method: "standard",
    shipping_address: {
      recipient_name: "Ada Buyer",
      line1: "14 Market Street",
      city: "Cape Town",
      region: "Western Cape",
      postal_code: "8001",
      country_code: "ZA",
    },
    items: [],
    created_at: "2026-09-06T10:00:00Z",
    updated_at: "2026-09-06T10:00:00Z",
    access_token: "tracking-token",
  })
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={["/checkout"]}>
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/orders/:number" element={<p>Order received</p>} />
      </Routes>
    </MemoryRouter>,
  )

  await user.type(screen.getByLabelText("Email"), "buyer@example.com")
  await user.type(screen.getByLabelText("Recipient name"), "Ada Buyer")
  await user.type(screen.getByLabelText("Address"), "14 Market Street")
  await user.type(screen.getByLabelText("City"), "Cape Town")
  await user.type(screen.getByLabelText("Province / region"), "Western Cape")
  await user.type(screen.getByLabelText("Postal code"), "8001")
  await user.click(screen.getByRole("button", { name: "Place order" }))

  expect(createOrder).toHaveBeenCalledWith(
    expect.objectContaining({
      email: "buyer@example.com",
      delivery_method: "standard",
    }),
    expect.any(String),
  )
  expect(await screen.findByText("Order received")).toBeInTheDocument()
  expect(useCartStore.getState().cart?.items).toEqual([])
})
