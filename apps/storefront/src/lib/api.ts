export type ReadinessResponse = {
  status: "ready" | "not_ready"
  service: string
  checks: Record<string, "ready" | "unavailable">
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api"

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
  })
  if (!response.ok) throw new Error("We couldn't load this part of the shop.")
  return response.json() as Promise<T>
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
