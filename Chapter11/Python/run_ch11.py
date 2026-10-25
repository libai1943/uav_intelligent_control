#!/usr/bin/env python3
"""Chapter 11 teaching examples: LP, scheduling MILP, and exhaustive verification.

Run from any directory: python /path/to/code/run_ch11.py
This script writes reproducible numerical results to ../results/python/.
It uses no random search. All times in the scheduling example are in minutes.
"""
from __future__ import annotations

import itertools
import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

TOL = 1e-5
OUT = Path(__file__).resolve().parent.parent / "results" / "python"


def single_aircraft_lp() -> dict:
    """Scheduled flight: cargo q_A,q_B (kg), fuel F=.4+.1(q_A+q_B) L.

    Unit gross margins before fuel are 6 and 5 yuan/kg, fuel price 10 yuan/L.
    Net return = 6*q_A+5*q_B-10*F = 5*q_A+4*q_B-4.
    Payload bounds already allow for the specified tank and reserve policy.
    """
    A = np.array([[1, 1], [2, 1]], dtype=float)
    b = np.array([10, 14], dtype=float)
    linear_return = np.array([5, 4], dtype=float)
    fixed_fuel_cost = 4.0
    result = linprog(-linear_return, A_ub=A, b_ub=b, bounds=[(0, None)] * 2,
                     method="highs")
    if not result.success:
        raise RuntimeError(result.message)
    # Independent vertex enumeration, including nonnegativity boundaries.
    all_A = np.vstack((A, -np.eye(2)))
    all_b = np.r_[b, 0.0, 0.0]
    vertices = []
    for pair in itertools.combinations(range(4), 2):
        matrix = all_A[list(pair)]
        if abs(np.linalg.det(matrix)) <= TOL:
            continue
        point = np.linalg.solve(matrix, all_b[list(pair)])
        if np.all(all_A @ point <= all_b + TOL):
            if not any(np.linalg.norm(point - p) < TOL for p in vertices):
                vertices.append(point)
    vertices.sort(key=lambda p: (float(p[0]), float(p[1])))
    best_vertex_value = max(float(linear_return @ p - fixed_fuel_cost) for p in vertices)
    assert abs(best_vertex_value - (-result.fun - fixed_fuel_cost)) < TOL
    assert np.allclose(result.x, [4, 6], atol=TOL)
    # Certificate: 3(q_A+q_B)+(2q_A+q_B)-4 <= 3*10+14-4 = 40.
    assert np.allclose(3 * A[0] + A[1], linear_return)
    assert abs(-result.fun - fixed_fuel_cost - 40) < TOL
    sensitivities = {}
    for name, changed_b in (("warehouse_15", [10, 15]), ("payload_11", [11, 14])):
        changed = linprog(-linear_return, A_ub=A, b_ub=changed_b,
                          bounds=[(0, None)] * 2, method="highs")
        assert changed.success
        sensitivities[name] = {"variables_kg": changed.x.tolist(),
                              "net_return_yuan": float(-changed.fun - fixed_fuel_cost),
                              "fuel_L": float(.4 + .1 * changed.x.sum()),
                              "resource_bounds": changed_b}
    return {
        "variables_kg": result.x.tolist(),
        "net_return_yuan": float(-result.fun - fixed_fuel_cost),
        "fuel_L": float(.4 + .1 * result.x.sum()),
        "resource_use": (A @ result.x).tolist(),
        "resource_bounds": b.tolist(),
        "resource_slack": (b - A @ result.x).tolist(),
        "vertices": [{"q_A": float(p[0]), "q_B": float(p[1]),
                      "net_return_yuan": float(linear_return @ p - fixed_fuel_cost)}
                     for p in vertices],
        "upper_bound_certificate": "5*q_A+4*q_B-4=3*(q_A+q_B)+(2*q_A+q_B)-4<=40",
        "verified_by_independent_vertex_enumeration": True,
        "sensitivities": sensitivities,
    }


