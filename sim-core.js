const SIM_VERSION = '1.1.0';
function mulberry32(a){
  return function(){
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const ISO = ("AF AL DZ AD AO AG AR AM AU AT AZ BS BH BD BB BY BE BZ BJ BT BO BA BW BR BN BG BF BI CV KH CM CA CF TD CL CN CO KM CG CD CR CI HR CU CY CZ DK DJ DM DO EC EG SV GQ ER EE SZ ET FJ FI FR GA GM GE DE GH GR GD GT GN GW GY HT HN HU IS IN ID IR IQ IE IL IT JM JP JO KZ KE KI KP KR KW KG LA LV LB LS LR LY LI LT LU MG MW MY MV ML MT MH MR MU MX FM MD MC MN ME MA MZ MM NA NR NP NL NZ NI NE NG MK NO OM PK PW PS PA PG PY PE PH PL PT QA RO RU RW KN LC VC WS SM ST SA SN RS SC SL SG SK SI SB SO ZA SS ES LK SD SR SE CH SY TJ TZ TH TL TG TO TT TN TR TM TV UG UA AE GB US UY UZ VU VA VE VN YE ZM ZW").split(" ");
const flagEmoji = c => String.fromCodePoint(...[...c].map(ch => 0x1F1E6 + ch.charCodeAt(0) - 65));
const DT = 1/60, SPEED = 1.25;
const GAP_C = 0.99875026039, GAP_S = 0.04997916927;
const YEL_C = 0.99920010666, YEL_S = 0.03998933419;
const GAP_T0 = 0.98, GAP_T1 = 0.94, GAP_GROW = 18;
const YEL_THR = 0.93;
const RUSH = 5.5;
const ARC_COLOR = '#FF8A2B';
const RING_COLOR = '#E6EBFA';
class Round {
  constructor(seed, n){
    const rnd = mulberry32(seed >>> 0);
    this.n = n; this.rnd = rnd; this.t = 0;
    this.r = 0.55 / Math.sqrt(n);
    this.R = 1;
    this.x = new Float64Array(n); this.y = new Float64Array(n);
    this.vx = new Float64Array(n); this.vy = new Float64Array(n);
    this.alive = new Uint8Array(n).fill(1);
    this.aliveCount = n;
    this.dead = [];
    this.trackEscapes = false; this.escapes = [];
    const lim = this.R - this.r * 1.05;
    for (let i = 0; i < n; i++){
      let px = 0, py = 0;
      for (let a = 0; a < 400; a++){
        px = (rnd()*2 - 1) * lim; py = (rnd()*2 - 1) * lim;
        if (px*px + py*py > lim*lim) continue;
        let clash = false;
        for (let j = 0; j < i; j++){
          const dx = px - this.x[j], dy = py - this.y[j];
          if (dx*dx + dy*dy < (2.02*this.r)*(2.02*this.r)) { clash = true; break; }
        }
        if (!clash) break;
      }
      this.x[i] = px; this.y[i] = py;
      let dx = 0, dy = 0, d2 = 0;
      do { dx = rnd()*2 - 1; dy = rnd()*2 - 1; d2 = dx*dx + dy*dy; } while (d2 < 0.01 || d2 > 1);
      const inv = SPEED / Math.sqrt(d2);
      this.vx[i] = dx*inv; this.vy[i] = dy*inv;
    }
    this.gx = 1; this.gy = 0;
    this.yx = 1; this.yy = 0;
    let s1 = (rnd() * 780) | 0, s2 = (rnd() * 780) | 0;
    for (let s = 0; s < s1; s++) this.rotGap();
    for (let s = 0; s < s2; s++) this.rotYel();
    this.cell = this.r * 2.2;
    this.gw = Math.max(1, Math.ceil(2 / this.cell));
    this.buckets = Array.from({length: this.gw*this.gw}, () => []);
  }
  rotGap(){
    const nx = this.gx*GAP_C - this.gy*GAP_S;
    const ny = this.gx*GAP_S + this.gy*GAP_C;
    const inv = 1 / Math.sqrt(nx*nx + ny*ny);
    this.gx = nx*inv; this.gy = ny*inv;
  }
  rotYel(){
    const nx = this.yx*YEL_C + this.yy*YEL_S;
    const ny = -this.yx*YEL_S + this.yy*YEL_C;
    const inv = 1 / Math.sqrt(nx*nx + ny*ny);
    this.yx = nx*inv; this.yy = ny*inv;
  }
  gapThreshold(){
    const p = this.t / GAP_GROW;
    return GAP_T0 + (GAP_T1 - GAP_T0) * (p > 1 ? 1 : p);
  }
  step(){
    const n = this.n, r = this.r, R = this.R;
    this.t += DT; this.rotGap(); this.rotYel();
    const gthr = this.gapThreshold();
    const dt = DT * (1 + RUSH * (1 - this.aliveCount / n));
    for (let i = 0; i < n; i++){
      if (!this.alive[i]) continue;
      this.x[i] += this.vx[i]*dt; this.y[i] += this.vy[i]*dt;
      const d2 = this.x[i]*this.x[i] + this.y[i]*this.y[i];
      const lim = R - r;
      if (d2 > lim*lim){
        const d = Math.sqrt(d2), nx = this.x[i]/d, ny = this.y[i]/d;
        const inGap = (nx*this.gx + ny*this.gy) >= gthr;
        const blocked = (nx*this.yx + ny*this.yy) >= YEL_THR;
        if (inGap && !blocked && this.aliveCount > 1){
          this.alive[i] = 0; this.aliveCount--; this.dead.push(i);
          if (this.trackEscapes)
            this.escapes.push({i, x:this.x[i], y:this.y[i], vx:nx*0.9, vy:ny*0.9});
          continue;
        }
        this.x[i] = nx*lim; this.y[i] = ny*lim;
        const dot = this.vx[i]*nx + this.vy[i]*ny;
        this.vx[i] -= 2*dot*nx; this.vy[i] -= 2*dot*ny;
      }
    }
    if (this.trackEscapes){
      for (let k = this.escapes.length - 1; k >= 0; k--){
        const e = this.escapes[k];
        e.x += e.vx*dt*2.2; e.y += e.vy*dt*2.2;
        if (e.x*e.x + e.y*e.y > 2.4) this.escapes.splice(k, 1);
      }
    }
    const b = this.buckets, gw = this.gw, cs = this.cell;
    for (let k = 0; k < b.length; k++) b[k].length = 0;
    for (let i = 0; i < n; i++){
      if (!this.alive[i]) continue;
      let cx = ((this.x[i]+1)/cs)|0, cy = ((this.y[i]+1)/cs)|0;
      if (cx < 0) cx = 0; if (cx >= gw) cx = gw-1;
      if (cy < 0) cy = 0; if (cy >= gw) cy = gw-1;
      b[cy*gw+cx].push(i);
    }
    for (let cy = 0; cy < gw; cy++) for (let cx = 0; cx < gw; cx++){
      const A = b[cy*gw+cx];
      if (!A.length) continue;
      for (let oy = 0; oy <= 1; oy++) for (let ox = -1; ox <= 1; ox++){
        if (oy === 0 && ox < 0) continue;
        const nx2 = cx+ox, ny2 = cy+oy;
        if (nx2 < 0 || nx2 >= gw || ny2 >= gw) continue;
        const B = b[ny2*gw+nx2];
        for (let ii = 0; ii < A.length; ii++){
          const i = A[ii];
          for (let jj = (B === A ? ii+1 : 0); jj < B.length; jj++){
            this.collide(i, B[jj]);
          }
        }
      }
    }
  }
  collide(i, j){
    const dx = this.x[j]-this.x[i], dy = this.y[j]-this.y[i];
    const d2 = dx*dx + dy*dy, md = 2*this.r;
    if (d2 >= md*md || d2 === 0) return;
    const d = Math.sqrt(d2), nx = dx/d, ny = dy/d, ov = (md-d)*0.5;
    this.x[i] -= nx*ov; this.y[i] -= ny*ov;
    this.x[j] += nx*ov; this.y[j] += ny*ov;
    const rvx = this.vx[j]-this.vx[i], rvy = this.vy[j]-this.vy[i];
    const p = rvx*nx + rvy*ny;
    if (p > 0) return;
    this.vx[i] += p*nx; this.vy[i] += p*ny;
    this.vx[j] -= p*nx; this.vy[j] -= p*ny;
  }
  finished(){ return this.aliveCount <= 1 || this.t > 90; }
  winner(){ for (let i = 0; i < this.n; i++) if (this.alive[i]) return i; return 0; }
}
function runHeadless(seed, n){
  const R = new Round(seed, n);
  while (!R.finished()) R.step();
  return R.winner();
}
function oddsFor(n, edgePct){ return Math.floor(n * (1 - edgePct/100) * 100) / 100; }
if (typeof module !== 'undefined' && module.exports){
  module.exports = { SIM_VERSION, Round, runHeadless, oddsFor, mulberry32, ISO, flagEmoji };
}
