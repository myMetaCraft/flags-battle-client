"""
sim_core.py — Python port of sim-core.js for Stake Engine book generation.

CRITICAL: this must produce bit-for-bit identical results to the JavaScript
version. The frontend replays the round from the seed, so if Python and JS
ever disagree, the animation shows one winner while the RGS pays another.

That holds because the simulation uses only + - * / and sqrt, which IEEE 754
specifies exactly, and both languages use 64-bit doubles. The requirement is
that the ORDER OF OPERATIONS matches exactly — hence the deliberately
un-Pythonic style below. Do not "clean up" the arithmetic.

Verify with cross_check.py after any change.
"""

import math

SIM_VERSION = "2.0.0"

DT = 1.0 / 60.0
SPEED = 1.25
GAP_C, GAP_S = 0.99875026039, 0.04997916927     # +0.050 rad / step
YEL_C, YEL_S = 0.99920010666, 0.03998933419     # -0.040 rad / step
GAP_T0, GAP_T1, GAP_GROW = 0.98, 0.94, 18.0     # gap 23deg -> 40deg
YEL_THR = 0.93
RUSH = 5.5

# Endgame ramp. Mirror of the JavaScript constants — see sim-core.js for why.
RAMP_T0, RAMP_T1, RAMP_END = 40.0, 52.0, -1.0

ISO = ("AF AL DZ AD AO AG AR AM AU AT AZ BS BH BD BB BY BE BZ BJ BT BO BA BW BR BN BG BF BI CV KH CM "
       "CA CF TD CL CN CO KM CG CD CR CI HR CU CY CZ DK DJ DM DO EC EG SV GQ ER EE SZ ET FJ FI FR GA "
       "GM GE DE GH GR GD GT GN GW GY HT HN HU IS IN ID IR IQ IE IL IT JM JP JO KZ KE KI KP KR KW KG "
       "LA LV LB LS LR LY LI LT LU MG MW MY MV ML MT MH MR MU MX FM MD MC MN ME MA MZ MM NA NR NP NL "
       "NZ NI NE NG MK NO OM PK PW PS PA PG PY PE PH PL PT QA RO RU RW KN LC VC WS SM ST SA SN RS SC "
       "SL SG SK SI SB SO ZA SS ES LK SD SR SE CH SY TJ TZ TH TL TG TO TT TN TR TM TV UG UA AE GB US "
       "UY UZ VU VA VE VN YE ZM ZW").split()


# ---------- 32-bit integer helpers, mirroring JavaScript semantics ----------

def _u32(x):
    """JavaScript >>> 0"""
    return x & 0xFFFFFFFF


def _i32(x):
    """JavaScript | 0"""
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x


def _imul(a, b):
    """Math.imul: 32-bit signed multiply, low bits kept."""
    return _i32(_u32(a) * _u32(b))


def mulberry32(a):
    """Identical to the JS generator, including overflow behaviour."""
    state = [_i32(a)]

    def rnd():
        state[0] = _i32(state[0] + 0x6D2B79F5)
        a_ = state[0]
        t = _imul(a_ ^ (_u32(a_) >> 15), 1 | a_)
        t = _i32(_i32(t + _imul(t ^ (_u32(t) >> 7), 61 | t)) ^ t)
        return _u32(t ^ (_u32(t) >> 14)) / 4294967296.0

    return rnd


