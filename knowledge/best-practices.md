# Universal Coding Best Practices

## Code Structure
- Single Responsibility: One function/module = one job
- DRY: Extract repeated logic into reusable functions
- Keep functions small (< 30 lines)
- Maximum nesting depth: 3 levels
- Use early returns to reduce nesting

## Naming Conventions
- Classes: PascalCase (UserService, DataAnalyzer)
- Functions/Methods: camelCase (getUserById, calculateTotal)
- Variables: camelCase (userCount, totalAmount)
- Constants: UPPER_SNAKE_CASE (MAX_RETRIES, API_BASE_URL)
- Private members: _prefix (internal JS/TS convention)
- Booleans: is/has/should prefix (isActive, hasPermission, shouldRetry)

## Error Handling
- Never swallow exceptions silently
- Always provide context in error messages
- Use specific exception types, not generic ones
- Log at appropriate levels (DEBUG, INFO, WARN, ERROR)
- Graceful degradation: fail partially, not completely

## Performance
- Profile before optimizing. Never guess.
- Use lazy loading for expensive resources
- Batch database operations
- Cache frequently accessed data
- Use connection pooling for databases
- Minimize network roundtrips

## Security
- Validate ALL input (server-side, never trust client)
- Use parameterized queries for SQL
- Hash passwords with bcrypt/argon2
- Use HTTPS everywhere
- Implement proper CORS policies
- Rate limit API endpoints
- Sanitize file uploads
- Keep dependencies updated
