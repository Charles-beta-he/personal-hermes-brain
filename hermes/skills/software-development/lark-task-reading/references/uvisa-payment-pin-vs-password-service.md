# UVISA Payment PIN vs Payment Password — Two Separate Services

## The Gotcha

UVISA backend has TWO independent credential services that are easy to confuse:

| Service | Field | Format | Endpoint prefix |
|---------|-------|--------|-----------------|
| `PaymentPinService` | `paymentPinHash` | 6-digit numeric PIN | `/auth/pin/*` |
| `PaymentPasswordService` | `paymentPasswordHash` | 8-64 char alphanumeric | `/auth/payment-password/*` |

Both use BCrypt. Both return `PIN_NOT_SET(20021)` when the hash field is null. But they check **different database columns**.

## How the confusion happens

- User sets a 6-digit PIN during first login → `PaymentPinService.setPin()` → saves to `paymentPinHash`
- User tries to change PIN via Security Center → `ChangePaymentPwdScreen` calls `authService.verifyPaymentPassword()` → calls `POST /auth/pin/verify` → `PaymentPinService.verify()` → checks `paymentPinHash` ✓
- But if the frontend accidentally calls `/auth/payment-password/verify` instead → `PaymentPasswordService.verify()` → checks `paymentPasswordHash` → null → `PIN_NOT_SET` error

## Frontend method naming (confusing but correct)

In `auth.service.ts`:
- `verifyPaymentPassword(pin)` → `POST /auth/pin/verify` (correct: uses PIN service)
- `changePaymentPassword(oldPin, newPin)` → `POST /auth/pin/change` (correct: uses PIN service)

The method names say "Password" but the URLs say "pin". This is intentional per the ADR comment on line 96-99.

## Backend routing

```
POST /auth/pin/verify        → LegacyApiController → PaymentPinService.verify()
POST /auth/pin/change        → LegacyApiController → PaymentPinService.verify() + setPin()
POST /auth/pin/setup         → LegacyApiController → PaymentPinService.setPin()
POST /auth/payment-password/verify → LegacyApiController → PaymentPasswordService.verify()
POST /auth/payment-password/change → LegacyApiController → PaymentPasswordService.change()
```

Also available at `/api/me/payment-pin/*` and `/api/me/payment-password/*` (MeController).

## Fix pattern for ChangePaymentPwdScreen

Add a guard: if `hasPaymentPin === false`, redirect to `/pin-setup` instead of letting the user enter an old PIN that will fail with `PIN_NOT_SET`.

```tsx
const hasPaymentPin = useAuthStore((s) => s.user?.hasPaymentPin);
useEffect(() => {
  if (hasPaymentPin === false) nav("/pin-setup", { replace: true });
}, [hasPaymentPin, nav]);
```

## When debugging PIN errors

1. Check which service is being called: `PaymentPinService` or `PaymentPasswordService`
2. Check which DB column: `paymentPinHash` or `paymentPasswordHash`
3. Check if `hasPaymentPin` is true in the frontend store
4. The error message "未设置支付密码" comes from `ErrorCode.PIN_NOT_SET(20021)` — same code for both services
