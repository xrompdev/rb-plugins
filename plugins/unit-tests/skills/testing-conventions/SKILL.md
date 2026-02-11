---
name: Testing Conventions
description: This skill should be used when the user asks to "write unit tests", "create tests", "update tests", "add test coverage", "write a spec file", mentions "*.spec.ts", or needs guidance on testing patterns, mocking strategies, and test structure for this NestJS/Nx monorepo project.
version: 0.1.0
---

# Testing Conventions

Provide guidance on writing and updating unit tests for the ResponsiBid NestJS/Nx monorepo. All unit tests follow consistent patterns for NestJS service/resolver testing with Prisma mocking and event sourcing support.

## Test File Conventions

- **Unit tests**: `*.spec.ts` colocated with source files in `src/`
- **Integration tests**: `*.integration.spec.ts` in `test/` directory
- **E2E tests**: `*.e2e.spec.ts` in `test/` directory
- **Naming**: Mirror source file name — `foo.service.ts` → `foo.service.spec.ts`

## Test Framework Stack

- **Jest** as the test runner
- **@nestjs/testing** (`Test.createTestingModule`) for NestJS DI setup
- **jest-mock-extended** (`mockDeep`, `DeepMockProxy`) for deep Prisma mocking
- **@faker-js/faker** for test data generation
- **@responsibid/testing** for domain-specific test factories (`createBundle`, `createBundleService`, `createBundleSubService`, `createModuleSubService`, etc.)

## Standard Service Test Structure

Follow this pattern for NestJS service unit tests:

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { PrismaClient } from '@prisma/client';
import { PrismaService } from '@responsibid/shared/types';
import { DeepMockProxy, mockDeep } from 'jest-mock-extended';
import { MyService } from './my.service';

describe('MyService', () => {
  let service: MyService;
  let prisma: DeepMockProxy<PrismaClient>;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [MyService, PrismaService],
    })
      .overrideProvider(PrismaService)
      .useValue(mockDeep<PrismaClient>())
      .compile();

    service = module.get<MyService>(MyService);
    prisma = module.get(PrismaService);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
```

## Event Sourcing Test Pattern

For services using the EventStore, mock the `events` table on the Prisma mock:

```typescript
beforeEach(async () => {
  // ... standard module setup ...

  prisma.events = {
    findMany: jest.fn().mockResolvedValue([]),
    findFirstOrThrow: jest.fn().mockRejectedValue(new Error('Not found')),
    findFirst: jest.fn().mockResolvedValue(null),
    create: jest.fn().mockResolvedValue({
      id: '1',
      eventStoreId: 'my-store',
      aggregateId: '1',
      version: 1,
      type: 'EventType',
      payload: '{}',
      metadata: null,
      timestamp: new Date(),
      aggregateClassVersion: 1,
    }),
  } as any;
});
```

When testing commands that update aggregates, mock existing events for aggregate initialization:

```typescript
const existingEvent = {
  id: '1',
  eventStoreId: 'store-name',
  aggregateId: entityId,
  version: 1,
  type: 'CORE.ENTITY.ENTITY_CREATED',
  payload: JSON.stringify({ /* initial state */ }),
  metadata: null,
  timestamp: new Date(),
  aggregateClassVersion: 1,
};

prisma.events.findMany.mockResolvedValue([existingEvent] as any);
```

## Command Test Pattern

For domain command tests, mock the aggregate factory:

```typescript
const makeAggregate = () => ({
  initialize: jest.fn().mockResolvedValue(undefined),
  commit: jest.fn().mockImplementation(async ({ payload, type }) => ({
    id: 'event-id',
    type,
    version: 1,
    timestamp: new Date(),
    aggregate: { id: 'entity-1' },
    payload,
    metadata: {
      actor: { type: 'COMPANY_USER', userId: 1 },
      company: { id: 1 },
    },
  })),
}) as any;
```

## Key Patterns

- Use `describe`/`it` BDD nesting for grouping related tests
- Use `jest.clearAllMocks()` in `afterEach`
- Import `EventStoreModule.register()` when service depends on event store
- Override `PrismaService` with `mockDeep<PrismaClient>()` — never use real DB in unit tests
- Use `@responsibid/testing` factories when available for domain entities
- Use `@faker-js/faker` for generating random test data
- Use `expect.objectContaining()` and `expect.arrayContaining()` for partial matching
- Use `expect.any(String)` for generated IDs

## Running Tests

All tests run inside the `sail-graphql-1` Docker container:

```bash
docker exec -it sail-graphql-1 bash -c "yarn nx run <project>:test --maxWorkers=7"
```

To run a specific test file:

```bash
docker exec -it sail-graphql-1 bash -c "yarn nx run <project>:test --testPathPattern='<pattern>' --maxWorkers=7"
```

## Determining the Nx Project

To find which Nx project a file belongs to, check the nearest `project.json` by walking up from the file's directory. The project name is in `project.json` → `"name"` field. Common projects: `server`, `payment`, `orchestrator`, `projector`, `reactor`, `event-store`, `core`.