def two_aircraft_transport_lp() -> dict:
    """Divisible deliveries to two receivers; order q11,q12,q21,q22.

    Each aircraft carries at most 6 kg in this allocation model. Receiver
    demands are 6 and 4 kg. Timing and routes are outside this small LP.
    """
    costs = np.array([2, 5, 4, 1], dtype=float)
    capacity_A = np.array([[1, 1, 0, 0], [0, 0, 1, 1]], dtype=float)
    capacity_b = np.array([6, 6], dtype=float)
    demand_A = np.array([[1, 0, 1, 0], [0, 1, 0, 1]], dtype=float)
    demand_b = np.array([6, 4], dtype=float)
    solved = linprog(costs, A_ub=capacity_A, b_ub=capacity_b,
                     A_eq=demand_A, b_eq=demand_b,
                     bounds=[(0, None)] * 4, method="highs")
    if not solved.success:
        raise RuntimeError(solved.message)
    expected = np.array([6, 0, 0, 4], dtype=float)
    assert np.max(np.abs(solved.x - expected)) <= TOL
    violation = max(0.0, float(np.max(capacity_A @ solved.x - capacity_b)),
                    float(np.max(np.abs(demand_A @ solved.x - demand_b))),
                    float(np.max(-solved.x)))
    assert violation <= TOL
    # Demand substitution gives cost=16+2*q21+4*q12 >=16.
    certificate_dual = np.array([2, 1], dtype=float)
    reduced_cost = costs - demand_A.T @ certificate_dual
    assert np.all(reduced_cost >= 0)
    lower_bound = float(demand_b @ certificate_dual)
    assert abs(solved.fun - lower_bound) <= TOL
    return {"variable_order": ["q11", "q12", "q21", "q22"],
            "variables_kg": solved.x.tolist(), "unit_cost": costs.tolist(),
            "minimum_cost": float(solved.fun),
            "aircraft_load_kg": (capacity_A @ solved.x).tolist(),
            "receiver_deliveries_kg": (demand_A @ solved.x).tolist(),
            "maximum_linear_constraint_violation": violation,
            "lower_bound_certificate": "cost=16+2*q21+4*q12>=16",
            "exact_lower_bound": lower_bound,
            "certificate_reduced_costs": reduced_cost.tolist(),
            "checked_absolute_gap": float(solved.fun - lower_bound),
            "validation_tolerance": TOL}


def base_data() -> dict:
    return {
        "p": np.array([[4, 6, 5, 7], [7, 4, 6, 5]], dtype=float),
        "r": np.array([0, 0, 2, 1], dtype=float),
        "d": np.array([12, 12, 14, 13], dtype=float),
        "available": np.array([1, 1], dtype=int),
    }


def build_milp(data: dict, constant_M: float | None = None) -> dict:
    """Build exactly the conditional nonoverlap formulation in the chapter.

    x[i,j]=1: aircraft i executes task j; y[j,k]=1: j precedes k
    when the two tasks use the same aircraft. s=start; c=completion;
    C=maximum completion time. The global y[j,k] is irrelevant if j,k
    use different aircraft; it has no claim about their chronological order.
    """
    p, r, d, available = (data[k] for k in ("p", "r", "d", "available"))
    m, n = p.shape
    pairs = list(itertools.combinations(range(n), 2))
    nx, ny = m * n, len(pairs)
    ix = np.arange(nx).reshape(m, n)
    iy = {pair: nx + q for q, pair in enumerate(pairs)}
    is_ = np.arange(nx + ny, nx + ny + n)
    ic = np.arange(nx + ny + n, nx + ny + 2 * n)
    iC = nx + ny + 2 * n
    nv = iC + 1
    lower = np.zeros(nv)
    upper = np.full(nv, np.inf)
    upper[:nx + ny] = 1.0
    for i in range(m):
        upper[ix[i]] = available[i]
    lower[is_] = r
    upper[is_] = d
    upper[ic] = d
    upper[iC] = max(d)
    integrality = np.zeros(nv, dtype=int)
    integrality[:nx + ny] = 1
    objective = np.zeros(nv)
    objective[iC] = 1.0
    rows, lows, ups = [], [], []

    def row(entries, lo=-np.inf, up=np.inf):
        a = np.zeros(nv)
        for index, coefficient in entries:
            a[index] += coefficient
        rows.append(a)
        lows.append(lo)
        ups.append(up)

    for j in range(n):
        row([(ix[i, j], 1.0) for i in range(m)], 1.0, 1.0)
        row([(ic[j], 1.0), (is_[j], -1.0)] +
            [(ix[i, j], -p[i, j]) for i in range(m)], 0.0, 0.0)
        row([(ic[j], 1.0), (iC, -1.0)], up=0.0)
    M = np.maximum(0.0, d[:, None] - r[None, :])
    if constant_M is not None:
        M[:] = constant_M
    for j, k in pairs:
        for i in range(m):
            # c_j <= s_k + M_jk*(1-y_jk) + M_jk*(2-x_ij-x_ik)
            row([(ic[j], 1.0), (is_[k], -1.0), (iy[j, k], M[j, k]),
                 (ix[i, j], M[j, k]), (ix[i, k], M[j, k])],
                up=3.0 * M[j, k])
            # c_k <= s_j + M_kj*y_jk + M_kj*(2-x_ij-x_ik)
            row([(ic[k], 1.0), (is_[j], -1.0), (iy[j, k], -M[k, j]),
                 (ix[i, j], M[k, j]), (ix[i, k], M[k, j])],
                up=2.0 * M[k, j])
    return {"objective": objective, "integrality": integrality,
            "bounds": Bounds(lower, upper),
            "constraints": LinearConstraint(np.array(rows), lows, ups),
            "ix": ix, "iy": iy, "is": is_, "ic": ic, "iC": iC,
            "M": M}


