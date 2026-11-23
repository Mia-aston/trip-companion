# ADR 0001: modular monorepo

Status: accepted

We keep frontend, API, domain modules and shared docs in one repository while enforcing module boundaries in code. This makes cross-cutting product work visible without requiring distributed-service overhead. External providers are adapters, so vendor changes do not leak into domain logic.
