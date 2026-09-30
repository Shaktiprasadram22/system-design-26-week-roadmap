## Phase 1 — Foundations: weeks 1–4

The goal is to understand what happens between a user clicking a button and the system returning a correct answer. Follow one request through the network, application, operating system, and database before introducing distributed infrastructure.

### 1. OSI & TCP/IP model

The OSI model separates communication into physical, data-link, network, transport, session, presentation, and application layers. TCP/IP groups these more practically into link, internet, transport, and application layers. Ethernet or Wi-Fi moves frames locally; IP routes packets between networks; TCP supplies an ordered byte stream with retransmission and congestion control; HTTP defines application messages. UDP sends datagrams without those TCP guarantees, although protocols built on UDP, such as QUIC, can provide reliability. A packet is a unit of network transmission; an HTTP request can span many packets.

**Production scenario.** A ShopStream checkout timeout can originate from failed DNS resolution, an unreachable IP route, a blocked TCP port, TLS negotiation, or slow application work. “The API is down” does not identify which layer failed. Diagnose from the outside inward so application engineers do not spend hours changing SQL for a network routing problem.

**Build and verify.** Trace a request with `dig`, `curl -v`, and a local packet capture. Explain which operations happen before HTTP, which connection is reused, and why a successful connection does not prove the checkout operation completed.

### 2. HTTP / HTTPS / HTTP2 / HTTP3

