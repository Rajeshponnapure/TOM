# Backend Development — Comprehensive Skill Guide

## Table of Contents
1. FastAPI Patterns
2. Node.js / Express Best Practices
3. NestJS Modular Architecture
4. Django REST Framework
5. Spring Boot Patterns
6. Authentication Strategies
7. API Design (RESTful)
8. Database Optimization
9. Caching Layer Design
10. Rate Limiting
11. Error Handling Patterns
12. Logging Best Practices

---

## 1. FastAPI Patterns

### Project Structure

```
project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── dependencies.py
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── endpoints/
│   │       │   ├── users.py
│   │       │   └── items.py
│   │       └── router.py
│   ├── models/
│   │   ├── user.py
│   │   └── item.py
│   ├── schemas/
│   │   ├── user.py
│   │   └── item.py
│   ├── services/
│   │   ├── user_service.py
│   │   └── item_service.py
│   └── db/
│       ├── session.py
│       └── base.py
├── alembic/
├── tests/
├── Dockerfile
└── requirements.txt
```

### Dependency Injection

```python
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService

app = FastAPI()

async def get_user_service(
    session: AsyncSession = Depends(get_session)
) -> UserService:
    return UserService(session)

@app.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    service: UserService = Depends(get_user_service),
):
    user = await service.create_user(user_data)
    if not user:
        raise HTTPException(400, "User creation failed")
    return user
```

### Background Tasks

```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

def send_welcome_email(email: str):
    import time
    time.sleep(2)
    print(f"Welcome email sent to {email}")

def generate_report(user_id: int):
    print(f"Generating report for user {user_id}")

@app.post("/register")
async def register(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_welcome_email, email)
    background_tasks.add_task(generate_report, 42)
    return {"message": "User registered, emails will be sent"}
```

