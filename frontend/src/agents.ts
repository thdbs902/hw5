import type { AgentName, AuditEvent, Draft } from './types'

export interface AgentMeta {
  name: AgentName
  title: string
  role: string
  icon: string
  color: string
}

// Each agent has its own colour + emblem so you can follow them across the floor, feed, and summary.
export const AGENTS: AgentMeta[] = [
  { name: 'boss', title: 'The Boss', role: 'Reads the ticket, picks the smallest team, signs off', icon: '👑', color: '#f5c542' },
  { name: 'inventory', title: 'Inventory', role: 'Stock, sizes, vendors, lead times', icon: '📦', color: '#2ed3b7' },
  { name: 'accounting', title: 'Accounting', role: 'Invoices, cash checks, payment requests', icon: '💵', color: '#a78bfa' },
  { name: 'facilities', title: 'Facilities', role: 'Lease, rent, landlord', icon: '🏛️', color: '#ff7a59' },
  { name: 'customer_service', title: 'Customer Service', role: 'Customer replies (drafts only)', icon: '💬', color: '#ff4fa3' },
]

export const AGENT_BY_NAME = Object.fromEntries(AGENTS.map((a) => [a.name, a])) as Record<AgentName, AgentMeta>

export type AgentStatus = 'idle' | 'working' | 'waiting' | 'done' | 'error'

export interface AgentState {
  status: AgentStatus
  doing: string
  tools: Record<string, number>
  calledBy?: AgentName
  task?: string
  summary?: string
  facts: string[]
  blockers: string[]
  drafts: Draft[]
}

export function shortArgs(args?: Record<string, unknown>): string {
  if (!args) return ''
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ')
}

const label = (a?: AgentName | null) => (a ? AGENT_BY_NAME[a]?.title ?? a : 'desk')

/** Turn one run's audit events (oldest first) into what each agent is doing right now. */
export function deriveAgents(events: AuditEvent[]): Record<AgentName, AgentState> {
  const state = Object.fromEntries(
    AGENTS.map((a): [AgentName, AgentState] => [a.name, { status: 'idle', doing: 'Off the floor', tools: {}, facts: [], blockers: [], drafts: [] }]),
  ) as Record<AgentName, AgentState>

  for (const e of events) {
    const a = e.agent ? state[e.agent] : undefined
    switch (e.event) {
      case 'run_start':
        state.boss.status = 'working'
        state.boss.doing = `Reading ticket #${e.ticket_id} and choosing the team`
        break
      case 'mcp_tool':
        if (!a || !e.tool) break
        a.tools[e.tool] = (a.tools[e.tool] ?? 0) + 1
        if (a.status === 'idle') a.status = 'working'
        a.doing = `Using ${e.tool}(${shortArgs(e.args)})`
        break
      case 'tool_refused':
        if (a) a.doing = `Refused tool ${e.tool} (not on its list)`
        break
      case 'delegate':
        if (a && e.to) {
          a.status = 'waiting'
          a.doing = `Handed a task to ${label(e.to)}`
          const t = state[e.to]
          t.status = 'working'
          t.calledBy = e.agent ?? undefined
          t.task = e.task
          t.doing = `Working on: ${e.task}`
        }
        break
      case 'agent_report':
        if (a && e.report) {
          a.status = 'done'
          a.summary = e.report.answer
          a.facts = e.report.facts ?? []
          a.blockers = e.report.blockers ?? []
          a.drafts = e.report.drafts ?? []
          a.doing = `Reported back to ${label(a.calledBy)}`
          if (a.calledBy && state[a.calledBy].status === 'waiting') {
            state[a.calledBy].status = 'working'
            state[a.calledBy].doing = `Reading ${label(e.agent)}'s report`
          }
        }
        break
      case 'run_end':
        state.boss.status = 'done'
        state.boss.summary = e.decision?.summary
        state.boss.doing = 'Signed off on the ticket'
        for (const s of Object.values(state)) if (s.status === 'working' || s.status === 'waiting') s.status = 'done'
        break
      case 'run_error':
        for (const s of Object.values(state)) if (s.status === 'working' || s.status === 'waiting') s.status = 'error'
        state.boss.doing = `Run failed: ${e.error ?? 'unknown error'}`
        break
    }
  }
  return state
}

export const DECISION_LABEL: Record<string, string> = {
  needs_human_approval: 'Needs your approval',
  waiting_on_vendor: 'Waiting on vendor',
  ready_for_human_review: 'Ready for review',
  blocked: 'Blocked',
}

export const TICKET_TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}
