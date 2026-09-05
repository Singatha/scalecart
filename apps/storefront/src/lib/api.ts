export type ReadinessResponse = {
  status: "ready" | "not_ready"
  service: string
  checks: Record<string, "ready" | "unavailable">
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api"

export async function getSystemReadiness(): Promise<ReadinessResponse> {
  const response = await fetch(`${API_BASE_URL}/system/ready`, {
    headers: { Accept: "application/json" },
  })
  if (!response.ok) throw new Error("The platform is still starting.")
  return response.json() as Promise<ReadinessResponse>
}

