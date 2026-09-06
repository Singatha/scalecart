export function formatMoney(amount: number, currency: string): string {
  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount / 100)
}
