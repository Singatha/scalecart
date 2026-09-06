export type ReadinessResponse = {
  status: "ready" | "not_ready"
  service: string
  checks: Record<string, "ready" | "unavailable">
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api"

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: { message?: string } } | null
    throw new Error(body?.error?.message ?? "We couldn't complete that request.")
  }
  return response.json() as Promise<T>
}

async function getJson<T>(path: string): Promise<T> {
  return requestJson<T>(path)
}

export async function getSystemReadiness(): Promise<ReadinessResponse> {
  return getJson<ReadinessResponse>("/system/ready")
}

export type Category = {
  id: string
  parent_id: string | null
  name: string
  slug: string
  description: string | null
  sort_order: number
  is_active: boolean
}

export type ProductSummary = {
  id: string
  name: string
  slug: string
  brand: string | null
  featured: boolean
  category: Category
  minimum_price_amount: number
  currency: string
  in_stock: boolean
  primary_image: string | null
}

export type ProductVariant = {
  id: string
  sku: string
  name: string
  price_amount: number
  compare_at_amount: number | null
  currency: string
  stock_quantity: number
  attributes: Record<string, string>
  is_active: boolean
}

export type ProductImage = {
  id: string
  url: string
  alt_text: string
  position: number
}

export type ProductDetail = ProductSummary & {
  description: string
  status: "draft" | "active" | "archived"
  variants: ProductVariant[]
  images: ProductImage[]
  created_at: string
  updated_at: string
}

export type ProductList = {
  items: ProductSummary[]
  total: number
  page: number
  page_size: number
  pages: number
}

export type ProductFilters = {
  search?: string
  category?: string
  inStock?: boolean
  sort?: "newest" | "price_asc" | "price_desc" | "name"
  page?: number
  pageSize?: number
}

export function getCategories(): Promise<Category[]> {
  return getJson<Category[]>("/categories")
}

export function getProducts(filters: ProductFilters = {}): Promise<ProductList> {
  const params = new URLSearchParams()
  if (filters.search) params.set("search", filters.search)
  if (filters.category) params.set("category", filters.category)
  if (filters.inStock) params.set("in_stock", "true")
  if (filters.sort) params.set("sort", filters.sort)
  if (filters.page) params.set("page", String(filters.page))
  if (filters.pageSize) params.set("page_size", String(filters.pageSize))
  const query = params.size ? `?${params.toString()}` : ""
  return getJson<ProductList>(`/products${query}`)
}

export function getProduct(slug: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/products/${encodeURIComponent(slug)}`)
}

export type CartItem = {
  variant_id: string
  product_id: string
  product_slug: string
  product_name: string
  variant_name: string
  sku: string
  unit_price_amount: number
  currency: string
  quantity: number
  line_total_amount: number
  available_stock: number
  is_available: boolean
  price_changed: boolean
  image_url: string | null
}

export type Cart = {
  cart_id: string | null
  items: CartItem[]
  item_count: number
  subtotal_amount: number
  currency: string | null
  expires_in: number
}

const CART_ID_KEY = "scalecart_cart_id"
const ACCESS_TOKEN_KEY = "scalecart_access_token"

function cartHeaders(): Record<string, string> {
  if (typeof localStorage === "undefined") return {}
  const token = localStorage.getItem(ACCESS_TOKEN_KEY)
  const cartId = localStorage.getItem(CART_ID_KEY)
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(cartId ? { "X-Cart-ID": cartId } : {}),
  }
}

function rememberCart(cart: Cart): Cart {
  if (cart.cart_id && typeof localStorage !== "undefined") {
    localStorage.setItem(CART_ID_KEY, cart.cart_id)
  }
  return cart
}

export async function getCart(): Promise<Cart> {
  return rememberCart(await requestJson<Cart>("/cart", { headers: cartHeaders() }))
}

export async function addCartItem(variantId: string, quantity = 1): Promise<Cart> {
  return rememberCart(await requestJson<Cart>("/cart/items", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...cartHeaders() },
    body: JSON.stringify({ variant_id: variantId, quantity }),
  }))
}

export async function updateCartItem(variantId: string, quantity: number): Promise<Cart> {
  return rememberCart(await requestJson<Cart>(`/cart/items/${variantId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...cartHeaders() },
    body: JSON.stringify({ quantity }),
  }))
}

export async function removeCartItem(variantId: string): Promise<Cart> {
  return rememberCart(await requestJson<Cart>(`/cart/items/${variantId}`, {
    method: "DELETE",
    headers: cartHeaders(),
  }))
}

export async function clearCart(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/cart`, {
    method: "DELETE",
    headers: { Accept: "application/json", ...cartHeaders() },
  })
  if (!response.ok) throw new Error("We couldn't clear your bag.")
}
