# HW5 — AI Prompts Log

This file records the prompts I typed to my vibe coder (Claude Code) while working on HW5, one section per problem. Quoted blocks are my prompts exactly as I typed them; follow-up prompts include a one-sentence note on what was missing after the first prompt.

---

## Setup instructions

These are the general instructions I gave before starting the problems (not a problem prompt).

> HW5 assignment under 'YALE' folder. I'm going to work on HW5

> plz follow these rules for my HW5 Campus Customs assignment.
>
> - I am a beginner, so work one problem at a time
> - use my PORTKEY_API_KEY for AI calls
> - use only gpt-6-luna through Portkey for every agent
> - do not use any other model in my code or runs
> - use only necessary tokens because multi-agent chats burn tokens fast
> - work as fast as possible and let me know if something will take more than 3 minutes
> - keep data/campus_customs.db untouched
> - use data/campus_customs_new.db as the working copy
> - human approval is required for any payments
> - if there is not enough cash, do not allow the payment
> - no negative cash balance
> - cash only goes out in this homework
> - do not email customers or call real vendors
> - before the full run over the three tickets, reset the working database to the original values
> - shop facts should come from the MCP server and the working database
>
> plz keep updating AI_prompts.md with the prompt I actually give you.
>
> If you understand what I asked, start your answer with silver heart emoji.
>
> If there is something I need to personally check, choose, approve, click, run, or confirm, mark it with yellow heart emoji, so I know I need to do it.
>
> Otherwise use your judgment and do not keep asking me questions.
>
> do not start Problem 1 yet.

> plz explain this HW5 Campus Customs assignment to me before we start.
>
> I need to build:
> - an MCP server
> - a FastAPI backend with a multi-agent team
> - a React dashboard
>
> My agents are:
> - boss
> - inventory
> - accounting
> - facilities
> - customer service
>
> Any agent can delegate work to another agent.
>
> There are three open tickets in the database.
>
> plz explain simply:
> - what each part does
> - how the MCP server, agents, backend, and dashboard work together
> - what happens from when I choose a ticket until it is resolved
> - where human approval is needed
> - what I will build from Problem 1 to Problem 11
>
> I am a beginner so keep it simple.
> let me know if you takes more than 3 minutes.
>
> If I need to personally check something, mark it with 💛.
>
> do not change any files yet.
> do not start Problem 1 yet.

> no. I won't provide HW5 handout because this is my homework. you can just follow my prompts.
>
> plz check what I already have for HW5 before we start.
>
> check:
> - data.zip
> - data/campus_customs.db
> - data/campus_customs_new.db
> - AI_prompts.md
> - requirements.txt
> - .env
> - .gitignore
> - backend/
> - frontend/
> - mcp_server/
> - output/
>
> also check if PORTKEY_API_KEY is available but do not show my key.
>
> do not change campus_customs.db.
>
> tell me what is ready and what is missing.
>
> 💛 mark anything I need to do myself.
>
> do not start Problem 1 yet.

---

## Problem 1 — Vibe coder prompts

> if yo find something is missing, please find it by yourself. I've done the previous homework (HW4 and HW3) regarding this matter, so you know what you have to do already.
>
> plz do Problem 1: Vibe coder prompts.
>
> - create AI_prompts.md at the start of the assignment
> - keep updating it as I work
> - make one section for each problem
> - include the problem number and title
> - include at least one prompt I actually typed for each problem
> - keep my wording as much as possible
> - if I need a follow-up prompt, add that prompt too
> - if there is a follow-up, add one sentence explaining what was missing after the first prompt
> - do not invent prompts I did not type
> - do not paste the homework page or URL into the file
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> show me what you created.
>
> 💛 mark anything I need to check.
>
> do not start Problem 2 yet.

Follow-up — the first prompt did not ask me to double-check the finished file against the Problem 1 requirements, so I asked for that check:

> plz check Problem 1.
>
> make sure:
> - AI_prompts.md exists
> - Problem 1 has its own section
> - my actual prompt is there
> - my wording is kept as much as possible
> - there are no invented prompts
> - the homework page or URL is not pasted into the file
>
> fix it if something is wrong.
>
> tell me if Problem 1 is complete.
>
> 💛 mark anything I need to check.
>
> if nothing more needed,

