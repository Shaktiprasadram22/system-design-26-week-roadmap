## Phase 5 — AI Fundamentals & RAG

The website assigns Weeks 21–23 to this phase. Use the marketplace's authorized support documents as the first AI dataset. Retrieval-augmented generation (RAG) retrieves relevant evidence and supplies it to a language model before generation. It improves access to current knowledge, but does not guarantee truthful answers or authorize access to data. The examples below describe a proposed ShopStream architecture, not a claimed deployment at a real company. Numerical acceptance criteria are teaching targets.

### 64. Transformer architecture

*Attention, embeddings, tokens.*

A tokenizer converts text into identifiers from a vocabulary; tokens can be words, word fragments, punctuation, or other units. Embeddings turn those identifiers into vectors. Position information represents sequence order. Attention computes how strongly each token should incorporate information from other tokens, using query, key, and value projections. Multiple attention heads capture different relationships, and feed-forward layers transform the resulting representations. Residual connections and normalization help training. Decoder-only language models use causal attention so a position cannot read future tokens when predicting the next token. The original Transformer paper used an encoder–decoder architecture; today's models include several architectural variants. [Original Transformer paper](https://arxiv.org/abs/1706.03762).

**Production scenario.** ShopStream asks a model to summarize a return policy. Attention lets the answer connect “30 days” with “unopened items,” even when those phrases appear in different sentences. This statistical relationship is useful, but it does not establish whether the policy is current, approved, or applicable to this customer. Those checks belong to retrieval and application logic.

**Build and verify.** Tokenize English, Hindi, product identifiers, and JSON. Inspect token counts and implement a tiny causal-attention example. Verify that changing a future token cannot change an earlier position's output; explain why long documents consume more processing resources than short ones.

### 65. LLM inference pipeline

*Tokenization → decode → output.*