def validate_schedule(data: dict, assignment: np.ndarray,
                      starts: np.ndarray, completions: np.ndarray) -> dict:
    """Check physical/task constraints directly, without using the MILP rows."""
    p, r, d, available = (data[k] for k in ("p", "r", "d", "available"))
    n = len(r)
    failures = []
    for j in range(n):
        i = int(assignment[j])
        if available[i] != 1:
            failures.append(f"task {j + 1}: unavailable aircraft")
        if starts[j] < r[j] - TOL:
            failures.append(f"task {j + 1}: release time")
        if completions[j] > d[j] + TOL:
            failures.append(f"task {j + 1}: deadline")
        if abs(completions[j] - starts[j] - p[i, j]) > TOL:
            failures.append(f"task {j + 1}: duration")
    for j, k in itertools.combinations(range(n), 2):
        if assignment[j] == assignment[k]:
            if not (completions[j] <= starts[k] + TOL or
                    completions[k] <= starts[j] + TOL):
                failures.append(f"tasks {j + 1},{k + 1}: aircraft overlap")
    if failures:
        raise AssertionError(failures)
    return {"all_tasks_assigned_once": True, "release_deadline_duration_ok": True,
            "same_aircraft_nonoverlap_ok": True}


def solve_milp(data: dict, constant_M: float | None = None,
               relax_integrality: bool = False) -> dict:
    model = build_milp(data, constant_M)
    integer_mask = (np.zeros_like(model["integrality"]) if relax_integrality
                    else model["integrality"])
    result = milp(model["objective"], integrality=integer_mask,
                  bounds=model["bounds"], constraints=model["constraints"],
                  options={"mip_rel_gap": 0.0})
    answer = {"status": int(result.status), "message": str(result.message),
              "success": bool(result.success)}
    if not result.success:
        return answer
    x = result.x[model["ix"]]
    answer.update({"objective": float(result.fun), "x": x.tolist(),
                   "starts": result.x[model["is"]].tolist(),
                   "completions": result.x[model["ic"]].tolist(),
                   "directional_M": model["M"].tolist()})
    if relax_integrality:
        return answer
    assignment = np.argmax(x, axis=0)
    assert np.max(np.abs(x - np.round(x))) <= TOL
    answer["assignment_aircraft_1_based"] = (assignment + 1).tolist()
    answer["y_for_unordered_pairs"] = {
        f"{j+1},{k+1}": int(round(result.x[index]))
        for (j, k), index in model["iy"].items()}
    answer["schedule_makespan"] = float(max(result.x[model["ic"]]))
    residual = model["constraints"].A @ result.x
    violation = max(0.0, float(np.max(residual - model["constraints"].ub)),
                    float(np.max(model["constraints"].lb - residual)),
                    float(np.max(model["bounds"].lb - result.x)),
                    float(np.max(result.x - model["bounds"].ub)))
    answer["maximum_linear_constraint_violation"] = violation
    assert violation <= TOL
    answer["validation_tolerance"] = TOL
    answer["mip_gap"] = float(result.mip_gap)
    answer["mip_dual_bound"] = float(result.mip_dual_bound)
    answer["checks"] = validate_schedule(data, assignment,
                                         result.x[model["is"]],
                                         result.x[model["ic"]])
    return answer