class Round:
    def __init__(self, seed, n):
        rnd = mulberry32(_u32(seed))
        self.n = n
        self.rnd = rnd
        self.t = 0.0
        self.r = 0.55 / math.sqrt(n)
        self.R = 1.0
        self.x = [0.0] * n
        self.y = [0.0] * n
        self.vx = [0.0] * n
        self.vy = [0.0] * n
        self.alive = [1] * n
        self.aliveCount = n
        self.dead = []
        self._winner = -1

        lim = self.R - self.r * 1.05
        for i in range(n):
            px = 0.0
            py = 0.0
            for _ in range(400):
                px = (rnd() * 2 - 1) * lim
                py = (rnd() * 2 - 1) * lim
                if px * px + py * py > lim * lim:
                    continue
                clash = False
                for j in range(i):
                    dx = px - self.x[j]
                    dy = py - self.y[j]
                    if dx * dx + dy * dy < (2.02 * self.r) * (2.02 * self.r):
                        clash = True
                        break
                if not clash:
                    break
            self.x[i] = px
            self.y[i] = py
            while True:
                dx = rnd() * 2 - 1
                dy = rnd() * 2 - 1
                d2 = dx * dx + dy * dy
                if not (d2 < 0.01 or d2 > 1):
                    break
            inv = SPEED / math.sqrt(d2)
            self.vx[i] = dx * inv
            self.vy[i] = dy * inv

        self.gx, self.gy = 1.0, 0.0
        self.yx, self.yy = 1.0, 0.0
        s1 = int(rnd() * 780)          # JS: (x)|0 truncates toward zero; x >= 0 here
        s2 = int(rnd() * 780)
        for _ in range(s1):
            self.rotGap()
        for _ in range(s2):
            self.rotYel()

        self.cell = self.r * 2.2
        self.gw = max(1, math.ceil(2 / self.cell))
        self.buckets = [[] for _ in range(self.gw * self.gw)]

    def rotGap(self):
        nx = self.gx * GAP_C - self.gy * GAP_S
        ny = self.gx * GAP_S + self.gy * GAP_C
        inv = 1 / math.sqrt(nx * nx + ny * ny)
        self.gx = nx * inv
        self.gy = ny * inv

    def rotYel(self):
        nx = self.yx * YEL_C + self.yy * YEL_S
        ny = -self.yx * YEL_S + self.yy * YEL_C
        inv = 1 / math.sqrt(nx * nx + ny * ny)
        self.yx = nx * inv
        self.yy = ny * inv

    def gapThreshold(self):
        p = self.t / GAP_GROW
        g = GAP_T0 + (GAP_T1 - GAP_T0) * (1 if p > 1 else p)
        if self.t <= RAMP_T0:
            return g
        q = (self.t - RAMP_T0) / (RAMP_T1 - RAMP_T0)
        return g + (RAMP_END - g) * (1 if q > 1 else q)

    # Neighbour cells for the collision grid. Only half the neighbours are
    # visited so each pair is tested once.
    _NB = ((0, 0), (1, 0), (-1, 1), (0, 1), (1, 1))

    def step(self):
        n, r, R = self.n, self.r, self.R
        self.t += DT
        self.rotGap()
        self.rotYel()
        gthr = self.gapThreshold()
        dt = DT * (1 + RUSH * (1 - self.aliveCount / n))

        # Locals: attribute lookups dominated the profile. The arithmetic and
        # its order are untouched — cross_check.py guards that.
        x, y, vx, vy, alive = self.x, self.y, self.vx, self.vy, self.alive
        gx, gy, yx, yy = self.gx, self.gy, self.yx, self.yy
        lim = R - r
        lim2 = lim * lim

        for i in range(n):
            if not alive[i]:
                continue
            x[i] += vx[i] * dt
            y[i] += vy[i] * dt
            xi = x[i]
            yi = y[i]
            d2 = xi * xi + yi * yi
            if d2 > lim2:
                d = math.sqrt(d2)
                nx = xi / d
                ny = yi / d
                if (nx * gx + ny * gy) >= gthr and (nx * yx + ny * yy) < YEL_THR \
                        and self.aliveCount > 1:
                    alive[i] = 0
                    self.aliveCount -= 1
                    self.dead.append(i)
                    continue
                x[i] = nx * lim
                y[i] = ny * lim
                dot = vx[i] * nx + vy[i] * ny
                vx[i] -= 2 * dot * nx
                vy[i] -= 2 * dot * ny

        b, gw, cs = self.buckets, self.gw, self.cell
        for bucket in b:
            if bucket:
                bucket.clear()
        for i in range(n):
            if not alive[i]:
                continue
            cx = int((x[i] + 1) / cs)
            cy = int((y[i] + 1) / cs)
            if cx < 0:
                cx = 0
            elif cx >= gw:
                cx = gw - 1
            if cy < 0:
                cy = 0
            elif cy >= gw:
                cy = gw - 1
            b[cy * gw + cx].append(i)

        md = 2 * r
        md2 = md * md
        for cy in range(gw):
            row = cy * gw
            for cx in range(gw):
                A = b[row + cx]
                if not A:
                    continue
                lenA = len(A)
                for ox, oy in self._NB:
                    nx2 = cx + ox
                    ny2 = cy + oy
                    if nx2 < 0 or nx2 >= gw or ny2 >= gw:
                        continue
                    B = b[ny2 * gw + nx2]
                    if not B:
                        continue
                    same = B is A
                    lenB = lenA if same else len(B)
                    for ii in range(lenA):
                        i = A[ii]
                        for jj in range(ii + 1 if same else 0, lenB):
                            j = B[jj]
                            # x[i]/y[i] must be re-read every pair: an earlier
                            # collision in this same loop may have moved i.
                            dx = x[j] - x[i]
                            dy = y[j] - y[i]
                            d2 = dx * dx + dy * dy
                            if d2 >= md2 or d2 == 0:
                                continue
                            d = math.sqrt(d2)
                            nx = dx / d
                            ny = dy / d
                            ov = (md - d) * 0.5
                            x[i] -= nx * ov
                            y[i] -= ny * ov
                            x[j] += nx * ov
                            y[j] += ny * ov
                            rvx = vx[j] - vx[i]
                            rvy = vy[j] - vy[i]
                            pdot = rvx * nx + rvy * ny
                            if pdot > 0:
                                continue
                            vx[i] += pdot * nx
                            vy[i] += pdot * ny
                            vx[j] -= pdot * nx
                            vy[j] -= pdot * ny

    def collide(self, i, j):
        dx = self.x[j] - self.x[i]
        dy = self.y[j] - self.y[i]
        d2 = dx * dx + dy * dy
        md = 2 * self.r
        if d2 >= md * md or d2 == 0:
            return
        d = math.sqrt(d2)
        nx = dx / d
        ny = dy / d
        ov = (md - d) * 0.5
        self.x[i] -= nx * ov
        self.y[i] -= ny * ov
        self.x[j] += nx * ov
        self.y[j] += ny * ov
        rvx = self.vx[j] - self.vx[i]
        rvy = self.vy[j] - self.vy[i]
        p = rvx * nx + rvy * ny
        if p > 0:
            return
        self.vx[i] += p * nx
        self.vy[i] += p * ny
        self.vx[j] -= p * nx
        self.vy[j] -= p * ny

    def finished(self):
        return self.aliveCount <= 1 or self.t > 90

    def winner(self):
        # Memoised: the draw below consumes the round's PRNG, so calling this
        # twice must not produce two different answers.
        if self._winner >= 0:
            return self._winner
        alive = [i for i in range(self.n) if self.alive[i]]
        if not alive:
            self._winner = 0
            return self._winner
        if len(alive) == 1:
            self._winner = alive[0]
            return self._winner
        # Time limit reached with more than one still in play. Draw one instead
        # of taking the first: the lowest index is never a neutral choice,
        # because the client puts the player's picks there.
        k = int(self.rnd() * len(alive))     # JS: (x)|0 truncates; x >= 0 here
        if k >= len(alive):
            k = len(alive) - 1
        self._winner = alive[k]
        return self._winner


def run_headless(seed, n):
    R = Round(seed, n)
    while not R.finished():
        R.step()
    return R.winner()


def odds_for(n, edge_pct):
    """Single-flag odds, floored so the house never loses the edge to rounding."""
    return math.floor(n * (1 - edge_pct / 100) * 100) / 100
