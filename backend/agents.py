"""Campus Customs agent team (PydanticAI): boss + inventory + accounting + facilities + customer service.

- Model: gpt-6-luna (OpenAI) through Portkey, using PORTKEY_API_KEY. No other model, no override.
- Shop facts: ONLY the campus-customs MCP server (mcp_server/server.py -> data/campus_customs_new.db).
  Each agent sees just the MCP tools it needs; nobody gets record_payment (humans approve payments).
- Delegation: every agent has a `delegate` tool. The boss picks who works on a ticket; specialists may
  ask one other specialist (max depth 2, no loops, max 5 agent calls per ticket).
- Prompts: backend/prompts/*.md   Types: backend/models.py   Audit: output/audit_trail.json
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Any, Literal

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from fastmcp import Client  # noqa: E402
from fastmcp.client.transports import PythonStdioTransport  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, RunContext, Tool  # noqa: E402
from pydantic_ai.mcp import MCPToolset  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.tools import ToolDefinition  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

import audit  # noqa: E402
import board  # noqa: E402
from models import SPECIALISTS, AgentCall, AgentReport, BossDecision, TeamDeps, TicketResult  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPTS = HERE / "prompts"
MCP_SERVER = ROOT / "mcp_server" / "server.py"

MODEL_NAME = "gpt-6-luna"  # the only model allowed in HW5 — deliberately not configurable
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# ---------- token / call budget (one ticket = one budget shared by every agent) ----------
LIMITS = UsageLimits(request_limit=18, tool_calls_limit=30, total_tokens_limit=90_000)
SETTINGS = OpenAIResponsesModelSettings(max_tokens=1_500, openai_reasoning_effort="low")
MAX_DEPTH = 2  # boss (0) -> specialist (1) -> specialist (2); depth-2 agents cannot delegate
MAX_AGENT_CALLS = 5  # per ticket

# ---------- which MCP tools each agent may see ----------
MCP_TOOLS: dict[str, set[str]] = {
    "boss": {"get_ticket", "list_open_tickets", "get_pricing"},  # ticket + date handed over up front; pricing for the discount decision
    "inventory": {"get_desk", "check_stock", "get_stock_all_sizes", "list_vendors", "vendor_shipping_status", "get_pricing"},
    "accounting": {
        "get_desk", "get_invoice", "list_open_invoices", "get_cash_balance", "check_payment",
        "list_payments", "get_lease", "get_pricing", "vendor_shipping_status",
    },
    "facilities": {"get_desk", "get_lease", "get_cash_balance"},
    "customer_service": {"get_desk", "get_ticket", "check_stock", "get_stock_all_sizes", "get_pricing"},
}
HUMAN_ONLY_TOOLS = {"record_payment", "set_ticket_status"}  # only the FastAPI routes call these
assert not any(HUMAN_ONLY_TOOLS & tools for tools in MCP_TOOLS.values()), "agents must never get record_payment"


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna through Portkey's OpenAI-compatible gateway."""
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set (checked HW5/.env and YALE/.env)")
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key, "x-portkey-provider": "openai"},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def build_mcp_client() -> Client:
    """One stdio connection to the campus-customs MCP server, shared by every agent in a run."""
    env = {k: os.environ[k] for k in ("PATH", "HOME", "CC_DB_PATH") if k in os.environ}
    return Client(PythonStdioTransport(str(MCP_SERVER), env=env, python_cmd=sys.executable, cwd=str(ROOT)))


async def _audited_call(ctx: RunContext[TeamDeps], call_tool: Any, name: str, args: dict[str, Any]) -> Any:
    """Every MCP tool call goes through here: allowlist check, then the real call, then the audit trail."""
    d = ctx.deps
    if name not in MCP_TOOLS[d.agent]:
        audit.log("tool_refused", run_id=d.run_id, ticket_id=d.ticket_id, agent=d.agent, tool=name, args=args)
        return {"error": f"{name} is not available to {d.agent}"}
    result = await call_tool(name, args)
    audit.log("mcp_tool", run_id=d.run_id, ticket_id=d.ticket_id, agent=d.agent, tool=name, args=args, result=result)
    return result


def _toolset_for(agent: str, mcp: MCPToolset) -> Any:
    allowed = MCP_TOOLS[agent]
    return mcp.filtered(lambda ctx, tool_def: tool_def.name in allowed)


# ---------- delegation ----------


def _merge(deps: TeamDeps, report: AgentReport) -> None:
    """Collect payment requests and drafts from every report onto the ticket (no duplicates)."""
    seen = {(p.kind, p.ref_id) for p in deps.payment_requests}
    for p in report.payment_requests:
        if (p.kind, p.ref_id) not in seen:
            deps.payment_requests.append(p)
            seen.add((p.kind, p.ref_id))
    seen_d = {(x.kind, x.to, x.subject) for x in deps.drafts}
    for x in report.drafts:
        if (x.kind, x.to, x.subject) not in seen_d:
            deps.drafts.append(x)
            seen_d.add((x.kind, x.to, x.subject))