def exhaustive_schedules(data: dict) -> dict:
    """Independent enumeration of every assignment and per-aircraft ordering.

    For a fixed ordering, starting each task at max(release, prior completion)
    gives componentwise earliest completion times. If that schedule violates
    a deadline, adding idle time cannot repair it. Thus this enumeration is
    exact for the present model (no shared pad or sequence-dependent setup).
    """
    p, r, d, available = (data[k] for k in ("p", "r", "d", "available"))
    m, n = p.shape
    best = np.inf
    tested = feasible = 0
    optimizers = []
    feasible_schedules = []
    for ass_tuple in itertools.product(range(m), repeat=n):
        assignment = np.array(ass_tuple)
        if any(not available[i] for i in assignment):
            continue
        group_orders = [list(itertools.permutations(np.where(assignment == i)[0]))
                        for i in range(m)]
        for orders in itertools.product(*group_orders):
            tested += 1
            starts, completions = np.zeros(n), np.zeros(n)
            for i, order in enumerate(orders):
                clock = 0.0
                for j in order:
                    starts[j] = max(clock, r[j])
                    completions[j] = starts[j] + p[i, j]
                    clock = completions[j]
            if np.any(completions > d + TOL):
                continue
            feasible += 1
            value = max(completions)
            feasible_schedules.append({
                "assignment_aircraft_1_based": (assignment + 1).tolist(),
                "orders_tasks_1_based": [[int(j + 1) for j in o] for o in orders],
                "starts": starts.tolist(), "completions": completions.tolist(),
                "makespan": float(value)})
            if value < best - TOL:
                best, optimizers = value, []
            if abs(value - best) <= TOL:
                validate_schedule(data, assignment, starts, completions)
                optimizers.append({
                    "assignment_aircraft_1_based": (assignment + 1).tolist(),
                    "orders_tasks_1_based": [[int(j + 1) for j in o] for o in orders],
                    "starts": starts.tolist(), "completions": completions.tolist()})
    return {"enumerated_assignment_order_combinations": tested,
            "feasible_assignment_order_combinations": feasible,
            "optimal_objective": None if np.isinf(best) else float(best),
            "optimal_earliest_schedules": optimizers,
            "all_feasible_earliest_schedules": feasible_schedules,
            "feasible_makespan_histogram": {
                str(v): sum(abs(item["makespan"] - v) < TOL for item in feasible_schedules)
                for v in sorted({item["makespan"] for item in feasible_schedules})}}


def audit_decoder_coverage(data: dict, enumeration: dict) -> dict:
    """Verify that a task permutation plus aircraft assignment covers the optimum.

    Every pair of per-aircraft ordered lists can be interleaved into a single
    task permutation without changing the within-aircraft order. The simple
    decoder below visits that permutation and appends each task to its assigned
    aircraft at the earliest feasible time. Release times and nonoverlap are
    automatic; deadlines are checked and are not claimed to be automatic.
    """
    p, r, d = (data[k] for k in ("p", "r", "d"))
    m, n = p.shape
    best = np.inf
    feasible = total = 0
    for assignment in itertools.product(range(m), repeat=n):
        if any(not data["available"][i] for i in assignment):
            continue
        for permutation in itertools.permutations(range(n)):
            total += 1
            clock = np.zeros(m)
            starts = np.zeros(n)
            completions = np.zeros(n)
            for j in permutation:
                i = assignment[j]
                starts[j] = max(r[j], clock[i])
                completions[j] = starts[j] + p[i, j]
                clock[i] = completions[j]
            if np.any(completions > d + TOL):
                continue
            feasible += 1
            best = min(best, max(completions))
    expected = enumeration["optimal_objective"]
    observed = None if np.isinf(best) else float(best)
    assert observed == expected
    return {"encoding": "task permutation plus per-task aircraft assignment",
            "enumerated_encodings": total,
            "feasible_encodings": feasible,
            "best_objective": observed,
            "matches_exact_schedule_enumeration": True,
            "automatic_constraints": ["unique task assignment", "release time",
                                      "same-aircraft nonoverlap"],
            "checked_not_automatic": ["deadline", "aircraft availability"]}


def decode_split(data: dict, permutation: tuple[int, ...], cut: int) -> dict:
    """Permutation + one cut => two ordered lists, then earliest start times.

    A permutation uses each task exactly once. The cut can be 0 or n, so an
    aircraft may receive an empty list. No explicit time or order variables
    are present in the encoding. Deadlines still need a feasibility check.
    """
    n = len(data["r"])
    if sorted(permutation) != list(range(n)) or not 0 <= cut <= n:
        raise ValueError("Expected a task permutation and a cut in 0,...,n")
    orders = (permutation[:cut], permutation[cut:])
    assignment = np.empty(n, dtype=int)
    starts, completions = np.zeros(n), np.zeros(n)
    for i, order in enumerate(orders):
        clock = 0.0
        for j in order:
            assignment[j] = i
            starts[j] = max(clock, data["r"][j])
            completions[j] = starts[j] + data["p"][i, j]
            clock = completions[j]
    feasible = (np.all(data["available"][assignment] == 1) and
                np.all(completions <= data["d"] + TOL))
    return {"assignment": assignment, "orders": orders, "starts": starts,
            "completions": completions, "feasible": bool(feasible),
            "makespan": float(max(completions))}


