import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { API, api } from './api'
import { AGENTS, AGENT_BY_NAME, DECISION_LABEL, TICKET_TYPE_LABEL, deriveAgents, shortArgs } from './agents'
import type { AgentState } from './agents'
import type { AgentName, AuditEvent, BossDecision, Cash, PaymentRequest, Ticket, TicketResult } from './types'

const money = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

/** Counts smoothly from the old balance to the new one so a payment visibly lands. */
function useAnimatedNumber(target: number | null): number | null {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    if (target == null) return
    const start = from.current ?? target
    // Nothing to animate (first load) or the tab is hidden (no animation frames): show the real number now.
    if (start === target || document.hidden) {
      from.current = target
      setShown(target)
      return
    }
    const t0 = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / 900)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(start + (target - start) * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
      else from.current = target
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target])
  return shown
}

interface Toast {
  id: number
  kind: 'ok' | 'error' | 'info'
  text: string
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [approvals, setApprovals] = useState<PaymentRequest[]>([])
  const [ledger, setLedger] = useState<AuditEvent[]>([])
  const [events, setEvents] = useState<AuditEvent[]>([]) // selected ticket, newest first (as the API returns)
  const [selectedId, setSelectedId] = useState(101)
  const [running, setRunning] = useState<{ ticketId: number; startedAt: number } | null>(null)
  const [lastResult, setLastResult] = useState<TicketResult | null>(null)
  const [offline, setOffline] = useState(false)
  const [model, setModel] = useState('')
  const [approver, setApprover] = useState(() => localStorage.getItem('cc-approver') ?? '')
  const [confirming, setConfirming] = useState<string | null>(null)
  const [paying, setPaying] = useState<string | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [celebrate, setCelebrate] = useState<number | null>(null)
  const prevStatus = useRef<Record<number, string>>({})

  const toast = useCallback((kind: Toast['kind'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, kind, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000)
  }, [])

  useEffect(() => localStorage.setItem('cc-approver', approver), [approver])

  // ---------- loading ----------
  const loadTickets = useCallback(async () => {
    const list = await api.tickets()
    const shown = list.filter((t) => [101, 102, 103].includes(t.id))
    for (const t of shown) {
      const before = prevStatus.current[t.id]
      if (before === 'open' && t.status === 'resolved') {
        setCelebrate(t.id)
        setTimeout(() => setCelebrate(null), 4000)
      }
      prevStatus.current[t.id] = t.status
    }
    setTickets(shown)
  }, [])

  const loadMoney = useCallback(async () => {
    const [c, a, l] = await Promise.all([api.cash(), api.approvals(), api.events(undefined, 500)])
    setCash(c)
    setApprovals(a)
    setLedger(l.filter((e) => ['payment_approved', 'payment_refused', 'reset'].includes(e.event)).slice(0, 8))
  }, [])

  const loadEvents = useCallback(async (ticketId: number) => {
    setEvents(await api.events(ticketId, 400))
  }, [])

