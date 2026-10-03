// Shapes returned by the FastAPI backend (backend/main.py, backend/models.py).

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface LastRun {
  run_id: string
  decision_status: string
  summary: string
  agents: AgentName[]
  payments_waiting: number
  drafts: number
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string // 'open' | 'resolved'
  notes: string | null
  created_at: string
  last_run: LastRun | null
}

export interface PaymentRequest {
  ticket_id?: number
  kind: 'invoice' | 'rent' | 'purchase'
  ref_id: number
  payee: string
  amount: number
  account: string
  reason: string
  sku?: string | null
  size?: string | null
  qty?: number | null
  balance_before?: number | null
  balance_after?: number | null
  status: string
  payment_id?: number | null
  approved_by?: string | null
}

export interface Draft {
  kind: string
  to: string
  subject: string
  body: string
  status: string
}

export interface AgentReport {
  answer: string
  facts: string[]
  payment_requests: PaymentRequest[]
  drafts: Draft[]
  blockers: string[]
}

export interface DiscountDecision {
  sku: string
  qty: number
  list_price: number
  unit_cost: number
  unit_price: number
  total: number
  reason: string
}

export interface BossDecision {
  summary: string
  status: string
  next_steps: string[]
  discount?: DiscountDecision | null
}

export interface AgentCall {
  agent: AgentName
  called_by: AgentName | null
  task: string
}

export interface TicketResult {
  run_id: string
  ticket_id: number
  shop_today: string | null
  decision: BossDecision
  agent_calls: AgentCall[]
  payment_requests: PaymentRequest[]
  drafts: Draft[]
  usage: Record<string, number>
  model: string
}

export interface AuditEvent {
  at: string
  run_id: string
  ticket_id: number | null
  agent: AgentName | null
  event: string
  tool?: string
  args?: Record<string, unknown>
  result?: unknown
  to?: AgentName
  task?: string
  report?: AgentReport
  decision?: BossDecision
  usage?: Record<string, number>
  error?: string
  reason?: string
  request?: PaymentRequest
  approved_by?: string
  checking?: number
  status?: string
  reasons?: string[]
  [key: string]: unknown
}

export interface Cash {
  found: boolean
  name: string
  balance: number
  date: string
}

export interface ApprovalResult {
  paid: boolean
  payment_id: number
  kind: string
  ref_id: number
  amount: number
  balance_after: number
  paid_at: string
  ticket_id: number
  ticket_status: string
}