An inference request passes through validation, tokenization, scheduling, model execution, decoding, and output serialization. For a conventional autoregressive Transformer, **prefill** processes the input prompt and produces reusable attention state; **decode** then generates new tokens sequentially. A decoding policy chooses from predicted token probabilities: greedy selection chooses the highest probability, while sampling introduces controlled variation. Generation stops at a termination token, configured limit, cancellation, or service deadline. Chat models also require the correct message template. These stages mean tokenization, model decoding, and conversion of tokens back into text are distinct operations. [Hugging Face text generation guide](https://huggingface.co/docs/transformers/main/llm_tutorial).

**Production scenario.** ShopStream's support assistant receives a question, retrieves policy evidence, constructs a prompt, and streams its answer. Measure queue time and **time to first token (TTFT)** separately from inter-token latency and complete-response latency. A response that begins quickly but emits tokens slowly feels different from one that waits before producing a fast burst. Retrieval can dominate TTFT even when model serving is efficient.

**Build and verify.** Instrument those stages independently. Compare short and long prompts with equal output limits, then compare short and long outputs. Cancel a stream halfway through and verify that backend generation stops, capacity is released, and the conversation records an interrupted response.

### 66. Context windows & KV cache

*Memory management in LLMs.*

The context window bounds the tokens a model can process for an interaction, subject to the model and serving configuration. System instructions, conversation history, retrieved passages, tool results, and generated output compete for that budget. A larger advertised limit does not guarantee that every fact in a long prompt will be used reliably. A **key–value cache** stores attention projections from previous tokens so decoding can reuse them. It improves computation efficiency while consuming memory. Cache memory generally grows with active sequence count and sequence length; architecture, precision, attention heads, sliding-window behavior, and parallelism affect the exact size. [Hugging Face cache strategies](https://huggingface.co/docs/transformers/main/kv_cache).

**Production scenario.** ShopStream retains the last few conversational turns, a summary, and selected policy excerpts. Sending every historical message would increase prefill work, crowd out evidence, and reduce concurrent GPU capacity. The application reserves output space before adding retrieved passages. It preserves exact order identifiers in structured state because a lossy summary might omit them.

**Build and verify.** Create a token-budget allocator with priorities and explicit truncation rules. Load-test increasing conversation lengths while recording KV memory and concurrency. Verify that over-budget requests produce a controlled result, and that critical identifiers and required evidence survive summarization and pruning.

### 67. Model serving (vLLM, TGI)

*Batching, quantization, VRAM.*

Model serving turns inference code into an admission-controlled service. GPU memory must accommodate model weights, KV caches, temporary workspaces, and runtime overhead. Weight size alone is insufficient for capacity planning. Continuous batching allows new requests to join as others finish; scheduling must balance throughput against interactive latency. Quantization reduces numerical precision to save memory or compute, but requires compatible hardware and kernels, and quality must be re-evaluated. vLLM documents continuous batching, PagedAttention, prefix caching, and quantization support. Hugging Face currently marks TGI as being in maintenance mode and points users toward alternative engines, including vLLM and SGLang. [vLLM documentation](https://docs.vllm.ai/en/latest/), [TGI status](https://huggingface.co/docs/text-generation-inference/main/en/index).

**Production scenario.** ShopStream runs interactive support traffic separately from overnight catalog enrichment. Long batch prompts can otherwise occupy resources needed for chat. Admission limits account for token demand and available cache memory; overload produces bounded queueing or a retryable response. Replica readiness waits for model loading and a warm-up request.

**Build and verify.** Serve one appropriately licensed small model. Benchmark concurrency, prompt lengths, output lengths, TTFT, token latency, and memory. Compare two supported precisions on the same evaluation questions. Pick the configuration that meets measured quality and latency targets, then test overload and replica restart behavior.

### 68. Prompt engineering

*Zero-shot, few-shot, CoT, ReAct.*

Zero-shot prompting describes the task without examples. Few-shot prompting adds representative input/output demonstrations, including difficult cases. Chain-of-thought (CoT) research explores intermediate reasoning demonstrations; it does not mean every production API should demand or expose a model's private reasoning. Request concise explanations or verifiable calculations when useful, and judge correctness through evidence and outcomes. ReAct combines reasoning with actions and observations, enabling iterative tool use. It introduces an execution loop that needs validation, time limits, and tool controls. Prompt design also specifies source boundaries, expected output structure, uncertainty behavior, and examples of refusal when evidence is missing. [CoT paper](https://arxiv.org/abs/2201.11903), [ReAct paper](https://arxiv.org/abs/2210.03629).

**Production scenario.** ShopStream asks the assistant to answer from supplied policy excerpts, cite document versions, and request clarification when the purchase date is unknown. A few examples distinguish “eligible,” “ineligible,” and “insufficient information.” Retrieved text remains untrusted data; a passage telling the model to issue a refund cannot confer that permission.

**Build and verify.** Version three prompt variants against a fixed set of questions and reference outcomes. Include ambiguous dates, missing evidence, contradictory policies, and injected instructions. Validate structured output with a schema and compare answer accuracy, unsupported claims, latency, and token cost before selecting a prompt.

### 69. Vector databases

*Pinecone, Qdrant, pgvector, FAISS.*

Vector search finds nearby representations rather than only exact word matches. Approximate nearest-neighbor indexes trade some recall for lower search cost; exact search provides a useful small-dataset baseline. Pinecone and Qdrant provide vector-search services; pgvector adds vector storage and indexing to PostgreSQL. **FAISS is a similarity-search library**, not a complete database: an application must provide persistence lifecycle, metadata handling, authorization, replication, and operations around it. Beyond nearest neighbors, compare filtering, update/delete semantics, backups, index build cost, and operational ownership. [FAISS project](https://github.com/facebookresearch/faiss), [Qdrant filtering](https://qdrant.tech/documentation/search/filtering/).

**Production scenario.** ShopStream stores policy chunks with tenant, document version, language, and access metadata. The authenticated tenant and permitted document scope constrain retrieval **before passages enter reranking, prompts, logs, or caches**. Asking the generator to ignore unauthorized passages after retrieval is insufficient. Application authorization supplies the filter; a user-written query cannot broaden it. Deleting a document removes its vectors and invalidates dependent cached answers.

**Build and verify.** Index a small corpus using pgvector or Qdrant and compare results with exact search. Measure recall and latency with selective filters. Insert similar documents for two tenants, attempt cross-tenant queries, and verify zero unauthorized candidates throughout the retrieval trace.

### 70. Embedding models

*Choosing dimensions, similarity search.*

An embedding model maps a query or document into a vector whose geometry reflects the model's training objective. Cosine similarity, dot product, and Euclidean distance are different scoring choices; follow the model's documented normalization and metric assumptions. Query and document vectors must use a compatible embedding space. Dimensions affect storage and computation, but more dimensions do not automatically mean better task accuracy. Language coverage, domain vocabulary, maximum input length, licensing, and deployment cost matter. Sentence-BERT illustrates how separately computed sentence embeddings enable efficient semantic similarity comparisons. [Sentence-BERT paper](https://arxiv.org/abs/1908.10084).

**Production scenario.** ShopStream buyers ask “Can I get my money back?” while policies say “refund eligibility.” Embeddings help connect these expressions. Exact SKU codes and unusual legal terms may still need lexical search. When changing embedding models, ShopStream builds a new versioned index and re-embeds documents; mixing old and new vectors can silently destroy relevance even when their dimensions match.

**Build and verify.** Label relevant documents for multilingual and domain-specific questions. Compare two models using recall at a fixed retrieval depth, indexing throughput, query latency, and storage. Record model revision, dimension, preprocessing, and normalization with every index. Verify that incompatible query/index versions fail explicitly and that a new index can be rolled back.

### 71. Chunking strategies

*Semantic vs fixed, chunk size.*

Chunking divides documents into retrieval units. Fixed token windows are simple and predictable, but can split an important condition from its exception. Sentence, heading, and semantic approaches preserve more structure at additional parsing or embedding cost. Small chunks can improve specificity while losing surrounding meaning; large chunks provide context but dilute retrieval and consume the generation budget. Overlap preserves boundary information but increases duplicates, index size, and retrieved redundancy. Tables, code, and forms often require specialized handling. LlamaIndex's sentence splitter prefers complete sentences and phrases while enforcing configured chunk limits and overlap. [Sentence splitter implementation](https://developers.llamaindex.ai/python/framework-api-reference/node_parsers/sentence_splitter/).

**Production scenario.** ShopStream's policy says returns are allowed within 30 days, followed by an exception for personalized products. A naive boundary separates those sentences and produces misleading evidence. Preserve the section heading and exception, and attach page number, source URI, document version, and parent-section identity. Document-level permissions must propagate to every chunk.

**Build and verify.** Compare token windows, sentence-aware splitting, and section-aware splitting on the same documents. Include PDF tables, scanned pages, and boundary-spanning questions. Measure retrieval recall, duplicate passages, context tokens, and answer correctness. Select sizes from those results, then verify every returned chunk resolves to a readable, authorized source location.

### 72. Hybrid search

*BM25 + vector, reranking.*

BM25 is a lexical ranking method that considers term matches, frequency, and document length. Dense retrieval captures semantic resemblance. Hybrid search combines their candidate sets to cover both exact identifiers and paraphrases. Their raw scores are not naturally comparable; reciprocal rank fusion (RRF) combines ranked positions instead. A reranker then evaluates a query together with each candidate, usually at greater cost than independent embeddings, to improve the final ordering. Candidate depth and reranker capacity need explicit limits. More candidates can improve recall while increasing latency and inference cost. [Elasticsearch RRF documentation](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion).

**Production scenario.** “Refund for SKU AB-104” contains an exact identifier and a semantic intent. ShopStream runs tenant-filtered lexical and vector retrieval in parallel, fuses the authorized candidates, removes duplicates, and reranks a bounded shortlist. A vector-only approach might confuse similar products; a lexical-only approach might miss a policy phrased as “reimbursement.” Both retrieval branches enforce the same permission scope.

**Build and verify.** Implement lexical-only, vector-only, and hybrid baselines with identical datasets and access controls. Measure recall, ranking quality, p95 retrieval latency, and reranking cost for identifiers, paraphrases, and misspellings. Keep reranking only if its measured improvement justifies the additional stage.

### 73. RAG evaluation

*Faithfulness, answer relevance, RAGAS.*

Evaluate retrieval and generation separately. Retrieval recall asks whether the necessary evidence was found; precision asks how much retrieved content is useful. Faithfulness asks whether the answer's claims are supported by retrieved context. Answer relevance asks whether it addresses the user's actual question. An answer can be faithful to an obsolete document and still be wrong, so also assess source currency, correctness, citation validity, and authorization. RAGAS provides automated evaluation metrics, including faithfulness; model-based judges have biases and errors, so calibrate them against human-reviewed examples. [RAGAS faithfulness documentation](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/).

**Production scenario.** ShopStream creates a reviewed dataset covering ordinary questions, policy exceptions, missing answers, multilingual queries, and adversarial documents. A retrieval change passes offline evaluation before a limited rollout. Online monitoring tracks user corrections, escalations, successful support outcomes, and latency; a positive rating alone does not prove the policy answer was correct.

**Build and verify.** Label required sources and expected answer claims for a teaching dataset of 100 questions. Run retrieval and answer evaluation for each change, inspect disagreements between judges and people, and classify failures by stage. Add tests for abstention and unauthorized retrieval, then verify citations support specific claims rather than merely pointing to related documents.

### 74. Advanced RAG patterns

*HyDE, self-query, parent-child chunks.*

HyDE generates a hypothetical answer-like document and embeds it to retrieve real documents. Its generated text is a search aid, never authoritative evidence. Self-query retrieval turns user intent into a semantic query plus structured metadata constraints, such as language or effective date. Generated filters need schema validation; application-enforced tenant and permission constraints always remain mandatory. Parent-child retrieval searches small child chunks for precision and fetches an authorized larger parent section for explanation. These patterns solve different problems and can increase latency, token usage, and failure surface. [HyDE research paper](https://arxiv.org/abs/2212.10496).

**Production scenario.** A ShopStream merchant asks, “What changed in the return policy this year?” Self-query extracts a date constraint, child chunks locate the revision, and parent sections supply surrounding exceptions. If HyDE proposes a nonexistent policy, only actual retrieved documents can support the response. Parent fetching repeats authorization checks and checks document versions; it cannot reveal an otherwise inaccessible section through an accessible child.

**Build and verify.** Start from the hybrid-search baseline and enable one pattern at a time. Measure gains on difficult questions and regressions on ordinary ones. Test malformed metadata filters and injected date constraints. Keep a pattern only when its evaluated accuracy improvement outweighs extra latency and cost.