def _make_delegate_tool(owner: str) -> Tool:
    targets = tuple(a for a in SPECIALISTS if a != owner)

    async def delegate(ctx: RunContext[TeamDeps], agent: str, task: str) -> dict:
        """Hand one focused task to another agent and get its short report back.
        Only delegate when that agent's tools or rules are really needed for this ticket.

        Args:
            agent: which agent should do the task.
            task: one clear task with the ids/sku/size/amount it needs (the other agent cannot see your chat).
        """
        d = ctx.deps
        if agent not in targets or agent in d.chain or agent == d.agent:
            return {"error": f"{d.agent} cannot delegate to {agent} (no self-calls or loops)."}
        if d.depth >= MAX_DEPTH:
            return {"error": "Delegation depth limit reached; finish with what you have."}
        if len(d.calls) >= MAX_AGENT_CALLS:
            return {"error": "Agent-call budget for this ticket is used up; finish with what you have."}
        d.calls.append(AgentCall(agent=agent, called_by=d.agent, task=task))
        audit.log("delegate", run_id=d.run_id, ticket_id=d.ticket_id, agent=d.agent, to=agent, task=task)
        child = d.child(agent)
        result = await AGENTS[agent].run(
            f"Shop today (desk.date_today): {d.today}\nTicket {d.ticket_id}. Task from {d.agent}: {task}",
            deps=child,
            usage=ctx.usage,
            usage_limits=LIMITS,
        )
        report: AgentReport = result.output
        _merge(d, report)
        audit.log("agent_report", run_id=d.run_id, ticket_id=d.ticket_id, agent=agent, report=report.model_dump())
        # keep the hand-back small: drafts/payments are already collected on the ticket
        return {
            "agent": agent,
            "answer": report.answer,
            "facts": report.facts,
            "blockers": report.blockers,
            "payment_requests": [f"{p.kind} {p.ref_id}: ${p.amount:,.2f} to {p.payee} ({p.status})" for p in report.payment_requests],
            "drafts": [f"{x.kind} to {x.to}: {x.subject}" for x in report.drafts],
        }

    delegate.__annotations__["agent"] = Literal[targets]  # the model can only pick a real teammate

    async def hide_when_too_deep(ctx: RunContext[TeamDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
        return tool_def if ctx.deps.depth < MAX_DEPTH else None

    return Tool(delegate, takes_ctx=True, prepare=hide_when_too_deep)


# ---------- the team ----------

_model = None
_mcp_client: Client | None = None
_mcp: MCPToolset | None = None
AGENTS: dict[str, Agent] = {}


def build_team() -> None:
    global _model, _mcp_client, _mcp
    if AGENTS:
        return
    _model = build_model()
    _mcp_client = build_mcp_client()
    _mcp = MCPToolset(_mcp_client, process_tool_call=_audited_call, max_retries=1)
    for name in ("boss", *SPECIALISTS):
        AGENTS[name] = Agent(
            _model,
            name=name,
            deps_type=TeamDeps,
            output_type=BossDecision if name == "boss" else AgentReport,
            instructions=(PROMPTS / f"{name}.md").read_text(encoding="utf-8"),
            toolsets=[_toolset_for(name, _mcp)],
            tools=[_make_delegate_tool(name)],
            model_settings=SETTINGS,
            retries=1,
        )


def _usage_dict(u: Any) -> dict[str, int]:
    return {
        "requests": u.requests,
        "tool_calls": u.tool_calls,
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "total_tokens": u.input_tokens + u.output_tokens,
    }


async def run_ticket(ticket_id: int) -> TicketResult:
    """Run the team on one ticket. Writes the result to output/board.json and every step to the audit trail."""
    build_team()
    run_id = uuid.uuid4().hex[:10]
    deps = TeamDeps(run_id=run_id, ticket_id=ticket_id, agent="boss")
    async with _mcp:  # one MCP server process for the whole ticket
        # Give the boss the ticket and shop date up front (fetched through MCP) so it does not spend calls on them.
        ticket = await _mcp_client.call_tool("get_ticket", {"ticket_id": ticket_id})
        desk = await _mcp_client.call_tool("get_desk", {})
        ticket, desk = ticket.data, desk.data
        deps.today = desk["date_today"]
        audit.log("run_start", run_id=run_id, ticket_id=ticket_id, agent="boss", model=MODEL_NAME, ticket=ticket, desk=desk)
        if not ticket.get("found"):
            raise ValueError(f"Ticket {ticket_id} not found")
        try:
            result = await AGENTS["boss"].run(
                f"Shop today (desk.date_today): {desk['date_today']}\nTicket: {ticket}",
                deps=deps,
                usage_limits=LIMITS,
            )
        except Exception as err:
            audit.log("run_error", run_id=run_id, ticket_id=ticket_id, agent="boss", error=f"{type(err).__name__}: {err}")
            raise
    out = TicketResult(
        run_id=run_id,
        ticket_id=ticket_id,
        shop_today=desk["date_today"],
        decision=result.output,
        agent_calls=[AgentCall(agent="boss", called_by=None, task=f"triage ticket {ticket_id}"), *deps.calls],
        payment_requests=deps.payment_requests,
        drafts=deps.drafts,
        usage=_usage_dict(result.usage),
        model=MODEL_NAME,
    )
    audit.log("run_end", run_id=run_id, ticket_id=ticket_id, agent="boss", decision=out.decision.model_dump(),
              agents_called=[c.agent for c in deps.calls], payment_requests=len(out.payment_requests),
              drafts=len(out.drafts), usage=out.usage)
    _save_to_board(out)
    return out


def _save_to_board(result: TicketResult) -> None:
    """Drafts and payment requests stay on the board (latest result per ticket); nothing is sent anywhere."""
    with board.lock:
        b = board.load()
        b[str(result.ticket_id)] = result.model_dump()
        board.save(b)


__all__ = ["run_ticket", "build_team", "AGENTS", "MCP_TOOLS", "MODEL_NAME"]
