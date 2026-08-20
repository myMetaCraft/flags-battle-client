# flags-battle-server — PRIVATE

Authoritative game server. **This repo must stay private.** It holds the RNG,
the payout logic and, once deployed, your credentials.

## Why the server decides everything

The browser never determines the winner. The server picks the seed, runs the
simulation, and pays out. The client receives the seed only so it can replay
the same round as an animation. A tampered client changes the pictures, not
the money.

## Provably fair (commit → reveal)

1. Before betting opens the server publishes `sha256(serverSeed)`.
2. `clientSeed` is public and derived from the previous round's result.
3. `roundSeed = HMAC-SHA256(serverSeed, "clientSeed:nonce")`, first 8 hex → uint32.
4. After the round `serverSeed` is revealed.

Anyone can then check the hash matches the commitment published *before* bets,
and recompute the winner. The server cannot pick a favourable seed after seeing
the bets, because it is locked in by the hash.

## Run locally

```bash
cp .env.example .env
npm install
npm start
```

## Deploy to Railway

- New project → deploy from this repo
- Set every variable from `.env.example` in Railway's Variables tab
- Set `CORS_ORIGIN` to your client's URL, not `*`
- Point the client at it: `https://your-client/?server=https://your-app.up.railway.app`

## sim-core.js must match the client

`sim-core.js` is byte-identical to the copy in the public client repo. If they
drift, the animation shows one winner and the server pays another. `SIM_VERSION`
guards this: a client on a different version is rejected at connect, and every
result is cross-checked client-side.

When you change the simulation, bump `SIM_VERSION` and update **both** repos.

## Before real money

This is a working prototype, not a production system.

- **State is in memory.** Balances and the audit trail vanish on restart. Move
  players, bets, rounds and chat to Postgres.
- **No accounts.** Identity is the socket id. Add real auth.
- **Chat logs are personal data.** Set a retention period and document it.
- **Swap the word list.** `moderation.js` ships a placeholder. The game is
  global, so English and Slovak alone are not enough.
- **Certification.** The RNG and the game maths need an accredited lab
  (GLI, BMM, eCOGRA, iTech) before any licensed operator can take this.