---

## Problem 2 — Study the CC database

> plz do Problem 2: Study the CC database.
>
> - open data/campus_customs.db
> - look through every table and its fields
> - study the three open tickets and how they connect to the other tables
> - copy data/campus_customs.db to data/campus_customs_new.db
> - keep campus_customs.db untouched
> - use campus_customs_new.db as the working copy from now on
> - start output/harness.md
> - for each table, list the fields
> - add one short line on why the table matters for the agents
>
> also explain tickets 101, 102, and 103 to me simply and show which tables are related to each ticket.
>
> do not resolve the tickets yet.
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> 💛 mark anything I need to check.
>
> do not start Problem 3 yet.

Follow-up — the first prompt did not ask me to double-check Problem 2 and fix gaps, so I asked for that check:

> plz check Problem 2.
>
> fix anything missing by yourself so that my assignment is completed well.
> 💛 mark anything I need to check.
>
> if no more issue found,

---

## Problem 3 — Build the MCP server

> plz do Problem 3: Build the MCP server.
>
> - create the MCP server in mcp_server/ using FastMCP
> - use data/campus_customs_new.db
> - do not use campus_customs.db
> - do not run or connect the MCP server yet
> - create three tools that we know we will need for the three open tickets
> - use clear tool names
> - only use information from the database
> - do not invent any shop data
>
> update output/harness.md.
>
> for each MCP tool include:
> - tool name
> - which table it reads
> - which ticket it helps unlock: 101, 102, or 103
> - one short sentence explaining why the tool is useful for that ticket
>
> create mcp_server/README.md.
>
> include:
> - what the MCP server is for
> - which database it uses
> - the three tools it has
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> tell me why you chose these three tools.
>
> 💛 mark anything I need to check.
>
> do not start Problem 4 yet.

Follow-up — the first prompt did not ask me to double-check Problem 3 (or the tool names) and fix gaps, so I asked for that check:

> 1. are you sure about the tool names? if you think you're right, I'll follow you.
>
>
> plz check Problem 3.
>
> fix anything missing by yourself so that my assignment is completed well.
> 💛 mark anything I need to check.
>
> if no more issue found,

---

## Problem 4 — Add the MCP server to Claude Code and test each tool

> plz do Problem 4: Add the MCP server to Claude Code and test each tool.
>
> - add my MCP server to this project in Claude Code
> - save the connection information in .mcp.json or the correct local MCP file Claude Code uses
> - connect the MCP server
> - test each of the three MCP tools
> - use real prompts related to tickets 101, 102, and 103
> - make sure the tool outputs match data/campus_customs_new.db
> - save the evidence in output/mcp_smoke.json
>
> for every tool include:
> - the prompt I asked
> - the tool name
> - the tool output
> - whether it matches the database
>
> do not show or save any API key.
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> 💛 if I need to approve or restart something in Claude Code, tell me exactly what to do and wait for me.
>
> do not start Problem 5 yet.

Follow-up — the first prompt did not include the actual ticket questions for the tool tests, so after connecting the server I gave them:

> Ticket 101: how many Classic Bulldog Tees (CC-TEE-WHITE) in size S are in stock?
>
> Ticket 102: what rent do we owe on lease 1, to whom, and when is it due?
>
> Ticket 103: what are the unit cost and list price of the navy hoodie CC-HOOD-NAVY?
>
> continue Problem 4.

Follow-up — the earlier prompts did not ask me to double-check Problem 4 or to verify the lease due date against the original data.zip, so I asked for that:

> plz check Problem 4.
>
> fix anything missing, given all my prompts for the HW5.
> 💛 tell me if there is anything I need to check in Claude Code myself.
>
> when it comes to the lease due date, you go ahead double check the data.zip file I gave you.
>
> if no more issues come out,

---

## Problem 5 — Build the agent team and grow the MCP tools

