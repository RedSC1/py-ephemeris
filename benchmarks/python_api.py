"""Benchmark installed Taiyin Python APIs without calling private native bindings."""

from __future__ import annotations

import argparse
import gc
import math
import platform
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import taiyin


def measure_epochs(operation, epochs, rounds: int) -> tuple[float, float, float]:
    for epoch in epochs[: min(32, len(epochs))]:
        operation(epoch)
    samples = []
    gc.collect()
    gc.disable()
    try:
        for _ in range(rounds):
            started = time.perf_counter_ns()
            for epoch in epochs:
                operation(epoch)
            samples.append((time.perf_counter_ns() - started) / len(epochs) / 1000.0)
    finally:
        gc.enable()
    return statistics.median(samples), min(samples), max(samples)


def measure_fixed(operation, iterations: int, rounds: int) -> tuple[float, float, float]:
    for _ in range(3):
        operation()
    samples = []
    gc.collect()
    gc.disable()
    try:
        for _ in range(rounds):
            started = time.perf_counter_ns()
            for _ in range(iterations):
                operation()
            samples.append((time.perf_counter_ns() - started) / iterations / 1000.0)
    finally:
        gc.enable()
    return statistics.median(samples), min(samples), max(samples)


def per_item(result: tuple[float, float, float], count: int) -> tuple[float, float, float]:
    return tuple(value / count for value in result)