HTTP defines methods, status codes, headers, and message bodies. HTTPS adds authenticated encryption using TLS. Understand safe and idempotent methods, connection reuse, caching headers, redirects, and the difference between transport success and business success. HTTP/2 multiplexes streams over TCP, but lost TCP data can stall multiple streams. HTTP/3 maps HTTP over QUIC, which runs over UDP and supplies reliable streams plus integrated TLS; loss on one stream need not block unrelated streams. Neither version fixes an expensive query or an overloaded application. [HTTP/2 specification](https://www.rfc-editor.org/info/rfc9113/), [HTTP/3 specification](https://www.rfc-editor.org/rfc/rfc9114.html).

**Production scenario.** Catalogue browsing transfers many independent thumbnails and API responses, making multiplexing useful. Checkout still needs request deadlines, safe retry rules, and meaningful errors. A `200` carrying an error-shaped body makes observability harder; a timeout after charging a card leaves the caller uncertain about the outcome.

**Build and verify.** Implement a resource endpoint with validation, correct status codes, an ETag, and conditional reads. Inspect response headers and compare cold versus reused connections. Demonstrate that repeating a GET does not mutate state.

### 3. DNS & CDN

DNS translates names into records, including addresses. A recursive resolver consults cached information or follows the hierarchy through root, top-level-domain, and authoritative servers. TTL controls how long a cached answer can remain usable; changing DNS does not instantly change every client's destination. A content delivery network places delivery infrastructure near users and caches eligible content. Anycast advertises one address from multiple locations, allowing routing to select a reachable location; it does not guarantee the geographically closest server or establish application-level correctness. [DNS concepts](https://www.rfc-editor.org/info/rfc1034/).

**Production scenario.** ShopStream serves product photos through a CDN so a user in Bengaluru does not repeatedly fetch them from a distant origin. During an origin migration, old DNS answers and persistent connections can keep traffic arriving at the old deployment. Keep it working during the transition and measure both destinations.

**Build and verify.** Inspect authoritative and recursive DNS answers and their TTLs. Serve a versioned image with cache headers. Confirm a repeated request is served from a cache where available, and explain why reducing TTL immediately before migration may not affect already cached answers.

### 4. WebSockets & SSE

WebSockets provide bidirectional message exchange over a persistent connection. Server-sent events, or SSE, send server-to-client text events over HTTP; clients can send their own actions using ordinary HTTP requests. SSE supports event identifiers and reconnection, but resumable delivery requires server-side retention and replay logic. Neither protocol makes messages durable automatically. Long-lived connections need heartbeats, authentication renewal, bounded outgoing buffers, and reconnect handling. [SSE implementation guidance](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events).

**Production scenario.** Order status updates and streaming support answers fit SSE because most traffic flows toward the browser. Live buyer–seller chat fits WebSockets because both sides send frequent messages. A disconnected mobile client must recover missed durable chat messages from storage; socket delivery alone is insufficient.

**Build and verify.** Implement an order-status SSE stream with sequential event IDs. Disconnect after event 3 and reconnect using the last received ID. Verify events 4 onward are recoverable, duplicates are harmless, and a deliberately slow client cannot consume unlimited server memory.

### 5. REST vs GraphQL vs gRPC

REST organizes APIs around resources and HTTP semantics. GraphQL lets clients select fields from a typed schema, useful when screens need different combinations of data. gRPC exposes typed remote procedures, commonly using Protocol Buffers and supporting streaming. Compare interoperability, schema evolution, caching, tooling, payload size, and operational complexity. GraphQL resolvers can create N+1 database queries, while one seemingly small query can demand substantial computation. gRPC deadlines and cancellation must propagate through the call chain. [GraphQL performance](https://graphql.org/learn/performance/), [gRPC core concepts](https://grpc.io/docs/what-is-grpc/core-concepts/).

**Production scenario.** ShopStream exposes REST to external merchants, considers GraphQL for a mobile product screen combining inventory and reviews, and could use gRPC between internal high-volume services. These are choices for particular clients, not a requirement to operate three protocols.

**Build and verify.** Design the same product lookup in all three styles on paper and implement one. Include pagination, authorization, validation, and backwards-compatible changes. Measure database query count when loading 20 products and demonstrate how batching prevents one extra query per product.

### 6. Relational DBs (SQL)

Relational databases store structured rows linked through keys. Normalization separates facts so one update does not require editing many contradictory copies; selective denormalization can simplify heavy reads. ACID describes atomicity, consistency of declared invariants, isolation between concurrent transactions, and durability under the configured failure model. Constraints, transactions, and indexes work together, but “uses SQL” does not automatically make application logic race-free. Isolation levels determine which concurrent anomalies remain possible. [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html).

**Production scenario.** ShopStream stores orders, order lines, inventory, and payment attempts in PostgreSQL. A conditional inventory update and order insert occur in one transaction. An external card processor cannot participate in that local transaction; coordinate payment separately with durable workflow state and idempotency. Store the price agreed at purchase time on the order line so later catalogue edits do not rewrite history.

**Build and verify.** Create tables with foreign keys, uniqueness constraints, and nonnegative stock. Send concurrent requests for the final item. Verify at most one reservation succeeds and failed transactions leave no partial order or negative inventory.

### 7. NoSQL DBs

NoSQL includes several families rather than one consistency model. Document databases such as MongoDB keep flexible structured documents; wide-column systems such as Cassandra organize data around partition access; key-value services such as DynamoDB emphasize key-based operations. Design around actual access patterns, partition distribution, item size, secondary indexes, and supported transaction semantics. Many NoSQL systems provide strong reads or transactions under defined conditions. DynamoDB, for example, distinguishes eventually consistent and strongly consistent reads, with restrictions that depend on the resource being queried. [DynamoDB read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html).

**Production scenario.** A document store can suit ShopStream catalogue attributes that vary between books and clothing. A high-volume activity history can suit time-bucketed, user-keyed partitions. Financial order invariants may still be simpler in a relational database. A single extremely popular seller can overload a poorly chosen partition key.

**Build and verify.** Write five required queries before choosing a datastore. Model each without full collection scans. Simulate a popular tenant and show whether its traffic concentrates on one partition; revise the key or add controlled bucketing where necessary.

### 8. CAP theorem

CAP says that during a network partition a distributed system cannot guarantee both linearizable consistency and availability as defined by the theorem. Consistency here means operations behave as though acting on one up-to-date copy; availability means requests to nonfailed nodes eventually receive responses. This is not the same as SQL constraint consistency or a monthly uptime percentage. A partition is lost or indefinitely delayed communication between components. Outside a partition, latency and consistency remain trade-offs, but the shorthand “always pick two of three” is misleading. [Gilbert and Lynch's CAP paper](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf).

**Production scenario.** If two ShopStream regions cannot communicate, selling the same final item from both can violate inventory correctness. A design may reject or delay reservations where authoritative stock cannot be reached. Product descriptions can tolerate stale regional copies and remain readable. Choose semantics by operation rather than labeling the entire application CP or AP.

**Build and verify.** Draw two regions with one item remaining. Disconnect them and specify the exact response to reads and writes in each. Identify which guarantee is relaxed, how clients see it, and how reconciliation works after connectivity returns.

### 9. ACID vs BASE

ACID describes transactional guarantees. BASE—basically available, soft state, eventually consistent—is a broad approach to asynchronous convergence, not a precise opposing database specification. A system can use ACID within a service while publishing events that update other services eventually. Eventual consistency needs a convergence mechanism and a clear policy for conflicts, duplicates, and stale reads; it does not mean all updates magically arrive. Distinguish immutable business facts from derived views. [PostgreSQL transaction introduction](https://www.postgresql.org/docs/current/tutorial-transactions.html).

**Production scenario.** ShopStream commits an order and inventory reservation atomically. Search results, sales dashboards, and notification status follow asynchronously. A user should see their confirmed order immediately even if the analytics dashboard is seconds behind. Writing the order and then separately publishing its event can lose the event when the process crashes, so an outbox or equivalent reliable change capture closes that gap.

**Build and verify.** Maintain an ACID order table and an asynchronously updated sales summary. Pause the consumer, create an order, and document what each screen shows. Resume processing and verify convergence without inflating totals when an event is delivered twice.

### 10. Database indexing

Indexes create alternate access paths at the cost of storage and write maintenance. B-tree indexes support many equality, range, and ordering queries; hash indexes primarily target equality. Composite indexes depend on column ordering and query shape, although optimizer capabilities vary by database and version. A useful index often starts with columns constrained by equality and continues with range or sort columns. Covering indexes can reduce table reads, but wider indexes cost more. Always inspect the actual execution plan and representative data. [PostgreSQL multicolumn indexes](https://www.postgresql.org/docs/current/indexes-multicolumn.html).

**Production scenario.** A merchant's latest orders query filters `tenant_id` and sorts by creation time. An index on `(tenant_id, created_at DESC, id DESC)` can support filtering and stable keyset pagination. An index only on `status` may be poor when almost every row has the same status. Tenant filtering also needs authorization; the index itself supplies no security.

**Build and verify.** Load at least 100,000 synthetic orders. Compare `EXPLAIN ANALYZE` before and after indexing, inspect scanned rows and sorting, and measure insert overhead. Verify pagination remains stable when several orders share one timestamp.

### 11. Processes & threads

A process has its own address space and resources. Threads within a process share memory and can therefore communicate cheaply, but require coordination around shared mutable state. Concurrency means multiple activities make progress over overlapping time; parallelism means executing simultaneously on multiple processing units. Async I/O can handle many waiting requests without dedicating one thread to every connection. CPU-heavy work still consumes processor time, and language runtimes differ in threading behavior. [Linux POSIX threads](https://man7.org/linux/man-pages/man7/pthreads.7.html).

**Production scenario.** ShopStream handles ordinary API requests in an async service while a separate worker generates thumbnails. Running image transformations on the request event loop stalls unrelated requests. Unbounded threads or workers can exhaust memory, database connections, and file descriptors. A shared in-memory counter also stops being globally correct as soon as multiple processes handle requests.

**Build and verify.** Run mixed workloads containing fast requests and CPU-heavy jobs. Move heavy work into a bounded worker pool and compare tail latency. Demonstrate a race in a shared counter, then correct it with synchronization appropriate to the chosen runtime.

### 12. Memory management

The stack holds call frames and local execution state; the heap holds dynamically allocated objects. Virtual memory maps process addresses to physical memory or backing storage, with page faults when required pages are not immediately available. Garbage collection reclaims unreachable objects in managed runtimes, but retained references still cause leaks and collection can introduce pauses. The operating system's page cache is useful memory consumption, not necessarily an application leak. Memory limits matter because swapping or termination can make a service fail abruptly. [Linux memory mapping](https://man7.org/linux/man-pages/man2/mmap.2.html).

**Production scenario.** A ShopStream upload handler buffers a 200 MB file per request. Twenty simultaneous uploads can consume several gigabytes before normal application overhead. Streaming uploads with bounded buffers and concurrency limits avoids memory growth proportional to complete file sizes. Similar problems occur when a slow WebSocket client accumulates an unlimited outgoing buffer.

**Build and verify.** Compare buffered and streamed processing of a large synthetic file. Record peak resident memory, request latency, and concurrent upload behavior. Set a memory limit and demonstrate predictable rejection or throttling before the process is killed.

### 13. I/O & file systems

Storage behavior depends on access patterns. HDDs suffer high seek costs; SSDs improve random access but still have finite throughput and latency. Buffered writes may reach the page cache before durable storage, so acknowledge persistence according to the database or filesystem's actual flush guarantees. Block storage exposes disk-like volumes; file storage exposes directories and files; object storage exposes keyed objects through an API. Object storage is suited to large immutable assets, not automatically to a database's small in-place writes. [Linux `fsync` semantics](https://man7.org/linux/man-pages/man2/fsync.2.html).

**Production scenario.** ShopStream stores transactional database files on suitable persistent storage and product images in object storage, keeping image metadata in SQL. A container's writable layer is not a safe sole copy of orders or uploads. Uploading a file successfully and creating its metadata are separate operations, so reconcile orphaned objects and incomplete records.

**Build and verify.** Implement a streamed upload, store a checksum and metadata, and retrieve the object by key. Restart the application and verify persistence. Simulate failure between object upload and metadata commit, then clean up or recover the incomplete workflow.