> plz do Problem 5: Build the agent team and grow the MCP tools.
>
> build these five PydanticAI agents:
> - boss
> - inventory
> - accounting
> - facilities
> - customer service
>
> - any agent may delegate work to another agent
> - boss should decide who needs to work on each ticket
> - boss should not call every agent if they are not needed
> - use my PORTKEY_API_KEY
> - use only gpt-6-luna through Portkey for every agent
> - do not use any other model
> - use only necessary tokens
>
> put the agent prompts in backend/prompts/:
> - boss.md
> - inventory.md
> - accounting.md
> - facilities.md
> - customer_service.md
>
> put the data types in backend/models.py.
>
> write detailed prompts for each agent using the shop rules that agent needs.
>
> add more MCP tools if the agents need them to solve tickets 101, 102, and 103.
>
> all shop facts should come from the MCP server using campus_customs_new.db.
>
> do not create another shop tools layer outside MCP.
>
> shop rules:
> - desk.date_today is today
> - vendor lead times come from vendors
> - a vendor will not ship if they have an open unpaid invoice
> - human approval is required for payments
> - payment must refuse if there is not enough cash
> - no negative cash
> - cash only goes out
> - do not email customers or call real vendors
> - drafts stay on the board
>
> append agent activity to output/audit_trail.json.
> do not wipe the file each run.
>
> update output/harness.md with:
> - each agent
> - each MCP tool
> - which table each tool uses
> - a short safety section
> - token limits / avoiding unnecessary agent calls
>
> update mcp_server/README.md so the tool list is current.
>
> before finishing, check the project and make sure only gpt-6-luna through Portkey is used.
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> 💛 mark anything I need to check.
>
> do not start Problem 6 yet.

Follow-up — the first prompt did not ask me to double-check Problem 5 against all my HW5 prompts, so I asked for that check:

> plz check Problem 5.
> fix anything missing, given all my prompts for the HW5.
> 💛 tell me if there is anything I need to check in Claude Code myself.
> if no more issues come out,

---

## Problem 6 — Plan the three tickets

> plz do Problem 6: Plan the three tickets.
>
> before running the agents, write what I expect the team to do on tickets 101, 102, and 103.
>
> create output/desk_tickets.html.
>
> make tabs for:
> - 101
> - 102
> - 103
> - Cash
> - Reflection
>
> leave Cash and Reflection blank or say coming later.
>
> for each ticket, create an Expected section.
>
> for each Expected section include:
> - who Boss should call first and why
> - the agent delegations I expect
> - do not send every agent to every ticket
> - which MCP tools I expect to be used
>
> use my own simple wording and use the real ticket information from the database.
>
> do not fill Actual yet.
> do not run the agents yet.
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> 💛 show me the Expected plan for all three tickets so I can check it before we move on.
>
> do not start Problem 7 yet.

Follow-up — my Problem 6 answer said the clean full run would be in Problem 7, so I corrected it and asked for a Problem 6 check:

> one correction. the clean full run not in problem 7 but in problem 9. keep audit_trail.json append-only and keep the earlier test runs and if problem 7 testing changes the working database, restore it after testing as needed. I will trust you so don't ruin my homework and keep what I asked you with my prompts.

> plz check Problem 6.
> fix anything missing, given all my prompts for the HW5.
> 💛 tell me if there is anything I need to check in Claude Code myself.
> if no more issues come out,

---

## Problem 7 — Backend routes

> plz do Problem 7: Backend routes.
>
> in backend/main.py use FastAPI and add routes to:
> - return the three tickets and whether each is open or resolved
> - take a ticket id and run the agent team on that ticket
> - return recent agent events
> - approve a payment or purchase after a human clicks approve
> - return the current checking balance from cash_accounts
> - reset campus_customs_new.db to the original values
>
> important:
> - agents only prepare payments
> - the approval route is what actually changes cash
> - do not allow negative cash
> - if payment is made, update the relevant table
> - keep campus_customs.db untouched
>
> make sure I can start it from backend/ with:
>
> uvicorn main:app --reload --port 8000
>
> update output/harness.md with one line for each route and what it does.
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> 💛 if I need to run the backend myself, give me the exact command.
>
> do not start Problem 8 yet.

