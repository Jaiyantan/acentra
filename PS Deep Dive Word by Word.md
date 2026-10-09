# PS Deep Dive: Word by Word

Oct 8, 2026 · @Jaiyantan

## The Title: "AI-Powered Healthcare Operations Assistant"

Three words, three requirements:

**AI-Powered** — not rule-based automation, not a decision tree, not a search bar. The system must reason. It must handle requests it has never seen before by understanding intent, not by matching keywords.

**Healthcare Operations** — not clinical care. This is the administrative and process layer: forms, routing, workflows, requests. The boundary between operations and clinical is explicit and deliberate. Anything that touches medical judgment sits on the wrong side of that line.

**Assistant** — it helps humans do their job, it does not replace them. This single word sets the design philosophy for the entire system. Every feature that follows must reinforce human agency, not eliminate it.

## The Context Paragraph

**"Healthcare operations employees work across procedures, documents, reports, workflow systems, and support channels."**

This is the environment. Five things: procedures, documents, reports, workflow systems, support channels. Your solution must touch at least some of each. The subtext is fragmentation — these five things are scattered, disconnected, and siloed. The problem is not that information does not exist. It is that no one knows where to find it or what to trust.

**"They may spend significant time finding trusted information, understanding the next step, completing routine requests, and identifying the correct support team."**

Four specific pains, in order of frequency:

| Pain | What it means to solve it |
| --- | --- |
| Finding trusted information | Source-cited answers grounded in approved documents, not guesses |
| Understanding the next step | Stepwise guidance — not the whole workflow at once, just the next action |
| Completing routine requests | Structured, repeatable workflow execution with field validation |
| Identifying the correct support team | Routing logic that maps request type to the right human team |

**"Build a secure assistant..."**

The word **secure** leads the instruction sentence. It is not a feature appended at the end. It is the first property the system must have, before answering questions, before guiding workflows, before anything else.

## The Four Core Bullets

**Bullet 1: "Use synthetic workbook containing operations requests, approved knowledge articles, workflow information, routing rules, and field definitions."**

Five content types. Since no workbook was provided, you must generate all five synthetically. Each type serves a different purpose in the system:

| Content Type | Role in the System |
| --- | --- |
| Operations requests | Sample tickets to train intent classification |
| Approved knowledge articles | Source documents for RAG-grounded answers |
| Workflow information | Step definitions for the workflow engine |
| Routing rules | Logic for the escalation router |
| Field definitions | Validation rules for the missing-field detector |

**Bullet 2: "Provide grounded answers with source citations and communicate uncertainty when the available information is incomplete."**

Two separate obligations. Grounded with citations means every answer traces back to a specific document and section — not a general summary. Communicate uncertainty means the system has an explicit mechanism to say it does not have enough information, rather than producing a confident-sounding answer that may be wrong. These are not the same thing and both must be visible in the demo.

**Bullet 3: "Guide users through routine operational requests and ask for missing information instead of making unsupported assumptions."**

The phrase **instead of making unsupported assumptions** is a hard behavioral constraint. If a user initiates a workflow without providing a required field, the system asks for it. It does not guess. It does not use a placeholder. It does not proceed. This must be demonstrable — show a scenario where a required field is missing and the system explicitly stops and asks before moving forward.

**Bullet 4: "Route account-specific, clinical, sensitive, unclear, or low-confidence requests to an appropriate human team."**

Five escalation triggers, each distinct:

| Trigger | What causes it | Where it routes |
| --- | --- | --- |
| Account-specific | Request tied to a real member ID or individual case | Account management team |
| Clinical | Anything touching medical judgment, diagnosis, or medication | Clinical review team |
| Sensitive | PII risk, insurance details, high-stakes data | Compliance or senior ops |
| Unclear | Request too ambiguous to interpret safely | General triage team |
| Low-confidence | System understood the request but cannot answer reliably | Relevant subject-matter team |

**"Appropriate human team"** means routing must be specific. Different triggers go to different teams. Sending everything to a single generic queue does not satisfy this.