### WebSockets

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active_connections.remove(ws)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(ws: WebSocket, client_id: str):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            await manager.broadcast(f"Client {client_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(ws)
```

### Streaming Responses

```python
from fastapi.responses import StreamingResponse
import asyncio

async def generate_events():
    for i in range(10):
        yield f"data: Event {i}\n\n"
        await asyncio.sleep(1)

@app.get("/events")
async def sse():
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

---

## 2. Node.js / Express Best Practices

### Project Setup

```typescript
import express, { Request, Response, NextFunction } from 'express';
import helmet from 'helmet';
import cors from 'cors';
import compression from 'compression';
import rateLimit from 'express-rate-limit';

const app = express();

// Security middleware
app.use(helmet());
app.use(cors({ origin: process.env.ALLOWED_ORIGINS?.split(',') }));
app.use(compression());
app.use(express.json({ limit: '10kb' }));

// Rate limiting
app.use(rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
}));

// Routes
app.use('/api/v1', router);

// Global error handler
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack);
  res.status(500).json({
    status: 'error',
    message: process.env.NODE_ENV === 'production'
      ? 'Internal server error'
      : err.message,
  });
});
```

### Controller-Service-Repository Pattern

```typescript
// repository/user.repository.ts
export class UserRepository {
  async findById(id: string): Promise<User | null> {
    return prisma.user.findUnique({ where: { id } });
  }

  async create(data: CreateUserDTO): Promise<User> {
    return prisma.user.create({ data });
  }
}

// service/user.service.ts
export class UserService {
  constructor(private repo: UserRepository) {}

  async createUser(dto: CreateUserDTO): Promise<User> {
    const existing = await this.repo.findByEmail(dto.email);
    if (existing) throw new ConflictError('Email already exists');

    const hashed = await bcrypt.hash(dto.password, 12);
    return this.repo.create({ ...dto, password: hashed });
  }
}

// controller/user.controller.ts
export class UserController {
  constructor(private service: UserService) {}

  create = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const user = await this.service.createUser(req.body);
      res.status(201).json({ data: user });
    } catch (err) {
      next(err);
    }
  };
}
```

---

## 3. NestJS Modular Architecture

### Module Structure

```typescript
// users/users.module.ts
@Module({
  imports: [
    TypeOrmModule.forFeature([User]),
    forwardRef(() => AuthModule),
  ],
  controllers: [UsersController],
  providers: [
    UsersService,
    UsersRepository,
    {
      provide: 'CACHE_SERVICE',
      useClass: RedisCacheService,
    },
  ],
  exports: [UsersService],
})
export class UsersModule {}
```

### Guards, Interceptors, Pipes

```typescript
// Guard — Authorization
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<Role[]>('roles', [
      context.getHandler(),
      context.getClass(),
    ]);
    if (!requiredRoles) return true;

    const { user } = context.switchToHttp().getRequest();
    return requiredRoles.some(role => user.roles?.includes(role));
  }
}

// Interceptor — Transform response
@Injectable()
export class TransformInterceptor<T> implements NestInterceptor<T, Response<T>> {
  intercept(context: ExecutionContext, next: CallHandler): Observable<Response<T>> {
    return next.handle().pipe(
      map(data => ({
        success: true,
        data,
        timestamp: new Date().toISOString(),
      })),
    );
  }
}

// Pipe — Validation
@Injectable()
export class ParseObjectIdPipe implements PipeTransform<string, string> {
  transform(value: string): string {
    if (!mongoose.Types.ObjectId.isValid(value)) {
      throw new BadRequestException('Invalid ObjectId');
    }
    return value;
  }
}
```

---

## 4. Django REST Framework

### ViewSets & Serializers

```python
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related('posts').all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['is_active', 'role']
    search_fields = ['email', 'username', 'profile__name']
    ordering_fields = ['created_at', 'email']

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'status': 'deactivated'})

    @action(detail=False)
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
```

### Performance with select_related / prefetch_related

```python
# Bad: N+1 queries
users = User.objects.all()
for user in users:
    print(user.profile.bio)  # Extra query per user

# Good: Join with select_related (ForeignKey, OneToOne)
users = User.objects.select_related('profile').all()

# Good: Prefetch for ManyToMany, reverse FK
users = User.objects.prefetch_related('posts__comments').all()
```

---

## 5. Spring Boot Patterns

### REST Controller

```java
@RestController
@RequestMapping("/api/v1/users")
@Validated
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUser(@PathVariable UUID id) {
        return ResponseEntity.ok(userService.findById(id));
    }

    @PostMapping
    public ResponseEntity<UserResponse> createUser(
        @Valid @RequestBody CreateUserRequest request,
        UriComponentsBuilder uriBuilder
    ) {
        UserResponse user = userService.create(request);
        URI location = uriBuilder.path("/api/v1/users/{id}")
            .buildAndExpand(user.id())
            .toUri();
        return ResponseEntity.created(location).body(user);
    }

    @GetMapping
    public ResponseEntity<Page<UserResponse>> listUsers(
        @PageableDefault(size = 20, sort = "createdAt") Pageable pageable,
        @RequestParam(required = false) String search
    ) {
        return ResponseEntity.ok(userService.findAll(search, pageable));
    }
}
```

### Service Layer

```java
@Service
@Transactional
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserResponse findById(UUID id) {
        return userRepository.findById(id)
            .map(UserResponse::from)
            .orElseThrow(() -> new ResourceNotFoundException("User", id));
    }

    public UserResponse create(CreateUserRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new ConflictException("Email already in use");
        }

        User user = User.builder()
            .email(request.email())
            .password(passwordEncoder.encode(request.password()))
            .name(request.name())
            .build();

        return UserResponse.from(userRepository.save(user));
    }
}
```

---

## 6. Authentication Strategies

### JWT Implementation

```typescript
// JWT Service
class JWTService {
  private readonly secret: string;
  private readonly expiresIn: string;

  sign(payload: JWTPayload): string {
    return jwt.sign(payload, this.secret, {
      expiresIn: this.expiresIn,
      algorithm: 'HS256',
    });
  }

  verify(token: string): JWTPayload {
    try {
      return jwt.verify(token, this.secret) as JWTPayload;
    } catch (error) {
      if (error instanceof jwt.TokenExpiredError) {
        throw new UnauthorizedError('Token expired');
      }
      throw new UnauthorizedError('Invalid token');
    }
  }
}

// Auth middleware
function authenticate(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;

  if (!authHeader?.startsWith('Bearer ')) {
    throw new UnauthorizedError('Missing authorization header');
  }

  const token = authHeader.split(' ')[1];
  const payload = jwtService.verify(token);

  req.user = payload;
  next();
}
```

### OAuth2 Flow (Authorization Code)

```typescript
// Passport.js strategy
passport.use(new GoogleStrategy({
  clientID: process.env.GOOGLE_CLIENT_ID!,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
  callbackURL: '/auth/google/callback',
  scope: ['profile', 'email'],
}, async (accessToken, refreshToken, profile, done) => {
  try {
    let user = await User.findOne({ googleId: profile.id });

    if (!user) {
      user = await User.create({
        googleId: profile.id,
        email: profile.emails?.[0].value,
        name: profile.displayName,
        avatar: profile.photos?.[0].value,
      });
    }

    done(null, user);
  } catch (error) {
    done(error as Error);
  }
}));
```

---

## 7. API Design (RESTful)

### URL Conventions

```
# Collection
GET    /api/v1/users          → List users (with pagination, filtering)
POST   /api/v1/users          → Create user

# Single resource
GET    /api/v1/users/:id      → Get user
PUT    /api/v1/users/:id      → Full update
PATCH  /api/v1/users/:id      → Partial update
DELETE /api/v1/users/:id      → Delete user

# Sub-resources
GET    /api/v1/users/:id/posts       → User's posts
GET    /api/v1/users/:id/posts/:pid  → Specific post by user

# Actions (rarely needed; use sub-resources)
POST   /api/v1/users/:id/activate    → Custom action
```

### Response Format

```typescript
// Success
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "perPage": 20,
    "total": 100,
    "totalPages": 5
  }
}

// Error
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      { "field": "email", "message": "Must be a valid email" }
    ],
    "requestId": "req_abc123"
  }
}
```

### HATEOAS

```typescript
function enrichWithLinks(resource: any, links: Link[]) {
  return {
    ...resource,
    _links: links.map(l => ({
      rel: l.rel,
      href: l.href,
      method: l.method,
    })),
  };
}

// Example response
GET /api/v1/users/123

{
  "id": "123",
  "name": "Tom",
  "_links": {
    "self": { "href": "/api/v1/users/123", "method": "GET" },
    "posts": { "href": "/api/v1/users/123/posts", "method": "GET" },
    "update": { "href": "/api/v1/users/123", "method": "PATCH" },
    "delete": { "href": "/api/v1/users/123", "method": "DELETE" }
  }
}
```

---

## 8. Database Optimization

### N+1 Query Solution

```sql
-- Bad: N+1 queries
SELECT * FROM users;  -- 1 query
-- For each user:
SELECT * FROM posts WHERE user_id = ?;  -- N queries

-- Good: JOIN
SELECT u.*, p.*
FROM users u
LEFT JOIN posts p ON p.user_id = u.id;

-- Good: Batch with WHERE IN
SELECT * FROM users;
SELECT * FROM posts WHERE user_id IN (1, 2, 3, ..., N);
```

### Indexing Strategies

```sql
-- B-tree indexes (default)
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status_created ON users(status, created_at DESC);

-- Partial index
CREATE INDEX idx_users_active ON users(email) WHERE is_active = true;

-- Covering index (includes all queried columns)
CREATE INDEX idx_users_list ON users(status, created_at DESC) INCLUDE (name, email);

-- GIN for JSON/array columns
CREATE INDEX idx_metadata ON documents USING GIN (metadata jsonb_path_ops);

-- Full-text search index
CREATE INDEX idx_search ON documents USING GIN (to_tsvector('english', content));

-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'tom@example.com';
```

---

## 9. Caching Layer Design

### Cache Strategy

```typescript
// Cache-Aside Pattern
async function getUser(id: string): Promise<User> {
  // 1. Try cache first
  const cached = await redis.get(`user:${id}`);
  if (cached) return JSON.parse(cached);

  // 2. Fall back to database
  const user = await db.user.findUnique({ where: { id } });

  // 3. Populate cache (with TTL)
  if (user) {
    await redis.setex(`user:${id}`, 3600, JSON.stringify(user));
  }

  return user;
}

// Write-Behind (lazy invalidation)
async function updateUser(id: string, data: UpdateUserDTO) {
  const user = await db.user.update({ where: { id }, data });

  // Invalidate cache instead of updating it
  await redis.del(`user:${id}`);
  await redis.publish('cache:invalidate', `user:${id}`);

  return user;
}
```

### Multi-Layer Cache

```
Browser Cache (Cache-Control headers)
  ↓
CDN Cache (CloudFront / Cloudflare)
  ↓
Application Cache (Redis / Memcached)
  ↓
Database Cache (shared_buffers / buffer pool)
```

### Cache-Control Headers

```typescript
// Immutable static assets
res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');

// API responses
res.setHeader('Cache-Control', 'private, max-age=60, stale-while-revalidate=600');

// Dynamic content
res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
```

---

## 10. Rate Limiting

### Token Bucket Algorithm

```typescript
class TokenBucket {
  private tokens: number;
  private lastRefill: number;

  constructor(
    private maxTokens: number,
    private refillRate: number, // tokens per second
    private refillInterval: number, // ms
  ) {
    this.tokens = maxTokens;
    this.lastRefill = Date.now();
  }

  tryConsume(count: number = 1): boolean {
    this.refill();

    if (this.tokens >= count) {
      this.tokens -= count;
      return true;
    }

    return false;
  }

  private refill(): void {
    const now = Date.now();
    const elapsed = now - this.lastRefill;
    const tokensToAdd = Math.floor(elapsed / this.refillInterval) * this.refillRate;

    if (tokensToAdd > 0) {
      this.tokens = Math.min(this.maxTokens, this.tokens + tokensToAdd);
      this.lastRefill = now;
    }
  }
}
```

### Rate Limit Headers

```
RateLimit-Limit: 100
RateLimit-Remaining: 87
RateLimit-Reset: 1700000000
Retry-After: 45
```

---

## 11. Error Handling Patterns

### Typed Error Classes

```typescript
export class AppError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code: string,
    public isOperational: boolean = true,
  ) {
    super(message);
    Error.captureStackTrace(this, this.constructor);
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string, id?: string) {
    super(
      id ? `${resource} with id ${id} not found` : `${resource} not found`,
      404,
      'NOT_FOUND',
    );
  }
}

export class ValidationError extends AppError {
  constructor(public details: ValidationDetail[]) {
    super('Validation failed', 422, 'VALIDATION_ERROR');
  }
}

export class UnauthorizedError extends AppError {
  constructor(message = 'Unauthorized') {
    super(message, 401, 'UNAUTHORIZED');
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super(message, 409, 'CONFLICT');
  }
}
```

### Global Error Handler (Node.js)

```typescript
function globalErrorHandler(
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction,
) {
  // Log all errors
  logger.error({
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
    requestId: req.id,
  });

  // Handle known operational errors
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      success: false,
      error: {
        code: err.code,
        message: err.message,
        details: (err as ValidationError).details,
      },
    });
  }

  // Handle unknown errors
  return res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_ERROR',
      message: process.env.NODE_ENV === 'production'
        ? 'An unexpected error occurred'
        : err.message,
    },
  });
}
```

---

## 12. Logging Best Practices

### Structured Logging

```python
import structlog
import logging

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer() if DEBUG
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage
logger.info("user_created", user_id=123, email="tom@example.com")
logger.error("payment_failed", error="insufficient_funds", amount=50.00)
```

### Log Levels

| Level | Use Case | Example |
|-------|----------|---------|
| ERROR | System is broken | Database connection failed |
| WARN | Something unexpected but handled | Rate limit approaching, retry attempted |
| INFO | Normal operational milestones | User created, payment processed |
| DEBUG | Development troubleshooting | Query parameters, function entry/exit |
| TRACE | Deep diagnostics | Loop iterations, line-by-line flow |

### Logging Best Practices

```typescript
// Include correlation ID for request tracing
app.use((req, res, next) => {
  req.id = req.headers['x-request-id'] || uuidv4();
  res.setHeader('x-request-id', req.id);
  next();
});

// Never log sensitive data
function sanitizeForLogging(data: any): any {
  const sensitive = ['password', 'creditCard', 'ssn', 'secret', 'token'];
  const sanitized = { ...data };

  for (const key of sensitive) {
    if (key in sanitized) {
      sanitized[key] = '[REDACTED]';
    }
  }

  return sanitized;
}

// Context-aware logging
logger.info('processing_order', extra: {
  orderId: order.id,
  userId: order.userId,
  amount: order.total,
  items: order.items.length,
  duration_ms: Date.now() - start,
});
```

---

## Deployment Checklist

- [ ] Environment variables configured (not in code)
- [ ] CORS whitelist set for production
- [ ] Rate limiting enabled
- [ ] Request body size limited
- [ ] HTTPS enforced (TLS 1.3)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS protection headers set
- [ ] CORS preflight cache configured
- [ ] Error messages don't leak internals
- [ ] Health check endpoint (`/health`)
- [ ] Graceful shutdown handlers
- [ ] Process manager configured (PM2/supervisor)
- [ ] Database connection pooling tuned
- [ ] CI/CD pipeline with tests