def audit_split_decoder(data: dict, enumeration: dict) -> dict:
    n = len(data["r"])
    total = feasible = 0
    best = np.inf
    unique_orders = set()
    for permutation in itertools.permutations(range(n)):
        for cut in range(n + 1):
            decoded = decode_split(data, permutation, cut)
            total += 1
            unique_orders.add(decoded["orders"])
            if decoded["feasible"]:
                feasible += 1
                best = min(best, decoded["makespan"])
                validate_schedule(data, decoded["assignment"], decoded["starts"],
                                  decoded["completions"])
    assert len(unique_orders) == total
    observed = None if np.isinf(best) else float(best)
    assert observed == enumeration["optimal_objective"]
    assert feasible == enumeration["feasible_assignment_order_combinations"]
    return {"encoding": "task permutation plus cut position (two aircraft)",
            "enumerated_encodings": total, "distinct_pairs_of_ordered_lists": len(unique_orders),
            "feasible_encodings": feasible, "best_objective": observed,
            "one_to_one_with_pairs_of_local_ordered_lists": True,
            "matches_exact_schedule_enumeration": True}


def write_schedule_csv(name: str, example: dict):
    import csv
    candidate = example["enumeration"]["optimal_earliest_schedules"]
    if not candidate:
        return
    selected = candidate[0]
    with (OUT / f"{name}_schedule.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["task", "aircraft", "start_min", "complete_min"])
        for j, i in enumerate(selected["assignment_aircraft_1_based"]):
            writer.writerow([j + 1, i, selected["starts"][j], selected["completions"][j]])
    with (OUT / f"{name}_all_feasible_schedules.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["aircraft_1_order", "aircraft_2_order", "makespan_min",
                         "starts_by_task", "completions_by_task"])
        for item in example["enumeration"]["all_feasible_earliest_schedules"]:
            writer.writerow([" ".join(map(str, item["orders_tasks_1_based"][0])),
                             " ".join(map(str, item["orders_tasks_1_based"][1])),
                             item["makespan"], " ".join(map(str, item["starts"])),
                             " ".join(map(str, item["completions"]))])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_results = {"environment": {"python": sys.version.split()[0],
                                   "numpy": np.__version__, "scipy": scipy.__version__,
                                   "platform": platform.platform(),
                                   "solver_interface": "scipy.optimize.linprog/milp (HiGHS)"},
                   "single_aircraft_lp": single_aircraft_lp(),
                   "two_aircraft_transport_lp": two_aircraft_transport_lp(),
                   "scheduling": {}}
    for name in ("baseline", "deadline_3_is_7", "aircraft_2_unavailable"):
        data = base_data()
        if name == "deadline_3_is_7":
            data["d"][2] = 7
        elif name == "aircraft_2_unavailable":
            data["available"][1] = 0
        solved = solve_milp(data)
        enumerated = exhaustive_schedules(data)
        if enumerated["optimal_objective"] is None:
            assert solved["status"] == 2
        else:
            assert solved["success"]
            assert abs(solved["objective"] - enumerated["optimal_objective"]) < TOL
        case = {"data": {k: v.tolist() for k, v in data.items()},
                "milp": solved, "enumeration": enumerated,
                "decoder_exhaustive_check": audit_decoder_coverage(data, enumerated),
                "split_decoder_exhaustive_check": audit_split_decoder(data, enumerated)}
        all_results["scheduling"][name] = case
        write_schedule_csv(name, case)
        print(f"{name}: MILP={solved.get('objective', solved['message'])}; "
              f"enumeration={enumerated['optimal_objective']}")
    data = base_data()
    wrong_M = solve_milp(data, constant_M=8.0)
    assert wrong_M["status"] == 2
    all_results["wrong_constant_M_8"] = wrong_M
    all_results["lp_relaxation_baseline"] = solve_milp(data, relax_integrality=True)
    all_results["lp_relaxation_M_1000"] = solve_milp(data, constant_M=1000.0,
                                                   relax_integrality=True)
    all_results["physical_workload_lower_bound_baseline"] = float(
        np.min(data["p"], axis=0).sum() / data["p"].shape[0])
    (OUT / "results.json").write_text(json.dumps(all_results, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    print("single_aircraft_lp: q_A=4 kg, q_B=6 kg, net return=40 yuan, fuel=1.4 L")
    print("two_aircraft_transport_lp: [q11,q12,q21,q22]=[6,0,0,4] kg; minimum cost=16")
    print("wrong M=8: infeasible model, although the physical scheduling problem is feasible")
    print(f"All exact independent checks passed. Results: {OUT / 'results.json'}")


if __name__ == "__main__":
    main()
