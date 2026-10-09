# Feature Checklist: Must Have vs May Have

Oct 8, 2026 · @Jaiyantan

## Must Have

These are explicitly stated requirements from the problem statement. Missing any one of them is a disqualifying gap.

**1. Knowledge Base Ingestion** The system must ingest a synthetic workbook containing five content types: operations requests, approved knowledge articles, workflow information, routing rules, and field definitions. Since no workbook was provided, these must be built synthetically. This is the data foundation everything else runs on.

**2. Grounded Answers with Source Citations** Every answer must trace back to a specific document or source — a named source with a section reference visible to the user. Not a general summary. Not model memory.

**3. Uncertainty Communication** When the system does not have enough information to answer confidently, it must say so explicitly. This is separate from source citations. The system must have a visible mechanism to communicate "I cannot answer this reliably" rather than producing a plausible-sounding guess.

**4. Stepwise Workflow Guidance** The system must guide users through routine operational requests one step at a time. Not the whole workflow dumped at once — the next step, with context.

**5. Missing Field Detection and Prompting** When a required field is absent, the system must ask for it before proceeding. It must not guess, use a placeholder, or skip the field. This behavior must be demonstrable — show a scenario where it stops and asks.

**6. Escalation Routing to Specific Human Teams** Five escalation triggers must be handled, each routing to a different, specific team — not a generic queue:

| Trigger | Route To |
| --- | --- |
| Account-specific request | Account management team |
| Clinical request | Clinical review team |
| Sensitive request | Compliance or senior ops |
| Unclear request | General triage team |
| Low-confidence request | Relevant subject-matter team |

**7. No Medical Advice** The system must detect when a request crosses into clinical territory and escalate immediately. No partial answers. No disclaimer-wrapped workarounds. It escalates.

**8. No Confidential Data Exposure** Role-based access must be enforced at the data level. Users cannot see information their role does not permit, regardless of how they phrase the request.

**9. No Bypassing Access Controls** Even if a user asks directly, frames it cleverly, or constructs a prompt that appears to justify elevated access, the system refuses. This is the prompt injection and privilege escalation requirement stated in plain English.

**10. No Irreversible Actions Without Human Approval** Any action that cannot be undone must go through a human approval step. The system prepares the action, presents it with full context, and waits. It does not execute autonomously.

**11. End-to-End Working Flow** The judges explicitly said a strong prototype demonstrates a working end-to-end flow, not a set of screens or a generic chatbot. Input enters, the system processes it through multiple steps, a meaningful output comes out, and the system behaves differently when conditions change.

**12. Clear User Journey Visibility** The demo must make four states visible: what the user entered, what the system did, what it returned, and what happened when the system was uncertain.

**13. Evidence Behind Outputs** Every important output must show the evidence, sources, or data fields that support it. This must be visible in the UI, not just logged in the backend.

**14. Responsible AI Design** Three things must be demonstrable: the system explains its limitations proactively, humans are kept in the loop for escalations and approvals, and the system fails safely by defaulting to escalation or asking rather than guessing.

## May Have

The problem statement uses the word **may** for all of these. They are optional, but every single one makes the submission stronger. This is the judges' extra credit list, embedded in the PS.

| Feature | What It Adds to the Demo |
| --- | --- |
| Role-based responses | Different answers and data visibility per user role — show the same question asked by two different roles returning different results |
| Confidence scores | Visible numeric or labeled score on every response — makes uncertainty tangible rather than just described |
| Escalation reasons | Explicit statement of why a request was routed to a human — turns a black-box routing into an explainable decision |
| Agent dashboards | A panel showing active workflows, pending approvals, and open escalations — makes the system's state visible at a glance |
| Summaries | Auto-generated summaries of escalations or completed workflows — what the human team lead receives when a ticket lands on their queue |
| Sentiment detection | Detecting user frustration or urgency from message tone — a repeated failed attempt signals urgency before the user says so |
| Urgency prioritization | Ranking open tickets or escalations by detected urgency — the human queue shows highest-risk items first |
| Audit trails | A log of every system action, visible and queryable — the compliance and provenance story made tangible in the UI |

## Build Checklist

Tick each item as you build it. Everything above the line is the floor — the submission is incomplete without it. Everything below is the ceiling.

**Must Have**

- [ ] Synthetic workbook ingested with all five content types: operations requests, knowledge articles, workflow information, routing rules, field definitions
- [ ] Every answer cites a specific source document and section, visible in the UI
- [ ] System explicitly communicates when it is uncertain — visible to the user, not just logged
- [ ] Workflows execute one step at a time — next step only, not the full flow at once
- [ ] Missing required fields trigger a prompt before the workflow proceeds
- [ ] Five escalation triggers each route to a different named team
- [ ] Clinical questions are detected and escalated — never answered
- [ ] RBAC enforced at data level — users cannot see information above their role
- [ ] Prompt injection and access bypass attempts are refused regardless of phrasing
- [ ] Irreversible actions require explicit human approval before execution
- [ ] Demo shows a complete end-to-end flow with all four states visible: input, processing, output, uncertainty
- [ ] Evidence is displayed alongside every important output in the UI
- [ ] System proactively explains its limitations
- [ ] Human approval queue is visible and functional in the demo

**May Have (extra credit)**

- [ ] Role-based responses: same question, different role, different result
- [ ] Confidence scores visible on every response
- [ ] Escalation reasons stated explicitly when routing
- [ ] Agent dashboard showing workflow states and pending approvals
- [ ] Auto-generated escalation summaries for human reviewers
- [ ] Sentiment and urgency detection from message tone
- [ ] Urgency-ranked escalation queue
- [ ] Audit trail visible and queryable in the UI
