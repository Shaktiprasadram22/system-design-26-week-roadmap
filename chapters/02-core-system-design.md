## Phase 2 — Core system design: weeks 5–10

The goal is to increase capacity without sacrificing correctness. Introduce one distributed boundary at a time and measure the new failure modes it creates.

### 14. Horizontal vs vertical scaling

Vertical scaling gives one machine more CPU, memory, or faster storage. Horizontal scaling adds machines and distributes work. Vertical scaling is simple but has hardware and failure limits; horizontal scaling introduces coordination, balancing, and state placement. Adding API replicas helps only if they are the bottleneck: it can worsen a saturated database by creating more connections. Stateless request handlers scale more easily when durable state lives outside the process. [AWS reliability design principles](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html).

**Production scenario.** ShopStream initially uses one API instance and one database. Profiling shows thumbnail processing saturates CPU, so separate and scale workers. Later, catalogue reads saturate the database, so indexes and caching help more than another API replica. Maintain spare capacity for bursts and instance failures; autoscaling reacts after signals rise and provisioning takes time.

**Build and verify.** Load-test one and two API instances using identical workloads. Measure throughput, p95 latency, CPU, and database connection wait. Explain why doubling instances may yield less than twice the capacity, and identify the next shared bottleneck before adding more machines.

### 15. Load balancers

