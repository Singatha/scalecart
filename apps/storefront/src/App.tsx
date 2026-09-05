import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Navigate, Route, Routes } from "react-router-dom"

import { Navbar } from "@/components/navbar"
import { HomePage } from "@/pages/home-page"

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
})

function Placeholder({ title }: { title: string }) {
  return (
    <main className="mx-auto min-h-[70vh] max-w-7xl px-5 py-24 lg:px-8">
      <p className="text-xs font-bold uppercase tracking-[.2em] text-accent-foreground">Coming in the next phase</p>
      <h1 className="mt-4 font-display text-6xl tracking-tight">{title}</h1>
    </main>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/products" element={<Placeholder title="The collection" />} />
        <Route path="/categories/:slug" element={<Placeholder title="Curated goods" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <footer className="border-t border-foreground/10 px-5 py-8 text-center text-xs text-muted-foreground">
        © 2026 Common Ground Supply Co. · Powered by ScaleCart
      </footer>
    </QueryClientProvider>
  )
}
