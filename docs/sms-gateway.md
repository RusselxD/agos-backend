# SMS Gateway Setup

AGOS uses an Android phone as an SMS gateway for OTP delivery and bulk SMS. The phone runs the [SMSGate](https://github.com/capcom6/android-sms-gateway) app, which exposes a REST API that the backend calls to send messages.

## How It Works

```
AGOS Backend ──HTTP POST──► SMSGate App (Android) ──SMS──► Recipient Phone
                              │
                              └── Uses SIM card balance to send
```

## Requirements

- Android phone with a SIM card that has SMS load/credits
- [SMSGate APK](https://github.com/capcom6/android-sms-gateway/releases) installed
- SMS permission granted to SMSGate

## Installation

1. Download the latest `.apk` from [GitHub Releases](https://github.com/capcom6/android-sms-gateway/releases)
2. On your phone: **Settings > Security > Install unknown apps** → allow your browser
3. Install the APK
4. If Google Play Protect blocks it: **Settings > Google > Play Protect > gear icon > disable "Scan apps with Play Protect"** temporarily
5. Grant SMS permission: **Settings > Apps > SMSGate > three dots (top right) > Allow restricted settings**, then **Permissions > SMS > Allow**
6. Re-enable Play Protect after granting permissions

## Configuration Modes

### Local Mode (development, same network)

Use when your backend server and phone are on the same WiFi network.

1. Open SMSGate → toggle **Local Server** on
2. Note the **Local address**, **Username**, and **Password**
3. Set in `.env`:
   ```
   SMS_GATEWAY_URL=http://192.168.x.x:8080
   SMS_GATEWAY_API_KEY=username:password
   ```

### Cloud Mode (production, deployed backend)

Use when your backend is deployed to a cloud server.

1. Open SMSGate → toggle **Cloud Server** on → tap **Online**
2. Note the **Server address**, **Username**, and **Password**
3. Set in `.env`:
   ```
   SMS_GATEWAY_URL=https://api.sms-gate.app
   SMS_GATEWAY_API_KEY=username:password
   ```

The cloud server acts as a relay: your backend sends the request to `api.sms-gate.app`, which forwards it to your phone, and the phone sends the SMS.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SMS_GATEWAY_URL` | `""` | Gateway URL. Empty = SMS disabled (OTPs logged to console). |
| `SMS_GATEWAY_API_KEY` | `""` | Credentials as `username:password`. |
| `SMS_GATEWAY_TIMEOUT_SECONDS` | `30` | HTTP request timeout. |
| `SMS_BULK_DELAY_SECONDS` | `1.5` | Delay between messages in bulk send (carrier throttle prevention). |

## API Format

The backend sends requests to the SMSGate API:

**Local mode:** `POST http://<phone-ip>:8080/message`
**Cloud mode:** `POST https://api.sms-gate.app/3rdparty/v1/message`

```json
{
  "phoneNumbers": ["+639171234567"],
  "message": "Your AGOS OTP code is: 123456"
}
```

Authentication: HTTP Basic Auth with the username and password from the app.

## Error Handling

| Scenario | What happens |
|----------|-------------|
| Gateway not configured (`SMS_GATEWAY_URL=""`) | OTP is generated and stored but not sent. Printed to console for dev testing. |
| Phone offline / app not running | `SMSGatewayUnavailableError` → HTTP 503 returned to client. |
| HTTP timeout (phone unresponsive) | `SMSGatewayUnavailableError` → HTTP 503 returned to client. |
| No SIM load / delivery failure | `SMSDeliveryError` → HTTP 503 returned to client. |
| Bulk send partial failure | HTTP 207 with count of succeeded/failed. |

## Testing

Verify connectivity:
```bash
curl -u username:password http://<phone-ip>:8080/
# Should return: {"status":"ok","model":"..."}
```

Send a test SMS:
```bash
curl -u username:password -X POST http://<phone-ip>:8080/message \
  -H "Content-Type: application/json" \
  -d '{"phoneNumbers": ["+639171234567"], "message": "Test from AGOS"}'
```

Check delivery status:
```bash
curl -u username:password http://<phone-ip>:8080/message/<message-id>
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `android.permission.SEND_SMS` error | Grant SMS permission (see Installation step 5) |
| `Connection refused` on port 8080 | Ensure Local Server is toggled on and phone is on same network |
| `Unauthorized` response | Check credentials match what the app shows; verify the trailing characters |
| Messages stuck in "Pending" | SIM has no load, or SMS permission not granted |
| Cloud mode `Unauthorized` | Ensure you're using cloud credentials (different from local) and phone is Online |

## Code Reference

- Service: `app/services/sms_service.py`
- Exceptions: `app/core/exceptions.py`
- Config: `app/core/config.py` (SMS_GATEWAY_* settings)
- Usage: `app/services/responder/responder_app_service.py` (send_otp, send_sms)
