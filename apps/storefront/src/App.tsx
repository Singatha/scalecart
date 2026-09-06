import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Navigate, Route, Routes } from "react-router-dom"

import { Navbar } from "@/components/navbar"
import { HomePage } from "@/pages/home-page"
import { ProductDetailPage } from "@/pages/product-detail-page"
import { ProductsPage } from "@/pages/products-page"

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/products/:slug" element={<ProductDetailPage />} />
        <Route path="/categories/:slug" element={<ProductsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <footer className="border-t border-foreground/10 px-5 py-8 text-center text-xs text-muted-foreground">
        © 2026 Common Ground Supply Co. · Powered by ScaleCart
      </footer>
    </QueryClientProvider>
  )
}
