"""Data types shared by the Campus Customs agent team (PydanticAI outputs + run deps)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
SPECIALISTS: tuple[str, ...] = ("inventory", "accounting", "facilities", "customer_service")


class PaymentRequest(BaseModel):
    """A payment or purchase an agent recommends. Nothing is paid until a human approves it
    (POST /api/approvals is the only thing that moves cash)."""

    kind: Literal["invoice", "rent", "purchase"]
    ref_id: int = Field(description="invoice id for 'invoice', lease id for 'rent', vendor id for 'purchase'")
    payee: str
    amount: float = Field(gt=0, description="cash only goes out, so always positive")
    account: str = "checking"
    reason: str
    sku: str | None = Field(None, description="purchase only: sku to reprint")
    size: str | None = Field(None, description="purchase only")
    qty: int | None = Field(None, description="purchase only: units to reprint; amount = qty x unit_cost")
    balance_before: float | None = Field(None, description="from check_payment")
    balance_after: float | None = Field(None, description="from check_payment; never negative")
    status: Literal["needs_human_approval", "refused_not_enough_cash", "paid"] = "needs_human_approval"
    payment_id: int | None = Field(None, description="set by the approval route once paid; agents leave it empty")
    approved_by: str | None = Field(None, description="set by the approval route; agents leave it empty")


class Draft(BaseModel):
    """A message draft. Drafts stay on the board — they are never emailed or sent to anyone."""

    kind: Literal["customer_reply", "vendor_note", "landlord_note", "internal_note"]
    to: str
    subject: str
    body: str
    status: Literal["draft"] = "draft"


class AgentReport(BaseModel):
    """What a specialist (inventory / accounting / facilities / customer service) hands back."""

    answer: str = Field(description="short answer to the task, 1-4 sentences, facts only from tools")
    facts: list[str] = Field(default_factory=list, description="key numbers/dates with their source tool")
    payment_requests: list[PaymentRequest] = Field(default_factory=list)
    drafts: list[Draft] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list, description="what stops the ticket from being finished")


class DiscountDecision(BaseModel):
    """The boss's FINAL discount decision on a price_override ticket (checked by the backend against get_pricing)."""

    sku: str
    qty: int = Field(gt=0, description="units ACTUALLY offered in the customer draft (e.g. only the in-stock units if the reprint was refused)")
    list_price: float = Field(gt=0, description="from get_pricing")
    unit_cost: float = Field(gt=0, description="from get_pricing; the price floor")
    unit_price: float = Field(gt=0, description="the decided discounted price per item; must be above unit_cost")
    total: float = Field(gt=0, description="unit_price x qty")
    reason: str = Field(description="one sentence: why this price")

    @model_validator(mode="after")
    def _total_matches(self) -> "DiscountDecision":
        if abs(self.total - round(self.unit_price * self.qty, 2)) > 0.005:
            raise ValueError(f"total {self.total} must equal unit_price x qty = {round(self.unit_price * self.qty, 2)}")
        return self


class BossDecision(BaseModel):
    """The boss's final word on one ticket."""

    summary: str = Field(description="2-5 sentences: what the ticket needs and what the team found")
    status: Literal["needs_human_approval", "waiting_on_vendor", "ready_for_human_review", "blocked"]
    next_steps: list[str] = Field(default_factory=list, description="ordered steps for the human owner")
    discount: DiscountDecision | None = Field(None, description="price_override tickets only: the boss's final discount decision")


class AgentCall(BaseModel):
    agent: AgentName
    called_by: AgentName | None
    task: str


class TicketResult(BaseModel):
    """One ticket's result as it goes on the board (output/board.json)."""

    run_id: str
    ticket_id: int
    shop_today: str | None = None
    decision: BossDecision
    agent_calls: list[AgentCall]
    payment_requests: list[PaymentRequest]
    drafts: list[Draft]
    usage: dict[str, int]
    model: str
    ticket_status: str | None = Field(None, description="open/resolved after the backend's resolution check")
    status_reasons: list[str] = Field(default_factory=list, description="why the ticket stayed open, if it did")


@dataclass
class TeamDeps:
    """Per-agent run context. Each delegation makes a child copy (one level deeper)."""

    run_id: str
    ticket_id: int
    agent: str
    today: str = ""  # desk.date_today, fetched once per run through MCP
    depth: int = 0
    chain: tuple[str, ...] = ()
    # shared across the whole ticket run (same list objects in every child)
    calls: list[AgentCall] = field(default_factory=list)
    payment_requests: list[PaymentRequest] = field(default_factory=list)
    drafts: list[Draft] = field(default_factory=list)

    def child(self, agent: str) -> "TeamDeps":
        return TeamDeps(
            run_id=self.run_id,
            ticket_id=self.ticket_id,
            agent=agent,
            today=self.today,
            depth=self.depth + 1,
            chain=self.chain + (self.agent,),
            calls=self.calls,
            payment_requests=self.payment_requests,
            drafts=self.drafts,
        )
