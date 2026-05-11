# UVISA Backend Authenticated Endpoint Data Leak Pattern

## Problem

The UVISA backend has two sets of topup config endpoints:

| Endpoint | Auth | Returns | Masking |
|----------|------|---------|---------|
| `GET /api/platform-config/topup` | Public | `sanitizeTopupConfig()` | ✅ Whitelist fields, mask account numbers |
| `GET /api/topup/swift/details` | JWT required | `topupService.getSwiftDetails()` | ❌ Raw config_json |
| `GET /api/topup/cny/banks` | JWT required | `topupService.getCnyBankDetails()` | ❌ Raw config_json |

**Authenticated ≠ safe.** Just because an endpoint requires JWT doesn't mean it can return raw sensitive data. Any logged-in user (or stolen JWT) can call these endpoints and see unmasked bank account numbers.

## Fix

Add masking at the controller layer for authenticated endpoints. Keep internal methods (used by createSwiftTopup/createCnyTopup) returning raw data for transaction processing.

```java
@GetMapping("/swift/details")
public ApiResponse<Map<String, Object>> swiftDetails() {
    return ApiResponse.ok(maskReceivingFields(topupService.getSwiftDetails()));
}

private static Map<String, Object> maskReceivingFields(Map<String, Object> raw) {
    Map<String, Object> out = new LinkedHashMap<>(raw);
    for (String key : List.of("accountNumber", "account_number")) {
        Object val = out.get(key);
        if (val instanceof String s && !s.isEmpty()) {
            out.put(key, maskAccountNumber(s));
        }
    }
    return out;
}
```

## General principle

When auditing data exposure:
1. Check ALL endpoints that return sensitive data, not just public ones
2. Authenticated endpoints are often overlooked — they're "behind login" but still accessible to any valid user
3. The masking logic should be at the controller layer (response boundary), not in the service layer (which needs raw data for business logic)
4. `TopupService` (inner class) methods like `getSwiftDetails()` must remain raw; masking is the controller's job

## Detection pattern

```bash
# Find all endpoints that load config_json directly
grep -rn "loadTopupConfig\|config_json" api/api-public/src/main/java/
# Check if any return raw data without masking
grep -rn "getSwiftDetails\|getCnyBankDetails" api/api-public/src/main/java/ | grep -v mask
```