def measure_threaded(
    operations, epochs, rounds: int
) -> tuple[tuple[float, float, float], float]:
    """Measure fixed work using one operation callable per worker."""
    workers = len(operations)
    if workers == 0:
        raise ValueError("at least one worker operation is required")

    chunks = [epochs[index::workers] for index in range(workers)]
    for operation, chunk in zip(operations, chunks):
        for epoch in chunk[: min(32, len(chunk))]:
            operation(epoch)

    def run_chunk(operation, chunk):
        checksum = 0.0
        for epoch in chunk:
            values, result_flags = operation(epoch)
            checksum += float(result_flags)
            checksum += sum(float(value) for value in values)
        return checksum

    samples = []
    checksum = 0.0
    gc.collect()
    gc.disable()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for _ in range(rounds):
                started = time.perf_counter_ns()
                futures = [
                    pool.submit(run_chunk, operation, chunk)
                    for operation, chunk in zip(operations, chunks)
                ]
                checksums = [future.result() for future in futures]
                samples.append(
                    (time.perf_counter_ns() - started) / len(epochs) / 1000.0
                )
                checksum += sum(checksums)
    finally:
        gc.enable()
    return (statistics.median(samples), min(samples), max(samples)), checksum


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--position-iterations", type=int, default=8000)
    parser.add_argument("--batch-iterations", type=int, default=1000)
    parser.add_argument("--where-iterations", type=int, default=3000)
    parser.add_argument("--how-iterations", type=int, default=2000)
    parser.add_argument("--global-iterations", type=int, default=80)
    parser.add_argument("--local-iterations", type=int, default=50)
    parser.add_argument("--threaded-iterations", type=int, default=8000)
    parser.add_argument("--threaded-rounds", type=int, default=7)
    args = parser.parse_args()

    data_root = Path(taiyin.__file__).resolve().parent / "data"
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()
    context.configuration.set_geocentric_observer(
        observer_id=taiyin.Body.earth.id,
        center_id=taiyin.Body.earth.id,
    )
    context.configuration.set_observer_location(
        taiyin.ObserverLocation(-96.7970, 32.7767, 131.0)
    )
    context.configuration.set_standard_atmosphere()

    epochs = [
        taiyin.JulianDate.from_double(2460310.5 + index * 0.0125)
        for index in range(args.position_iterations)
    ]
    batch_epochs = epochs[: min(args.batch_iterations, len(epochs))]
    solar_start = taiyin.JulianDate.from_double(2460409.0)
    solar_maximum = taiyin.JulianDate.from_double(2460409.262039739)
    major_bodies = (
        taiyin.Body.mercury,
        taiyin.Body.venus,
        taiyin.Body.mars,
        taiyin.Body.jupiter,
        taiyin.Body.saturn,
        taiyin.Body.uranus,
        taiyin.Body.neptune,
        taiyin.Body.pluto,
    )

    rows = [
        (
            "Mars position.at_ut1",
            measure_epochs(
                lambda epoch: context.position.at_ut1(taiyin.Body.mars, epoch),
                epochs,
                args.rounds,
            ),
        ),
        (
            "Mars position.at_ut1 + speed",
            measure_epochs(
                lambda epoch: context.position.at_ut1(
                    taiyin.Body.mars, epoch, (taiyin.PositionFlag.speed,)
                ),
                epochs,
                args.rounds,
            ),
        ),
        (
            "Mars state_at_ut1",
            measure_epochs(
                lambda epoch: context.position.state_at_ut1(taiyin.Body.mars, epoch),
                epochs,
                args.rounds,
            ),
        ),
        (
            "Mars barycenter position.at_ut1",
            measure_epochs(
                lambda epoch: context.position.at_ut1(
                    taiyin.Body.mars_barycenter, epoch
                ),
                epochs,
                args.rounds,
            ),
        ),
        (
            "8-body scalar loop (per body)",
            per_item(
                measure_epochs(
                    lambda epoch: tuple(
                        context.position.at_ut1(body, epoch)
                        for body in major_bodies
                    ),
                    batch_epochs,
                    args.rounds,
                ),
                len(major_bodies),
            ),
        ),
        (
            "8-body batch_at_ut1 (per body)",
            per_item(
                measure_epochs(
                    lambda epoch: context.position.batch_at_ut1(
                        major_bodies, epoch
                    ),
                    batch_epochs,
                    args.rounds,
                ),
                len(major_bodies),
            ),
        ),
        (
            "Solar eclipse fixed global (where)",
            measure_fixed(
                lambda: context.eclipses.solar_eclipse_where_at_ut1(solar_maximum),
                args.where_iterations,
                args.rounds,
            ),
        ),
        (
            "Solar eclipse fixed local (how)",
            measure_fixed(
                lambda: context.eclipses.local_solar_circumstances_at_ut1(
                    solar_maximum
                ),
                args.how_iterations,
                args.rounds,
            ),
        ),
        (
            "Solar eclipse next global",
            measure_fixed(
                lambda: context.eclipses.next_solar_at_ut1(solar_start),
                args.global_iterations,
                args.rounds,
            ),
        ),
        (
            "Solar eclipse next local",
            measure_fixed(
                lambda: context.eclipses.next_local_solar_at_ut1(solar_start),
                args.local_iterations,
                args.rounds,
            ),
        ),
    ]

    threaded_epochs = [
        taiyin.JulianDate.from_double(2460310.5 + index * 0.0125)
        for index in range(args.threaded_iterations)
    ]
    threaded_operation = lambda epoch: context.position.at_ut1(
        taiyin.Body.mars, epoch, (taiyin.PositionFlag.speed,)
    )
    shared_threaded_rows = []
    shared_threaded_checksums = []
    independent_threaded_rows = []
    independent_threaded_checksums = []
    for workers in (1, 2, 4, 6, 8):
        result, checksum = measure_threaded(
            [threaded_operation] * workers,
            threaded_epochs,
            args.threaded_rounds,
        )
        shared_threaded_rows.append((workers, result))
        shared_threaded_checksums.append(checksum)

        worker_contexts = [ephemeris.clone_context(context) for _ in range(workers)]
        worker_operations = [
            lambda epoch, worker_context=worker_context: worker_context.position.at_ut1(
                taiyin.Body.mars, epoch, (taiyin.PositionFlag.speed,)
            )
            for worker_context in worker_contexts
        ]
        try:
            result, checksum = measure_threaded(
                worker_operations, threaded_epochs, args.threaded_rounds
            )
        finally:
            for worker_context in worker_contexts:
                worker_context.close()
        independent_threaded_rows.append((workers, result))
        independent_threaded_checksums.append(checksum)
    shared_baseline = shared_threaded_rows[0][1][0]
    independent_baseline = independent_threaded_rows[0][1][0]

    print(f"Python {platform.python_version()} on {platform.machine()}")
    print(f"Taiyin {getattr(taiyin, '__version__', 'preview')}")
    print(f"Packaged data: {data_root}")
    print(f"Warm measurements; median/min/max of {args.rounds} rounds; microseconds/call")
    for label, result in rows:
        print(f"{label:<43} {result[0]:9.2f} / {result[1]:9.2f} / {result[2]:9.2f}")
    print(
        "Shared-context threaded position.at_ut1; fixed work of "
        f"{args.threaded_iterations} calls, {args.threaded_rounds} rounds"
    )
    print("workers   median us/call   min us/call   max us/call   speedup")
    for (workers, result), checksum in zip(
        shared_threaded_rows, shared_threaded_checksums
    ):
        print(
            f"{workers:>7} {result[0]:>16.2f} {result[1]:>13.2f} "
            f"{result[2]:>13.2f} {shared_baseline / result[0]:>9.2f}"
        )
    print(
        "Independent-context threaded position.at_ut1; one cloned context "
        "per worker"
    )
    print("workers   median us/call   min us/call   max us/call   speedup")
    for (workers, result), checksum in zip(
        independent_threaded_rows, independent_threaded_checksums
    ):
        print(
            f"{workers:>7} {result[0]:>16.2f} {result[1]:>13.2f} "
            f"{result[2]:>13.2f} {independent_baseline / result[0]:>9.2f}"
        )
    reference_checksum = shared_threaded_checksums[0]
    if not all(
        math.isclose(checksum, reference_checksum, rel_tol=1e-12, abs_tol=1e-9)
        for checksum in shared_threaded_checksums + independent_threaded_checksums
    ):
        raise RuntimeError("threaded benchmark result checksum changed")

    context.close()


if __name__ == "__main__":
    main()