A load balancer routes traffic across healthy backends. Layer 4 balancing operates on transport information; layer 7 balancing understands application requests and can route by hostname, path, or headers. Round-robin rotates targets; least-connections favors less occupied servers; hashing can preserve affinity. Health checks, connection draining, deadlines, and retry rules matter as much as the algorithm. A backend can be alive yet unable to serve traffic correctly. [NGINX load balancing](https://nginx.org/en/docs/http/load_balancing.html).

**Production scenario.** ShopStream sends API traffic across three instances. Before deployment, an instance becomes unready, stops receiving new traffic, finishes in-flight requests, and shuts down. Long-lived chat connections need draining and client reconnect logic. Sticky sessions can simplify an initial implementation but concentrate load and complicate failover; durable sessions should not exist solely in one process.

**Build and verify.** Place two API processes behind a local reverse proxy. Kill one and record failures and recovery time. Test readiness separately from liveness. During a rolling restart, verify an in-flight order creation is completed or safely retried without creating a second order.

### 16. Caching strategies

Caching stores reusable results closer to callers. Cache-aside reads the cache first, loads misses from the authoritative database, and inserts results. Write-through synchronously updates a cache through the write path; write-behind defers persistence and requires stronger failure handling. TTL bounds retention; eviction frees memory according to policies such as LRU or LFU. Redis offers richer data structures, while Memcached focuses on an in-memory cache. Plan for misses, stale values, invalidation races, and a cold cache. [Redis eviction policies](https://redis.io/docs/latest/develop/reference/eviction/).

**Production scenario.** ShopStream caches popular product descriptions but validates authoritative stock at checkout. A flash sale expires thousands of keys simultaneously, causing a database surge. TTL jitter, coalescing concurrent misses for the same key, and controlled stale reads reduce this stampede. Include tenant identity and relevant visibility rules in keys so one merchant's private data cannot leak to another.

**Build and verify.** Implement cache-aside with bounded TTL and coalesced misses. Warm the cache, measure hit rate and database queries, then flush it under load. Verify correct stock decisions and bounded database concurrency when the cache is unavailable.

### 17. CDN architecture

A CDN typically combines edge locations, cache lookup, origin fetching, and sometimes a shielding tier that reduces origin requests. Cache keys can include URL, selected headers, and other configured dimensions. `Cache-Control`, validators such as ETags, and `Vary` help determine eligibility and reuse. Invalidation removes cached objects, but propagation and client-side caches complicate immediate replacement. Fingerprinted asset URLs provide predictable versioning. Personalized responses need deliberate cache isolation. [HTTP caching specification](https://www.rfc-editor.org/rfc/rfc9111.html).

**Production scenario.** ShopStream publishes `product-photo.<content-hash>.webp` with long-lived caching. Editing the photo creates a new URL, while private invoices require authorization and appropriate cache policy. Omitting tenant or authorization context from a shared cache key can expose data even when the origin checks permissions correctly. A CDN also reduces bandwidth costs and origin load; measure actual hit rates instead of assuming every request is cached.

**Build and verify.** Version two images and inspect their cache headers. Design public and private download paths. Confirm one tenant's authenticated invoice request cannot produce a cached response usable by a different tenant.

### 18. Database sharding

Sharding divides data across independently operated database partitions. Select a shard key that distributes load while keeping frequent operations local. Hash partitioning spreads keys; range partitioning supports locality but can produce hotspots. Cross-shard joins, uniqueness, transactions, resharding, and operational recovery become harder. Table partitioning within one PostgreSQL server can improve management and some queries but does not by itself distribute workload across independent servers. [PostgreSQL table partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html).

**Production scenario.** ShopStream considers tenant-based sharding when one database can no longer serve the measured workload. Keeping a tenant's orders together simplifies many queries, but a large merchant can dominate one shard. Separate exceptional tenants or use another partition dimension while preserving order-level locality. Global reports should use an analytical pipeline rather than repeatedly scanning every production shard.

**Build and verify.** Route synthetic tenants across two database instances using a shard directory. Move one tenant while requests continue and document cutover consistency. Verify no missing orders, duplicate writes, or incorrect routing during the transition; explain how large tenants are handled.

### 19. Read replicas

A leader accepts writes while followers replay changes and can serve reads. Asynchronous replication reduces write coordination but allows lag; synchronous arrangements add durability or freshness guarantees with latency and availability costs. A successful write on the leader may not yet appear on a follower. Read-after-write consistency can use leader routing, session affinity to a consistency point, or waiting for a replica to catch up. Replica failover needs a policy for stale state and lost acknowledged writes under the configured mode. [PostgreSQL standby and replication](https://www.postgresql.org/docs/current/warm-standby.html).

**Production scenario.** ShopStream sends catalogue browsing to replicas but reads a newly created order from the leader. If a customer is redirected immediately to a lagging replica, “order not found” creates confusion and repeat checkout attempts. Replicas improve read capacity; they do not scale leader write throughput, and they are not independent backups against accidental deletion replicated everywhere.

**Build and verify.** Set up a follower or simulate delayed replication. Write an order and compare leader and follower reads. Add explicit read-after-write handling and measure how long lag can persist under sustained writes.

### 20. Consistent hashing

Consistent hashing maps both keys and nodes into a hash space. A key belongs to a node according to a placement rule, often the next node on a ring. Adding or removing a node changes ownership for a portion of keys rather than nearly all keys as simple modulo assignment can. Virtual nodes improve distribution and can represent heterogeneous capacity. Replication requires selecting multiple distinct physical nodes or failure domains, not simply adjacent virtual nodes. Ownership changes still require data movement and transitional routing. [Amazon's original Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf).

**Production scenario.** ShopStream distributes cache keys across several servers. Scaling the cache causes some misses while ownership changes, so database protection remains necessary. A popular individual key can still overwhelm one node; consistent hashing balances key placement, not necessarily request volume. Replication or special hot-key handling may be needed.

**Build and verify.** Assign 100,000 keys to three nodes, add a fourth, and compare moved-key percentage against modulo hashing. Repeat with virtual nodes and uneven key popularity. Explain why a balanced key count does not prove balanced CPU or network load.

### 21. Replication

Replication keeps copies of data for availability, durability, or read capacity. Leader–follower, multi-leader, and leaderless designs make different conflict and coordination choices. With `N` replicas, write quorum `W`, and read quorum `R`, `R + W > N` creates overlap under relevant assumptions; overlap alone does not establish linearizability. Version selection, concurrent writes, membership changes, and failure handling also matter. Synchronous acknowledgements trade latency for stronger persistence guarantees; asynchronous copies can lag. [Cassandra consistency levels](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html).

**Production scenario.** ShopStream values durable order records more than instantly available likes. Place replicas in distinct failure domains so one host or availability-zone failure does not remove all copies. A remote acknowledgement can dominate latency. Choose the required guarantee explicitly: surviving one disk failure differs from surviving a regional disaster without losing acknowledged writes.

**Build and verify.** Model three replicas and several read/write quorum combinations. Inject a stale replica and concurrent updates, then explain the returned value. State which failures the configuration tolerates and why replicas still need backups and restoration tests.

### 22. Consensus (Raft / Paxos)

Consensus lets distributed participants agree on values or an ordered log despite some failures. Raft explains leader election, log replication, terms, and majority commitment; Paxos is another family of protocols solving agreement. A majority of a fixed membership can preserve progress through some node failures, but a minority partition must not independently commit conflicting state. Election timeouts and failure detection affect availability without proving a node is permanently dead. Consensus provides a building block, not arbitrary transactional correctness for an entire application. [Raft paper](https://raft.github.io/raft.pdf).

**Production scenario.** ShopStream uses a proven coordination system for membership or leader selection rather than implementing its own production consensus. A worker elected as leader can pause and later resume after another leader is chosen. External writes therefore need fencing tokens or equivalent authority checks to prevent a stale leader from continuing work.

**Build and verify.** Use a small Raft simulator or existing educational implementation with three nodes. Stop the leader, observe election, and isolate one node. Verify the minority cannot commit conflicting log entries, and explain why a two-node cluster cannot tolerate one loss while retaining a majority.

### 23. Distributed transactions

Two-phase commit asks participants to prepare before a coordinator decides commit or abort. It can provide atomic commitment across participants but introduces coordination, lock retention, and blocking when outcomes are uncertain. A saga breaks a business workflow into local transactions with compensating actions. Compensation is a business operation, not a time machine: a shipment or sent email cannot simply be undone. Durable state, idempotent actions, retries, and reconciliation make a saga reliable. [Azure saga pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga).

**Production scenario.** ShopStream reserves inventory, authorizes payment, and confirms an order. If payment fails, release the reservation; if confirmation is temporarily unavailable, keep enough state to recover. A payment timeout means “unknown outcome,” not “definitely failed.” Query by the same idempotency key or process the provider callback before making a compensation decision.

**Build and verify.** Implement a durable order state machine: pending, reserved, payment-pending, confirmed, compensation-pending, cancelled. Crash between each step and restart. Verify every order reaches a valid recoverable state and repeated actions cannot double-charge or release stock twice.

### 24. Clock & ordering

Wall clocks can drift, move backwards, and disagree between hosts. Use a monotonic clock for local durations. Lamport clocks encode a logical ordering: if event A causally precedes B, A's logical timestamp is smaller; the converse does not prove causality. Vector clocks can distinguish causal order from concurrency by tracking multiple participants, at the cost of larger metadata. Total ordering, causal ordering, and per-key ordering solve different needs. [Lamport's time and clocks paper](https://lamport.azurewebsites.net/pubs/time-clocks.pdf).

**Production scenario.** ShopStream cannot decide the winner of concurrent inventory changes solely by comparing application-server timestamps. Buyer–seller messages can carry server-assigned conversation sequence numbers so clients restore a coherent conversation. Global total ordering of every message would add unnecessary coordination; per-conversation order is sufficient for many features.

**Build and verify.** Simulate three processes exchanging events. Assign Lamport timestamps and identify two events whose timestamps differ despite no causal link. Add vector timestamps to detect concurrency. Move a wall clock backwards and confirm request-duration calculations still use monotonic time correctly.

### 25. Message queues

Queues decouple producers and consumers, absorb bounded bursts, and allow independent retry. RabbitMQ emphasizes routing and acknowledgements; SQS provides managed queue semantics; Kafka is a durable partitioned log with replay and consumer offsets. Learn visibility timeouts or acknowledgements, redelivery, dead-letter handling, ordering scope, retention, and consumer concurrency. Broker acknowledgement of publication and consumer acknowledgement of processing represent separate milestones. Queue depth and oldest-message age reveal backlog; queues cannot compensate forever for insufficient processing capacity. [RabbitMQ acknowledgements and confirms](https://www.rabbitmq.com/docs/confirms).

**Production scenario.** ShopStream confirms an order synchronously and sends emails asynchronously. If email delivery slows, checkout remains responsive while backlog grows. A consumer that acknowledges before sending can lose the notification; one that sends and crashes before acknowledging can send twice unless the external effect is deduplicated. Separate critical fulfillment jobs from lower-priority marketing work.

**Build and verify.** Publish notification jobs and crash a worker during processing. Observe redelivery and ensure jobs are not silently lost. Set retry limits and a dead-letter workflow, then show backlog drains when processing capacity exceeds arrival rate.

### 26. Event-driven architecture

Events describe facts that happened, such as `OrderConfirmed`; commands request actions, such as `SendReceipt`. Publisher–subscriber systems allow multiple independent consumers to react. CQRS separates write handling from read models; it does not require separate databases or event sourcing. Event sourcing stores authoritative state transitions as events, adding replay and schema-evolution concerns. Reliable event publication must bridge the transaction–broker boundary. A transactional outbox stores business changes and pending events in the same local transaction. [Transactional outbox implementation](https://aws.amazon.com/blogs/compute/implementing-the-transactional-outbox-pattern-with-amazon-eventbridge-pipes/).

**Production scenario.** A confirmed ShopStream order drives fulfillment, analytics, and notifications. Commit the order and outbox row together; a relay publishes the event and marks progress. The relay may publish twice if it crashes after publication, so consumers remain idempotent. Include event ID, tenant ID, schema version, and business entity version so consumers can validate and order work appropriately.

**Build and verify.** Add an outbox to checkout. Kill the process after database commit but before publication. Restart and verify the event is eventually delivered, with no missing order and no duplicate business effect.

### 27. Exactly-once delivery

Separate message delivery from the effect of processing a message. In general application workflows, assume messages or requests may be repeated. At-least-once delivery plus atomic deduplication can produce one business effect. Store an event ID or idempotency key with the result in the same transaction as the state mutation. Broker-specific exactly-once processing has a defined boundary; it does not automatically include a card processor, email provider, or independent database. Deduplication retention and key reuse rules are part of the contract. [SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html), [Kafka processing semantics](https://kafka.apache.org/41/design/design/).

**Production scenario.** A ShopStream customer retries checkout after a mobile timeout. The server scopes the key to tenant and operation, rejects a different payload using the same key, and returns the original completed result. Payment requests use a stable provider key too; local deduplication alone cannot control external side effects.

**Build and verify.** Send the same order request 100 times, including concurrently. Confirm one order, one reservation, and one effective charge. Multiple provider API attempts may occur, but they reuse the same idempotency key. Simulate a crash after commit but before response and verify retry returns the stored outcome.

### 28. Stream processing

Stream processing continuously transforms arriving events, often using keyed state and windows. Event time is when something occurred; processing time is when the processor handles it. Watermarks estimate event-time progress so windows can produce results despite out-of-order arrival. Define policies for late events, corrections, state retention, and recovery. Kafka Streams and Flink support stateful processing, but checkpoint guarantees still depend on source and sink behavior. Backpressure slows upstream work when downstream processing cannot keep up. [Flink event time and watermarks](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/time/).

**Production scenario.** ShopStream calculates five-minute sales totals and detects suspicious purchase bursts. Mobile events arrive late or twice. An event-time window with deduplication and a correction policy produces more meaningful totals than grouping solely by server receipt time. Keep checkout operational if the analytical stream processor is behind.

**Build and verify.** Aggregate timestamped order events into tumbling windows. Deliver one event late, replay several events, and restart the processor. Explain the watermark and correction policy, then verify expected totals and bounded retained state.

### 29. System estimation

Estimate demand before choosing infrastructure. Start with active users and requests per user; derive average requests per second, peak factors, read/write mix, payload bandwidth, and retained storage. Include indexes, replicas, logs, media, and backup overhead separately. Little's law estimates average in-flight work as arrival rate times average time in system under stable conditions. Do not substitute p99 latency into that mean-value formula or treat a guessed requests-per-server number as a benchmark.

**Production scenario.** Suppose ShopStream has 100,000 daily active users making 20 API requests each: 2,000,000 requests/day, or about 23 requests/second on average. A teaching peak factor of 10 gives approximately 230 requests/second. At 20 KB per API response this is about 4.6 MB/second, excluding images and protocol overhead. Ten thousand 2 KB order records per day produce roughly 20 MB/day before indexes, replication, and backups.

**Build and verify.** Maintain a capacity worksheet with units and assumptions. Load-test realistic catalogue and checkout mixes, measure bottlenecks, and replace guessed service capacity with observed results. Forecast one year of retained data and explain which assumptions dominate cost.

### 30. Component design

High-level design assigns responsibilities, interfaces, state ownership, and failure behavior to components. An API gateway can handle ingress authentication, routing, quotas, and protocol adaptation. A service mesh handles aspects of service-to-service traffic such as identity, telemetry, and policy. Neither should absorb all business authorization or repair unclear service boundaries. Draw data paths as well as component boxes: identify synchronous dependencies, durable stores, asynchronous events, and where a request can become stuck.

**Production scenario.** ShopStream begins with catalogue, checkout, and merchant administration modules inside one deployable application. Add a reverse proxy, database, object store, and worker. Extract a service only when ownership, scaling, release independence, or reliability justify the additional network boundary. A gateway validating identity does not prove the caller is entitled to a particular tenant's order.

**Build and verify.** Draw the checkout sequence and annotate deadlines, authentication, authorization, durable commits, and retries. For every component, answer: what does it own, how is it monitored, and what does the user experience if it fails?

### 31. Microservices patterns

Decompose around business capabilities and stable ownership, not every database table. Each service should control its data and expose a contract. Remote calls introduce latency, partial failure, schema compatibility, and operational overhead. Circuit breakers bound repeated calls to a failing dependency; bulkheads isolate resources; sagas coordinate business workflows; the strangler pattern incrementally replaces existing functionality. A modular monolith is often a useful starting point because it allows boundaries to evolve before they become network contracts. [Azure microservices architecture](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/microservices).

**Production scenario.** ShopStream separates image processing because its resource needs and failure behavior differ from checkout. Splitting order lines and orders into independent services would make simple invariant enforcement harder without an obvious operational benefit. Avoid a chain of ten synchronous services where one slow dependency controls the entire user's latency.

**Build and verify.** Extract the thumbnail worker behind a versioned job contract. Keep catalogue storage ownership explicit. Fail the worker and show checkout remains available. Compare deployment independence and recovery effort against the additional queue, contract, and monitoring responsibilities.

### 32. Design a URL shortener

A URL shortener maps a compact identifier to a target URL. Define link creation, redirection, expiration, custom aliases, abuse handling, and analytics. Choose identifiers with sufficient collision resistance or allocate unique IDs and encode them in base62. A unique constraint remains necessary for collision handling. Redirection is read-heavy and cacheable, while creation must preserve uniqueness and ownership. Permanent and temporary redirects have different caching consequences, particularly when destinations can change.

**Production scenario.** ShopStream merchants share campaign links. A viral link receives far more reads than other keys, requiring hot-key handling, caching, and asynchronous click analytics. Validation must block dangerous schemes and address abuse; a short link is also an opaque identifier, not an authorization mechanism. Cache TTL must respect expiry and destination changes.

**Build and verify.** Implement `POST /links` and `GET /{code}` with expiration, alias collision handling, and a cache. Replay simultaneous creations, load one hot link, and disable it. Verify correct redirects, no alias overwrites, and a documented maximum delay before revocation becomes visible.

### 33. Design Instagram/Twitter

This is an exercise in social feed architecture rather than a claim about either company's current implementation. Store posts and media separately, maintain follow relationships, and choose a feed distribution strategy. Fan-out on write inserts post references into followers' timelines, making reads fast but multiplying writes. Fan-out on read assembles posts when a user requests a feed. A hybrid can precompute normal authors while merging high-fanout authors at read time. Ranking, pagination, moderation, and visibility checks are additional concerns.

**Production scenario.** ShopStream adds a merchant-following feed. A seller with 500 followers is cheap to fan out, while one with millions creates a major burst. Store IDs rather than duplicating entire media objects. Deleting a post or changing its visibility must affect feed delivery even if timeline references are already cached. Eventual feed freshness can be acceptable; privacy violations are not.

**Build and verify.** Implement a chronological feed and compare write/read work for both fan-out strategies. Add a high-fanout author, keyset pagination, deletion, and unfollowing. Verify no duplicate pages or unauthorized posts while new posts arrive.

### 34. Design WhatsApp

This is a messaging design exercise, not a reconstruction of WhatsApp's private architecture. Separate connection gateways, durable message storage, delivery workers, presence, and push notifications. A server acknowledgement, recipient-device acknowledgement, and read receipt mean different things. Define conversation-level ordering, deduplication by client message ID, offline delivery, multi-device synchronization, attachment storage, retention, and encryption requirements. Presence is ephemeral and can tolerate stale status; accepted messages need a stronger durability policy.

**Production scenario.** ShopStream supports buyer–seller chat. A client resends after losing its connection, so the server accepts the same message ID once. Offline users later sync from a durable cursor rather than relying on a missed socket event. If end-to-end encryption is required, key distribution, device changes, backups, and accessible metadata need a dedicated threat model; TLS alone is not end-to-end encryption.

**Build and verify.** Build a two-user chat prototype with reconnect, offline sync, and per-conversation sequence numbers. Crash a gateway after accepting a message. Verify accepted messages are recoverable, duplicates do not appear twice, and the interface reports delivery state accurately.
