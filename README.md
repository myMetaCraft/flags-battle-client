# flags-battle-client — public

Browser client for Flags Battle. 195 flags bounce inside a ring with a rotating
gap; an orange segment counter-rotates and plugs the gap. Flags that escape are
out. Last one standing wins.

## Two modes

**Offline (default).** Open `index.html` and everything runs locally with demo
credits. Good for testing feel and for GitHub Pages.

**Online.** Append the server URL:

```
https://your-pages-url/?server=https://your-app.up.railway.app
```

The server then drives rounds, balances, payouts and chat.

## Maths

Odds are `floor(flags × (1 − edge))`. At 195 flags and a 4% edge that is 187.2×,
so RTP is 96.00%. Rounding **down** matters: covering every flag stakes 195 to
win 187.20, a guaranteed loss. Round up and players buy the whole board for a
risk-free profit.

Starting positions are randomised every round, so no flag is favoured. The
built-in fairness test runs thousands of headless rounds and checks the winner
distribution with a chi-square test.

## sim-core.js

Shared, deterministic, and identical to the server's copy. Uses only `+ - * /`
and `sqrt` — no `Math.sin`/`cos` in the simulation path — so the same seed gives
the same winner on every device. Do not edit it here alone; bump `SIM_VERSION`
and update the server repo too.

## Note

Flag emoji do not render on Windows; those users see ISO codes instead. That is
a Windows font limitation, not a bug.
