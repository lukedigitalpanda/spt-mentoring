# JaaS (8x8) setup for video calls

The mentoring platform mints its own moderator tokens for video calls. To enable
this you need a free 8x8 JaaS account and three secrets in `.env`.

## 1. Create the JaaS app
1. Go to https://jaas.8x8.vc and sign up / log in.
2. Create an application. Note the **App ID** — it looks like
   `vpaas-magic-cookie-xxxxxxxxxxxx`.

## 2. Generate an API key
1. In the JaaS console, open **API Keys** and add a new key pair.
2. Download/keep the **private key** (PEM). The console keeps the public half.
3. Note the **Key ID (kid)** shown for the key — usually
   `vpaas-magic-cookie-xxxx/yyyyyy`.

## 3. Put the secrets in `.env`
- `JAAS_APP_ID` = the App ID from step 1.
- `JAAS_KID` = the Key ID from step 2.
- `JAAS_PRIVATE_KEY` = the private key PEM on **one line** with `\n` between each
  line. To convert a key file to a single line:

  ```bash
  awk 'NF {printf "%s\\n", $0}' your-key.pk > one-line.txt
  ```

  Paste the result after `JAAS_PRIVATE_KEY=`.

## 4. Apply
```bash
docker compose up -d backend
```

`docker compose restart` does NOT pick up `.env` changes — use `up -d`.

## Verifying
- With the three vars set, the "Join video call" button opens an `8x8.vc` URL and
  the call starts immediately with no log-in gate.
- If the vars are blank, the platform falls back to the public `meet.jit.si`
  server (the old behaviour, including its moderator gate).
