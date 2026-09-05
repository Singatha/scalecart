import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { vi } from "vitest"

import App from "./App"

vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)))

test("renders the storefront foundation", () => {
  render(<MemoryRouter><App /></MemoryRouter>)
  expect(screen.getByRole("heading", { name: /useful things/i })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: /explore the collection/i })).toHaveAttribute("href", "/products")
})
