import type { ApprovalResult, AuditEvent, Cash, PaymentRequest, Ticket, TicketResult } from './types'

// The FastAPI backend from Problem 7.
export const API = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API + path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body)
    } catch {
      /* keep the status text */
    }
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ ok: boolean; model: string }>('/api/health'),
  tickets: () => request<Ticket[]>('/api/tickets'),
  runTeam: (ticketId: number) => request<TicketResult>(`/api/tickets/${ticketId}/run`, { method: 'POST' }),
  events: (ticketId?: number, limit = 300) =>
    request<AuditEvent[]>(`/api/events?limit=${limit}${ticketId ? `&ticket_id=${ticketId}` : ''}`),
  approvals: () => request<PaymentRequest[]>('/api/approvals'),
  approve: (body: { ticket_id: number; kind: string; ref_id: number; approved_by: string }) =>
    request<ApprovalResult>('/api/approvals', { method: 'POST', body: JSON.stringify(body) }),
  cash: () => request<Cash>('/api/cash'),
  reset: () => request<{ reset: boolean; checking: number; open_tickets: number }>('/api/reset', { method: 'POST' }),
}