  const refreshAll = useCallback(async () => {
    try {
      const h = await api.health()
      setModel(h.model)
      await Promise.all([loadTickets(), loadMoney(), loadEvents(selectedId)])
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }, [loadTickets, loadMoney, loadEvents, selectedId])

  useEffect(() => {
    refreshAll()
  }, [])

  useEffect(() => {
    loadEvents(selectedId).catch(() => setOffline(true))
  }, [selectedId, loadEvents])

  // While the team works, poll the (cheap, file-based) events route so the floor updates live.
  useEffect(() => {
    if (!running || running.ticketId !== selectedId) return
    const id = setInterval(() => loadEvents(running.ticketId).catch(() => {}), 1200)
    return () => clearInterval(id)
  }, [running, selectedId, loadEvents])

  // ---------- which run is on screen ----------
  const selected = tickets.find((t) => t.id === selectedId)
  const chronological = useMemo(() => [...events].reverse(), [events])

  const runId = useMemo(() => {
    const starts = chronological.filter((e) => e.event === 'run_start')
    if (running && running.ticketId === selectedId) {
      const mine = starts.filter((e) => Date.parse(e.at) >= running.startedAt - 3000)
      return mine.length ? mine[mine.length - 1].run_id : null
    }
    return selected?.last_run?.run_id ?? (starts.length ? starts[starts.length - 1].run_id : null)
  }, [chronological, running, selectedId, selected])

  const runEvents = useMemo(() => (runId ? chronological.filter((e) => e.run_id === runId) : []), [chronological, runId])
  const agentState = useMemo(() => deriveAgents(runEvents), [runEvents])
  const runEnd = runEvents.find((e) => e.event === 'run_end')
  const runError = runEvents.find((e) => e.event === 'run_error')
  const statusEvent = [...runEvents].reverse().find((e) => e.event === 'ticket_status')
  // A human correction of the Boss's discount (appended to the audit trail) wins over the original.
  const correction = [...runEvents].reverse().find((e) => e.event === 'decision_corrected')
  const discount = (correction?.discount as BossDecision['discount']) ?? runEnd?.decision?.discount
  const isRunningHere = running?.ticketId === selectedId
  const result = lastResult && lastResult.run_id === runId ? lastResult : null
  const drafts = result?.drafts ?? Object.values(agentState).flatMap((s) => s.drafts)
  const ticketApprovals = approvals.filter((p) => p.ticket_id === selectedId)
  const otherApprovals = approvals.filter((p) => p.ticket_id !== selectedId)

  // ---------- actions ----------
  async function startTeam(ticketId: number) {
    if (running) return
    setSelectedId(ticketId)
    setLastResult(null)
    setRunning({ ticketId, startedAt: Date.now() })
    toast('info', `Ticket #${ticketId}: the Boss is on it…`)
    try {
      const r = await api.runTeam(ticketId)
      setLastResult(r)
      toast('ok', `Ticket #${ticketId} — ${DECISION_LABEL[r.decision.status] ?? r.decision.status}`)
    } catch (err) {
      toast('error', `Run failed: ${(err as Error).message}`)
    } finally {
      setRunning(null)
      await Promise.all([loadTickets(), loadMoney(), loadEvents(ticketId)]).catch(() => setOffline(true))
    }
  }

  async function approve(p: PaymentRequest) {
    const key = `${p.ticket_id}-${p.kind}-${p.ref_id}`
    if (!approver.trim()) {
      toast('error', 'Type your name first — a human has to sign every approval.')
      return
    }
    if (confirming !== key) {
      setConfirming(key)
      return
    }
    setConfirming(null)
    setPaying(key)
    try {
      const r = await api.approve({ ticket_id: p.ticket_id!, kind: p.kind, ref_id: p.ref_id, approved_by: approver.trim() })
      toast('ok', `Paid ${money(r.amount)} to ${p.payee}. Checking is now ${money(r.balance_after)}.`)
      if (r.ticket_status === 'resolved') toast('ok', `Ticket #${r.ticket_id} resolved.`)
    } catch (err) {
      toast('error', `Refused: ${(err as Error).message}`)
    } finally {
      setPaying(null)
      await Promise.all([loadTickets(), loadMoney(), loadEvents(selectedId)]).catch(() => setOffline(true))
    }
  }

  async function resetDb() {
    if (running) return
    if (!window.confirm('Reset campus_customs_new.db to the original values? Paid requests go back to waiting.')) return
    try {
      const r = await api.reset()
      toast('info', `Working database reset. Checking back to ${money(r.checking)}.`)
    } catch (err) {
      toast('error', `Reset failed: ${(err as Error).message}`)
    }
    await refreshAll()
  }

  const balance = useAnimatedNumber(cash?.balance ?? null)
  const resolvedCount = tickets.filter((t) => t.status === 'resolved').length

  return (
    <div className="desk">
      <header className="masthead">
        <div className="brand">
          <div className="crest">CC</div>
          <div>
            <h1>
              Campus <em>Customs</em>
            </h1>
            <p className="tagline">Front Desk · New Haven · custom Yale merch</p>
          </div>
        </div>
        <div className="mast-stats">
          <div className="stat">
            <span>Shop date</span>
            <strong>{cash?.date ?? '—'}</strong>
          </div>
          <div className="stat">
            <span>Tickets resolved</span>
            <strong>
              {resolvedCount}
              <small> / {tickets.length || 3}</small>
            </strong>
          </div>
          <div className="stat">
            <span>Waiting on you</span>
            <strong className={approvals.length ? 'hot' : ''}>{approvals.length}</strong>
          </div>
          <div className={`cash-chip ${cash && cash.balance < 500 ? 'low' : ''}`}>
            <span>Checking balance</span>
            <strong>{balance == null ? '—' : money(balance)}</strong>
          </div>
        </div>
      </header>

      {offline && (
        <div className="offline">
          Can't reach the backend at <code>{API}</code>. Start it from <code>backend/</code> with{' '}
          <code>uvicorn main:app --reload --port 8000</code>, then{' '}
          <button className="link" onClick={refreshAll}>
            retry
          </button>
          .
        </div>
      )}

      <main className="grid">
        {/* ---------- tickets ---------- */}
        <section className="col tickets">
          <h2 className="eyebrow">Ticket rail</h2>
          {tickets.map((t) => (
            <article
              key={t.id}
              className={`ticket ${t.id === selectedId ? 'selected' : ''} ${t.status} ${celebrate === t.id ? 'celebrate' : ''}`}
              onClick={() => setSelectedId(t.id)}
            >
              <div className="ticket-top">
                <span className="ticket-no">#{t.id}</span>
                <span className="ticket-type">{TICKET_TYPE_LABEL[t.type] ?? t.type}</span>
              </div>
              <h3>{t.subject}</h3>
              <p className="muted">{t.requester}</p>
              <p className="ticket-notes">{t.notes}</p>
              <div className="ticket-foot">
                <span className={`pill ${t.status}`}>{t.status === 'resolved' ? '✓ Resolved' : '● Open'}</span>
                {t.last_run && t.last_run.payments_waiting > 0 && (
                  <span className="pill gold">{t.last_run.payments_waiting} to approve</span>
                )}
                {running?.ticketId === t.id && <span className="pill live">Team working</span>}
              </div>
              {t.status === 'resolved' && <div className="stamp">Resolved</div>}
            </article>
          ))}
          <button className="ghost reset" onClick={resetDb} disabled={!!running}>
            ↺ Reset working database
          </button>
        </section>

        {/* ---------- the floor ---------- */}
        <section className="col floor">
          {selected ? (
            <div className={`hero ${selected.status}`}>
              <div>
                <span className="eyebrow">
                  Ticket #{selected.id} · {TICKET_TYPE_LABEL[selected.type] ?? selected.type}
                </span>
                <h2 className="hero-title">{selected.subject}</h2>
                <div className="facts-row">
                  <span>From <b>{selected.requester}</b></span>
                  {selected.sku && <span>SKU <b>{selected.sku}</b></span>}
                  {selected.size && <span>Size <b>{selected.size}</b></span>}
                  {selected.qty != null && <span>Qty <b>{selected.qty}</b></span>}
                  {selected.lease_id != null && <span>Lease <b>#{selected.lease_id}</b></span>}
                  {selected.invoice_id != null && <span>Invoice <b>#{selected.invoice_id}</b></span>}
                </div>
                <p className="hero-notes">“{selected.notes}”</p>
              </div>
              <div className="hero-cta">
                {selected.status === 'resolved' && <div className="resolved-badge">✦ Resolved ✦</div>}
                <button className="gold-btn" onClick={() => startTeam(selected.id)} disabled={!!running}>
                  {isRunningHere ? (
                    <>
                      <span className="spinner" /> Team working…
                    </>
                  ) : selected.last_run ? (
                    'Run the team again'
                  ) : (
                    'Start the agent team'
                  )}
                </button>
                <small className="muted">
                  {model ? `${model} via Portkey · ` : ''}uses tokens · nothing is paid without you
                </small>
              </div>
            </div>
          ) : (
            <div className="hero">Loading tickets…</div>
          )}

          {celebrate === selectedId && <div className="confetti" aria-hidden>{'✦✧✦✧✦✧✦✧✦✧✦✧'.split('').map((c, i) => <i key={i} style={{ ['--i' as string]: i }}>{c}</i>)}</div>}

          <h2 className="eyebrow">The floor {runId && <span className="run-id">run {runId}</span>}</h2>
          <div className="agents">
            {AGENTS.map((a) => (
              <AgentCard key={a.name} name={a.name} state={agentState[a.name]} />
            ))}
          </div>

          <div className="split">
            <div className="panel feed">
              <h2 className="eyebrow">Live wire {isRunningHere && <span className="dot-live" />}</h2>
              {runEvents.length === 0 ? (
                <p className="muted">
                  {isRunningHere ? 'The Boss is opening the ticket…' : 'No run yet for this ticket. Start the team to watch it work.'}
                </p>
              ) : (
                <ol>
                  {[...runEvents].reverse().map((e, i) => (
                    <FeedItem key={`${e.at}-${i}`} e={e} />
                  ))}
                </ol>
              )}
            </div>

            <div className="panel summary">
              <h2 className="eyebrow">Run summary</h2>
              {runError && <p className="error-text">Run failed: {runError.error}</p>}
              {runEnd?.decision ? (
                <>
                  <div className={`decision ${runEnd.decision.status}`}>
                    {DECISION_LABEL[runEnd.decision.status] ?? runEnd.decision.status}
                  </div>
                  <p className="boss-summary">{runEnd.decision.summary}</p>
                  {discount && (
                    <div className="discount">
                      <span className="eyebrow">👑 Boss's final price</span>
                      <b>
                        {money(discount.unit_price)} each × {discount.qty} = {money(discount.total)}
                      </b>
                      <small>
                        list {money(discount.list_price)} · floor (unit cost) {money(discount.unit_cost)} · {discount.reason}
                        {correction && ' · corrected by a human to match the actual offer'}
                      </small>
                    </div>
                  )}
                  {statusEvent && (
                    <p className={`status-line ${statusEvent.status}`}>
                      Ticket {statusEvent.status === 'resolved' ? 'resolved' : 'stays open'}
                      {statusEvent.reasons && statusEvent.reasons.length > 0 && <>: {statusEvent.reasons.join('; ')}</>}
                    </p>
                  )}
                  {runEnd.decision.next_steps.length > 0 && (
                    <>
                      <h4>Next steps</h4>
                      <ol className="steps">
                        {runEnd.decision.next_steps.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ol>
                    </>
                  )}
                  <h4>Who did what</h4>
                  <ul className="who">
                    {AGENTS.filter((a) => agentState[a.name].status !== 'idle').map((a) => (
                      <li key={a.name} style={{ ['--c' as string]: a.color }}>
                        <span className="who-name">
                          {a.icon} {a.title}
                        </span>
                        <span>{agentState[a.name].summary ?? 'Worked the ticket.'}</span>
                        {Object.keys(agentState[a.name].tools).length > 0 && (
                          <span className="who-tools">{Object.keys(agentState[a.name].tools).join(' · ')}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                  {drafts.length > 0 && (
                    <>
                      <h4>Drafts on the board (never sent)</h4>
                      {drafts.map((d, i) => (
                        <details key={i} className="draft">
                          <summary>
                            <span className="pill">{d.kind.replace('_', ' ')}</span> to {d.to}: {d.subject}
                          </summary>
                          <p>{d.body}</p>
                        </details>
                      ))}
                    </>
                  )}
                  {runEnd.usage && (
                    <p className="muted tiny">
                      {runEnd.usage.requests} model calls · {runEnd.usage.tool_calls} tool calls ·{' '}
                      {runEnd.usage.total_tokens?.toLocaleString()} tokens
                    </p>
                  )}
                </>
              ) : (
                <p className="muted">{isRunningHere ? 'Summary appears when the Boss signs off.' : 'Nothing yet.'}</p>
              )}
            </div>
          </div>
        </section>

        {/* ---------- money ---------- */}
        <section className="col money">
          <div className="panel vault">
            <h2 className="eyebrow">The vault · checking</h2>
            <div className={`vault-balance ${cash && cash.balance < 500 ? 'low' : ''}`}>
              {balance == null ? '—' : money(balance)}
            </div>
            <p className="muted tiny">From cash_accounts · cash only goes out · never below $0</p>
            {ledger.length > 0 && (
              <ul className="ledger">
                {ledger.map((e, i) => (
                  <li key={i} className={e.event}>
                    {e.event === 'payment_approved' && (
                      <>
                        <span>
                          −{money(e.request?.amount)} · {e.request?.payee}
                          <small> approved by {e.approved_by}</small>
                        </span>
                        <b>{money((e.result as { balance_after?: number })?.balance_after)}</b>
                      </>
                    )}
                    {e.event === 'payment_refused' && (
                      <span>
                        Refused {money(e.request?.amount)} · <small>{e.reason}</small>
                      </span>
                    )}
                    {e.event === 'reset' && (
                      <>
                        <span>Database reset</span>
                        <b>{money(e.checking)}</b>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="panel approvals">
            <h2 className="eyebrow">Needs your signature</h2>
            <label className="signer">
              <span>Approving as</span>
              <input value={approver} onChange={(e) => setApprover(e.target.value)} placeholder="Your name" />
            </label>
            {approvals.length === 0 && <p className="muted">Nothing waiting. Agents only prepare payments — you approve them here.</p>}
            {[...ticketApprovals, ...otherApprovals].map((p) => {
              const key = `${p.ticket_id}-${p.kind}-${p.ref_id}`
              const after = cash ? cash.balance - p.amount : null
              const short = after != null && after < 0
              return (
                <div key={key} className={`approval ${p.ticket_id === selectedId ? 'mine' : ''} ${short ? 'short' : ''}`}>
                  <div className="approval-top">
                    <span className={`pill kind-${p.kind}`}>{p.kind}</span>
                    <span className="muted">ticket #{p.ticket_id}</span>
                  </div>
                  <div className="approval-amount">{money(p.amount)}</div>
                  <div className="approval-payee">to {p.payee}</div>
                  {p.kind === 'purchase' && p.sku && (
                    <div className="muted tiny">
                      {p.qty} × {p.sku} {p.size ?? ''}
                    </div>
                  )}
                  <p className="approval-reason">{p.reason}</p>
                  <div className="approval-after">
                    Checking after: <b className={short ? 'neg' : ''}>{money(after)}</b>
                  </div>
                  <button
                    className={`approve-btn ${confirming === key ? 'confirm' : ''}`}
                    disabled={short || paying === key || !!running}
                    onClick={() => approve(p)}
                  >
                    {short
                      ? 'Not enough cash'
                      : paying === key
                        ? 'Paying…'
                        : confirming === key
                          ? `Confirm: pay ${money(p.amount)}`
                          : 'Approve'}
                  </button>
                  {confirming === key && (
                    <button className="link" onClick={() => setConfirming(null)}>
                      cancel
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      </main>

      <div className="toasts">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>
            {t.text}
          </div>
        ))}
      </div>
    </div>
  )
}

function AgentCard({ name, state }: { name: AgentName; state: AgentState }) {
  const meta = AGENT_BY_NAME[name]
  const tools = Object.entries(state.tools)
  return (
    <div className={`agent ${name} ${state.status}`} style={{ ['--c' as string]: meta.color }}>
      <div className="agent-head">
        <div className="avatar">{meta.icon}</div>
        <div>
          <h3>{meta.title}</h3>
          <p className="muted tiny">{meta.role}</p>
        </div>
        <span className={`status ${state.status}`}>{state.status}</span>
      </div>
      <p className="doing">{state.doing}</p>
      {state.calledBy && name !== 'boss' && (
        <p className="tiny muted">called by {AGENT_BY_NAME[state.calledBy]?.title}</p>
      )}
      {tools.length > 0 && (
        <div className="tools">
          {tools.map(([t, n]) => (
            <span key={t} className="tool">
              {t}
              {n > 1 && <b>×{n}</b>}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function FeedItem({ e }: { e: AuditEvent }) {
  const meta = e.agent ? AGENT_BY_NAME[e.agent] : undefined
  const color = meta?.color ?? '#f5f1e6'
  const time = new Date(e.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  let body: ReactNode = e.event
  switch (e.event) {
    case 'run_start':
      body = <>opened the ticket and started the run</>
      break
    case 'mcp_tool':
      body = (
        <>
          used <span className="tool">{e.tool}</span> <code>{shortArgs(e.args)}</code>
          <details>
            <summary>result</summary>
            <pre>{JSON.stringify(e.result, null, 2)}</pre>
          </details>
        </>
      )
      break
    case 'tool_refused':
      body = <>was refused <span className="tool">{e.tool}</span> (not on its allowlist)</>
      break
    case 'delegate':
      body = (
        <>
          → handed to <b style={{ color: e.to ? AGENT_BY_NAME[e.to].color : undefined }}>{e.to && AGENT_BY_NAME[e.to].title}</b>: {e.task}
        </>
      )
      break
    case 'agent_report':
      body = <>reported: {e.report?.answer}</>
      break
    case 'run_end':
      body = <>signed off — {DECISION_LABEL[e.decision?.status ?? ''] ?? e.decision?.status}</>
      break
    case 'run_error':
      body = <>run failed: {e.error}</>
      break
    case 'payment_approved':
      body = (
        <>
          ✍️ {e.approved_by} approved {money(e.request?.amount)} to {e.request?.payee}
        </>
      )
      break
    case 'payment_refused':
      body = <>payment refused: {e.reason}</>
      break
    case 'decision_corrected':
      {
        const d = e.discount as BossDecision['discount']
        body = <>Boss's discount corrected to match the actual offer: {d?.qty} × {money(d?.unit_price)} = {money(d?.total)}</>
      }
      break
    case 'ticket_status':
      body = (
        <>
          ticket marked <b>{e.status}</b>
          {e.reasons && e.reasons.length > 0 && <> — {e.reasons.join('; ')}</>}
        </>
      )
      break
  }
  return (
    <li className={`feed-item ${e.event}`} style={{ ['--c' as string]: color }}>
      <span className="feed-time">{time}</span>
      <span className="feed-who">{meta ? `${meta.icon} ${meta.title}` : e.event.startsWith('payment') ? 'Human' : 'Desk'}</span>
      <span className="feed-body">{body}</span>
    </li>
  )
}
