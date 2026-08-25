"""Precompute winning indices for a range of simulation numbers.

The physics is the only slow part of book generation: roughly one second per
round at 195 flags on a modest core. The seven bet modes all read the same
simulation numbers, so the same rounds get solved seven times unless the
result is cached — and the in-process cache in gamestate.py disappears the
moment threads > 1, because each thread is a separate process.

This script solves each round once, in parallel, and writes the answers to a
file. gamestate.py then reads that file instead of simulating, which makes
run.py finish in minutes no matter how many modes or how many sims.

    python precompute_winners.py 100000

Run it with the same simulation count you intend to put in run.py. The output
lands in winners_195.json next to this file.

The keys are SEEDS, not simulation numbers. The SDK hands run_spin an explicit
simulation_seed — run_sims.py builds them as plain 0, 1, 2, ... — so those are
the values the physics actually runs on. Keying by seed means the file works
whichever way the seed arrives.

Resumable: stop it with Ctrl+C and run it again with the same argument. It
picks up where it left off, so a long run can be spread over several sittings
or moved to a faster machine part-way through.

Correctness note: the winner for a given seed depends on sim_core.py. Change
that file — the physics, the constants, SIM_VERSION — and this cache is stale
and must be deleted. The version is stored in the file and checked on load.
"""

import json
import os
import sys
import time
from multiprocessing import Pool, cpu_count

import sim_core

NUM_FLAGS = 195
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"winners_{NUM_FLAGS}.json")
CHUNK = 500          # results are flushed this often, so little work is lost


def solve(seed):
    return seed, sim_core.run_headless(seed, NUM_FLAGS)


def load():
    if not os.path.exists(OUT):
        return {}
    with open(OUT) as f:
        data = json.load(f)
    if data.get("simVersion") != sim_core.SIM_VERSION:
        print(f"  cache was built with sim {data.get('simVersion')}, this is "
              f"{sim_core.SIM_VERSION} — starting over")
        return {}
    if data.get("numFlags") != NUM_FLAGS:
        return {}
    return {int(k): v for k, v in data["winners"].items()}


def save(winners):
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump({
            "simVersion": sim_core.SIM_VERSION,
            "numFlags": NUM_FLAGS,
            "winners": {str(k): v for k, v in sorted(winners.items())},
        }, f)
    os.replace(tmp, OUT)      # atomic, so a crash mid-write cannot corrupt it


def main():
    total = int(float(sys.argv[1])) if len(sys.argv) > 1 else 100000
    procs = int(sys.argv[2]) if len(sys.argv) > 2 else cpu_count()

    winners = load()
    # The SDK numbers its seeds 0..n-1, so that is exactly the range to cover.
    todo = [s for s in range(total) if s not in winners]

    print(f"sim {sim_core.SIM_VERSION}, {NUM_FLAGS} flags, {procs} processes")
    print(f"already done: {len(winners)}   to do: {len(todo)}")
    if not todo:
        print("nothing to do")
        return

    t0 = time.time()
    done = 0
    try:
        with Pool(procs) as pool:
            for sim, w in pool.imap_unordered(solve, todo, chunksize=8):
                winners[sim] = w
                done += 1
                if done % CHUNK == 0:
                    save(winners)
                    rate = done / (time.time() - t0)
                    left = (len(todo) - done) / rate / 3600
                    print(f"  {done}/{len(todo)}   {rate:.1f} rounds/s   "
                          f"{left:.1f} h remaining", flush=True)
    except KeyboardInterrupt:
        print("\ninterrupted — progress is saved, run again to resume")
    finally:
        save(winners)

    el = time.time() - t0
    print(f"\n{len(winners)} winners in {OUT}")
    print(f"this session: {done} rounds in {el/60:.1f} min")


if __name__ == "__main__":
    main()