Follow-up — the first prompt did not ask me to confirm that this session could see all the campus-customs MCP tools, so I asked for that check:

> allow campus-customs
>
> plz check how many current campus-customs MCP tools this session can see.
>
> the current MCP server should have 17 tools.
>
> do not change any files.
> do not start Problem 8 yet.
>
> just tell me whether all 17 tools are available.

Follow-up — the first prompt did not ask me to double-check Problem 7 against the assignment before moving on, so I asked for that check at the start of my Problem 8 prompt (full prompt under Problem 8):

> plz check Problem 7 first.
>
> make sure everything for Problem 7 works correctly and matches the assignment.
>
> if something is wrong or missing, fix it using your judgment.
>
> if Problem 7 is already correct, move on to Problem 8.

---

## Problem 8 — React dashboard

> plz check Problem 7 first.
>
> make sure everything for Problem 7 works correctly and matches the assignment.
>
> if something is wrong or missing, fix it using your judgment.
>
> if Problem 7 is already correct, move on to Problem 8.
>
> for Problem 8:
> - build the frontend in frontend/ using React + Vite + TypeScript
> - use the backend routes from Problem 7
> - list tickets 101, 102, and 103
> - let me choose one ticket and start the agent team
> - show each agent and what they are doing
> - show which tools they use
> - show when a ticket is resolved
> - show a short summary of what each agent did
> - let a human approve a payment or purchase when asked
> - show the checking balance
> - update the checking balance after an approved payment
> - make the dashboard look good and feel like a real Campus Customs desk
> - the frontend should talk to http://localhost:8000
> - allow the Vite frontend origin on the backend
> - start the frontend with npm run dev
>
> create output/design.md with:
> - the dashboard layout
> - how the agents look different
> - how resolved tickets look
> - how cash and approvals look
> - what creative choices I made and why
>
> do not do the final three-ticket run yet.
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> 💛 mark anything I need to check, click, run, or approve myself.
>
> if you understand, start with 🩶.
>
> do not start Problem 9 yet.

Follow-up — the first prompt did not ask me to double-check Problem 8 against the assignment before moving on, so I asked for that check at the start of my Problem 9 prompt:

> plz check Problem 8 first.
>
> make sure everything for Problem 8 works correctly and matches the assignment.
>
> if something is wrong or missing, fix it using your judgment.
>
> if Problem 8 is already correct, move on to Problem 9.

---

## Problem 9 — Resolve the tickets

> plz do Problem 9: Resolve the tickets.
>
> before the full run:
> - reset data/campus_customs_new.db from data/campus_customs.db
> - make sure the reset worked
> - record the starting checking balance
>
> then run tickets:
> - 101
> - 102
> - 103
>
> run them one at a time.
>
> important:
> - do not approve any payment or purchase automatically
> - if a payment or purchase needs approval, stop and show me:
>   - ticket id
>   - what the payment or purchase is
>   - who it is for
>   - amount
>   - why it is needed
>   - current checking balance
>   - expected balance after approval
>
> 💛 wait for my approval before making the payment or purchase.
>
> for each ticket record:
> - which agents worked
> - what they delegated
> - which tools they used
> - final outcome
> - any human approval
> - cash change
>
> update output/desk_tickets.html:
> - keep the Expected sections
> - fill the Actual sections
> - fill the Cash tab with:
>   - starting checking balance
>   - cash change for each ticket
>   - reason for each cash change
>   - ending checking balance
>
> the ending checking balance must match cash_accounts.
>
> create:
> - output/resolved_tickets.json
> - output/resolved_board.html
>
> append the real runs to output/audit_trail.json.
> do not wipe the earlier audit trail.
>
> finish output/harness.md.
>
> before finishing, check that:
> - tickets 101, 102, and 103 have the correct final status
> - no blocked ticket is marked resolved
> - no payment or purchase happened without my approval
> - cash never went negative
> - the cash math matches the database
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> 💛 stop and wait for me at every human approval.
>
> if you understand, start with 🩶.
>
> do not start Problem 10 yet.

