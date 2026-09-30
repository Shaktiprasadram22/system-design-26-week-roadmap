# System Design: 26-Week Roadmap

**89 topics · 89 production scenarios · 89 practical exercises**

A complete system-design learning guide covering networking, databases, distributed systems, reliability, security, cloud infrastructure, RAG, and AI agents. Every topic includes an explanation, a realistic production scenario, and an exercise with verification criteria.

## Start reading on GitHub

1. Follow the [26-week roadmap](roadmap.md) for the weekly schedule, project deliverables, and milestones.
2. Read the phase chapters below, or use the [complete guide](complete-guide.md) for all lessons in one document.
3. Work through the [checkout and document-Q&A walkthroughs](chapters/07-production-walkthroughs-and-case-studies.md) to connect the concepts.
4. Track completion and evidence in the [89-topic progress tracker](topic-tracker.csv).

The Markdown files render directly on GitHub. PDFs are also included for offline reading and printing.

## Read by phase

| Phase | Weeks | Topics | Markdown chapter |
|---|---|---|---|
| 1. Foundations | 1–4 | 1–13 | [Networking, APIs, databases, operating systems, and storage](chapters/01-foundations.md) |
| 2. Core system design | 5–10 | 14–34 | [Scaling, caching, replication, consensus, messaging, and system design](chapters/02-core-system-design.md) |
| 3. Reliability, security, and LLD | 11–16 | 35–51 | [Resilience, recovery, observability, authorization, and component design](chapters/03-reliability-security-and-lld.md) |
| 4. Cloud and infrastructure | 17–20 | 52–63 | [Cloud, containers, serverless, storage, and safe delivery](chapters/04-cloud-and-infrastructure.md) |
| 5. AI fundamentals and RAG | 21–23 | 64–74 | [Transformers, inference, embeddings, retrieval, and evaluation](chapters/05-ai-fundamentals-and-rag.md) |
| 6. Agents and AI production | 24–26 | 75–89 | [Agents, MCP, memory, guardrails, gateways, and AI system designs](chapters/06-agents-and-ai-production.md) |

The [production walkthroughs and case studies](chapters/07-production-walkthroughs-and-case-studies.md) include two connected designs and six documented examples from GitHub, Amazon, Google, Slack, Netflix, and Uber, with primary-source references.

## Download the documents

- [Complete guide — PDF](complete-guide.pdf)
- [Weekly roadmap — PDF](roadmap.pdf)
- [Full reading package — ZIP](system-design-learning-package.zip)
- [Complete guide — editable Markdown](complete-guide.md)
- [Weekly roadmap — editable Markdown](roadmap.md)

Browser versions are available as [complete-guide.html](complete-guide.html) and [roadmap.html](roadmap.html). Download and open them locally; reference links require internet access.

## Learn through one project

The running project is **ShopStream**, an illustrative multi-tenant marketplace with a product catalogue, inventory, checkout, payments, notifications, chat, and support document search. It connects the lessons through practical requirements:

- Inventory never becomes negative.
- Repeated requests do not create duplicate effective charges.
- One tenant cannot access another tenant's private data.
- Accepted durable operations remain recoverable.
- AI answers use authorized evidence, and tools enforce permissions outside the model.

Use one backend language you already know. Start with a small application and add infrastructure when a measured problem or required failure behavior justifies it. All proposed architectures and numerical lab targets are teaching assumptions; company case studies describe the systems documented at publication time.

## Suggested pace

Budget **7–8 hours per week** for a focused first pass, extending weeks for deeper implementations. The first ten weeks cover the core track; later phases deepen reliability, cloud, and AI skills. Week 26 implements one AI capstone and reviews the other four designs.

Complete a topic when you can explain its trade-offs and demonstrate its behavior, including at least one relevant failure case. Keep diagrams, measurements, decision notes, and recovery evidence alongside your progress tracker.

## Rebuild the PDF and HTML files

The [phase chapters](chapters/) and [roadmap.md](roadmap.md) are the source documents. The build combines them into the complete guide and exports both documents to PDF and HTML.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build_documents.py
```

WeasyPrint requires its platform dependencies; see the [official installation instructions](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation). The PDF styles use DejaVu fonts. Rebuilding preserves an existing progress tracker.

## Curriculum attribution

Based on the [original implementation curriculum](https://system-design-24-week.vercel.app/), inspected on **1 October 2026**, and its linked [mental-model curriculum](https://system-design-12-week.vercel.app/). Despite the source URL saying “24-week,” the actual plan contains **26 weeks and 89 topics**.

The explanations, scenarios, exercises, weekly assignments, walkthroughs, and production corrections expand the source checklist. [curriculum.json](curriculum.json) preserves the structured source-topic mapping. Primary references appear beside the relevant lessons and case studies.
