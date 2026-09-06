import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { vi } from "vitest"

import App from "@/App"

const category = {
  id: "category-1",
  parent_id: null,
  name: "Home",
  slug: "home",
  description: "Quiet goods for considered spaces.",
  sort_order: 0,
  is_active: true,
}

test("renders products returned by the catalog API", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      const body = url.includes("/categories")
        ? [category]
        : {
            items: [
              {
                id: "product-1",
                name: "Woven Linen Throw",
                slug: "woven-linen-throw",
                brand: "Common Ground",
                featured: true,
                category,
                minimum_price_amount: 129900,
                currency: "ZAR",
                in_stock: true,
                primary_image: null,
              },
            ],
            total: 1,
            page: 1,
            page_size: 12,
            pages: 1,
          }
      return { ok: true, json: async () => body } as Response
    }),
  )

  render(
    <MemoryRouter initialEntries={["/products"]}>
      <App />
    </MemoryRouter>,
  )

  expect(await screen.findByRole("heading", { name: "Woven Linen Throw" })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "View Woven Linen Throw" })).toHaveAttribute(
    "href",
    "/products/woven-linen-throw",
  )
  expect(screen.getByText("1 piece")).toBeInTheDocument()
})
