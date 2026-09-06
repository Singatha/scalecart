import { create } from "zustand"

import {
  addCartItem,
  clearCart as clearCartApi,
  getCart,
  removeCartItem,
  updateCartItem,
  type Cart,
} from "@/lib/api"

type CartState = {
  cart: Cart | null
  isOpen: boolean
  isLoading: boolean
  hasLoaded: boolean
  pendingVariantId: string | null
  error: string | null
  open: () => void
  close: () => void
  load: () => Promise<void>
  add: (variantId: string, quantity?: number) => Promise<void>
  update: (variantId: string, quantity: number) => Promise<void>
  remove: (variantId: string) => Promise<void>
  clear: () => Promise<void>
  completeCheckout: () => void
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong with your bag."
}

export const useCartStore = create<CartState>((set, get) => ({
  cart: null,
  isOpen: false,
  isLoading: false,
  hasLoaded: false,
  pendingVariantId: null,
  error: null,
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false, error: null }),
  load: async () => {
    if (get().isLoading) return
    set({ isLoading: true, error: null })
    try {
      set({ cart: await getCart() })
    } catch (error) {
      set({ error: message(error) })
    } finally {
      set({ isLoading: false, hasLoaded: true })
    }
  },
  add: async (variantId, quantity = 1) => {
    set({ pendingVariantId: variantId, error: null })
    try {
      set({ cart: await addCartItem(variantId, quantity), isOpen: true })
    } catch (error) {
      set({ error: message(error), isOpen: true })
    } finally {
      set({ pendingVariantId: null })
    }
  },
  update: async (variantId, quantity) => {
    set({ pendingVariantId: variantId, error: null })
    try {
      set({ cart: await updateCartItem(variantId, quantity) })
    } catch (error) {
      set({ error: message(error) })
    } finally {
      set({ pendingVariantId: null })
    }
  },
  remove: async (variantId) => {
    set({ pendingVariantId: variantId, error: null })
    try {
      set({ cart: await removeCartItem(variantId) })
    } catch (error) {
      set({ error: message(error) })
    } finally {
      set({ pendingVariantId: null })
    }
  },
  clear: async () => {
    set({ isLoading: true, error: null })
    try {
      await clearCartApi()
      const current = get().cart
      set({
        cart: current
          ? { ...current, items: [], item_count: 0, subtotal_amount: 0, currency: null }
          : null,
      })
    } catch (error) {
      set({ error: message(error) })
    } finally {
      set({ isLoading: false })
    }
  },
  completeCheckout: () => {
    const current = get().cart
    set({
      cart: current
        ? { ...current, items: [], item_count: 0, subtotal_amount: 0, currency: null }
        : null,
      isOpen: false,
      error: null,
    })
  },
}))