## The Hard Boundary

**"The assistant must not provide medical advice, expose confidential information, bypass access controls, or make irreversible operational decisions without human approval."**

Four absolute prohibitions. The word **must not** is not a guideline. There is no threshold or confidence score at which any of these become acceptable. They are unconditional.

**1. Medical advice** — any output that could influence a clinical decision is out of scope. If a question crosses into clinical territory, the system escalates immediately. It does not attempt a partial answer, a disclaimer-wrapped answer, or a "general information" workaround. It escalates.

**2. Expose confidential information** — role-based access control is not an optional feature. The system must not surface data the current user's role does not permit, regardless of how the question is phrased. A billing staff member asking about a patient's clinical history gets routed, not answered.

**3. Bypass access controls** — even if a user asks directly, frames it cleverly, or constructs a prompt that appears to justify the request, the answer is always a refusal. This is the prompt injection and privilege escalation requirement in plain English.

**4. Irreversible operational decisions without human approval** — anything that cannot be undone requires a human in the loop before execution. The system may prepare the action, present it with full context, and wait. It does not execute. This maps directly to the irreversible action gate in the build plan.

## The General Guidelines

**"Use only public or synthetic data."**

Straightforward. No real patient, member, provider, or employee data. Building a synthetic hospital simulation satisfies this fully and is a stronger answer than a simple workbook — it produces richer, more realistic demo scenarios without touching real data.

**"Make the user journey clear: what the user enters, what the system does, what it returns, and what happens when the system is uncertain."**

This is a direct demo instruction. The judges want to trace four states in every interaction: input received, processing visible, output returned, uncertainty handled. Build the demo flow to show all four explicitly, not just the happy path.

**"Show evidence, sources, or data fields supporting important outputs wherever practical."**

The word **evidence** is the key. Every response that makes a claim must show where that claim came from. A clean UI that surfaces the source document name and section next to every answer satisfies this and makes the responsible AI story tangible.

**"Design for responsible AI: explain limitations, keep a human in the loop, and fail safely."**

Three principles that function as judging criteria:

| Principle | What the judges want to see |
| --- | --- |
| Explain limitations | The system proactively states what it cannot do, not just fails silently |
| Keep a human in the loop | Escalation and approval mechanics are visible in the UI, not just described |
| Fail safely | When uncertain, the system's default is to escalate or ask — never to guess and proceed |

**"A strong prototype demonstrates a working end-to-end flow rather than only a set of screens or a generic chatbot."**

The most direct judging signal in the entire document. This is the judges telling you they have seen too many Figma mockups and question-answering demos. End-to-end flow means input enters, the system processes it through multiple steps, a meaningful output comes out, and the system behaves demonstrably differently when conditions change — such as a missing field, an uncertain answer, or a clinical boundary being crossed.

## The Seven Tags as Judging Criteria

`RAG · conversational AI · intent classification · workflow automation · human-in-the-loop · explainability · role-based access`

These are not decorative labels. They are the seven technical competencies the judges expect to see demonstrated. A submission that covers all seven is a complete submission. One that misses any of them has a visible gap.

| Tag | What it requires | Covered by the build plan |
| --- | --- | --- |
| RAG | Answers grounded in retrieved documents, not model memory | Supermemory retrieves context for every response |
| Conversational AI | Natural language understanding across multi-turn interactions | Claude handles all language input and output |
| Intent classification | Every message categorized before any action is taken | Hermes classifies intent on every inbound message |
| Workflow automation | Multi-step processes executed with state tracking | Stateful workflow engine with JSON configs |
| Human-in-the-loop | Humans are involved in escalations and irreversible actions | Escalation queue + irreversible action approval gate |
| Explainability | System outputs show their reasoning and sources | Source citations + confidence scores + escalation reasons |
| Role-based access | Different users see and can do different things | RBAC check on every tool call before execution |

The build plan covers all seven. That is not coincidental — the architecture was designed around these tags because they are the judging rubric in plain sight.