Follow-up — after ticket 101 stopped for approval, the first prompt did not ask me to re-check the run and the cash before approving, so I asked for that (and gave my Problem 10 prompt, which had to wait until the three runs were finished):

> plz double check Problem 9 and the cash before I approve ticket 101.
>
> make sure nothing is wrong.
>
> do not change anything yet.

> if no issue is found,

Follow-up — the team stopped at the ticket 101 payment request and waited for my decision:

> approve 101

Follow-up — the team stopped at the ticket 102 rent request; my first reply had a typo, so I was asked to confirm and then approved:

> approve 10

> approve 102

Follow-up — after Problems 9 and 10 were written, I thought ticket 103 needed a closer look, so I asked for a double check:

> plz double check ticket 103.
>
> I think this shall be double checked.
>
> do not change anything else.

Follow-up — the check found that 103 was marked resolved while the discount was still "pending the owner" and nobody had checked cash for the 12-hoodie reprint, so I chose to reopen it and fix it:

> B.
>
> plz reopen ticket 103 and fix it so the ticket is actually finished correctly.
>
> the Boss should make the final decision on the discount.
>
> if a reprint purchase is needed, check the cash first and follow the human approval rule.
>
> update the Problem 9 and Problem 10 files to match the real result.
>
> do not start Problem 11 yet.

Follow-up — the 103 re-run's Boss decision said 20 × $50 = $1,000 while the real offer was 8 hoodies, so I asked to keep the price and fix the decision (and then move on to Problem 11):

> plz keep the $50 price for ticket 103.
>
> fix the Boss decision so it matches the actual offer:
> 8 hoodies × $50 = $400, not 20 × $50 = $1,000.
>
> make sure all Problem 9 and Problem 10 files match the final ticket 103 result.
>
> if everything is correct after that, move on to Problem 11.
>
> 💛 only tell me if there is something I really need to check or approve myself.

---

## Problem 10 — Reflection

(I typed this together with my Problem 9 double-check prompt; it was done after the three runs finished.)

> plz do Problem 10: Reflection.
>
> use:
> - the Expected sections
> - the Actual sections
> - the Cash tab
> - the three real ticket runs
>
> fill the Reflection tab in output/desk_tickets.html.
>
> answer:
> - how I would evaluate the agents on each ticket and why
> - for each ticket, how Actual compared to Expected
> - what would have been simpler as one agent with tools and why
> - three new CC problems this agent team could solve with the tools I built
> - three new CC problems this team could not solve with the tools I built
> - for the problems it cannot solve, explain what new tools or agents would be needed
>
> use specific examples from tickets 101, 102, and 103.
>
> do not write a generic AI essay.
>
> write it in my simple and practical style.
>
> 💛 if there is something that depends on my personal opinion, mark it so I can check it.
>
> keep updating AI_prompts.md with the prompt I actually give you.
>
> do not start Problem 11 yet.

---

## Problem 11 — Submit to GitHub

> plz do Problem 11: Submit to GitHub.
>
> prepare my HW5 project for a public GitHub repo.
>
> make sure these are included:
> - AI_prompts.md
> - requirements.txt
> - .env.example
> - .gitignore
> - .mcp.json
> - README.md
> - both database files
> - mcp_server/
> - frontend/
> - backend/
> - output/
>
> important:
> - do not push my real .env
> - do not push my PORTKEY_API_KEY
> - check the project for secrets before pushing
> - include both data/campus_customs.db and data/campus_customs_new.db
> - make sure only gpt-6-luna through Portkey is used
>
> README should explain:
> - how to reset the working database
> - how to start the MCP server
> - how to start the FastAPI backend
> - how to start the React board
> - reset the database before a full three-ticket run
>
> 💛 before pushing, show me what will be committed and tell me if there is anything I need to check.
>
> after I approve, push to a public GitHub repo.
>
> save the repo URL in output/github_url.txt.
>
> keep updating AI_prompts.md with the prompt I actually give you.

Follow-up — the first prompt asked to see what would be committed before pushing; after checking the list and creating the empty public repo, I approved:

> approve push
