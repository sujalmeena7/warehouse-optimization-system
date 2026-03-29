#!/usr/bin/env python
"""
Test suite for optimization algorithms
Run with: python test_algorithms.py
"""

import sys
sys.path.insert(0, '.')

from layout_api import (
    optimize_layout_astar,
    optimize_layout_genetic,
    optimize_layout_reinforcement,
    optimize_greedy,
    LayoutConfig,
    calculate_metrics,
)

# Sample containers for testing
sample_containers = [
    {"container_id": "HIGH-001", "size": "Small", "weight": 20.0, "access_frequency": "High", "arrival_time": "2026-03-28T10:00:00"},
    {"container_id": "HIGH-002", "size": "Medium", "weight": 50.0, "access_frequency": "High", "arrival_time": "2026-03-28T11:00:00"},
    {"container_id": "MED-001", "size": "Medium", "weight": 55.0, "access_frequency": "Medium", "arrival_time": "2026-03-28T12:00:00"},
    {"container_id": "LOW-001", "size": "Large", "weight": 90.0, "access_frequency": "Low", "arrival_time": "2026-03-28T08:00:00"},
    {"container_id": "LOW-002", "size": "Large", "weight": 85.0, "access_frequency": "Low", "arrival_time": "2026-03-28T07:00:00"},
]

config = LayoutConfig(rows=8, cols=8, max_stack_height=4, strategy="greedy_access")

def test_algorithm(name, algorithm_func):
    """Test an optimization algorithm"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")

    try:
        grid, unplaced = algorithm_func(sample_containers, config)
        metrics = calculate_metrics(grid, config)

        total_placed = len(sample_containers) - len(unplaced)
        print(f"[OK] Algorithm executed successfully")
        print(f"  - Containers placed: {total_placed}/{len(sample_containers)}")
        print(f"  - Containers unplaced: {len(unplaced)}")
        if unplaced:
            print(f"    Unplaced: {', '.join(unplaced)}")

        print(f"\nLayout Metrics:")
        print(f"  - Space utilization: {metrics.space_utilization}%")
        print(f"  - Avg retrieval time: {metrics.average_retrieval_time:.2f} min")
        print(f"  - Avg container movements: {metrics.average_container_movements:.2f}")
        print(f"  - Total movements: {metrics.total_container_movements_for_all_retrievals}")

        print(f"\nGrid Summary:")
        total_containers = sum(len(stack) for row in grid for stack in row)
        max_height = max((len(stack) for row in grid for stack in row), default=0)
        occupied_cells = sum(1 for row in grid for stack in row if stack)
        print(f"  - Total containers in grid: {total_containers}")
        print(f"  - Max stack height: {max_height}")
        print(f"  - Occupied cells: {occupied_cells}/{config.rows * config.cols}")

        return metrics

    except Exception as e:
        print(f"[ERROR] Algorithm failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("\n" + "="*60)
    print("WAREHOUSE OPTIMIZATION ALGORITHMS - TEST SUITE")
    print("="*60)

    results = {}
    results["Greedy (Baseline)"] = test_algorithm("Greedy Algorithm", optimize_greedy)
    results["A* Pathfinding"] = test_algorithm("A* Algorithm", optimize_layout_astar)
    results["Genetic Algorithm"] = test_algorithm("Genetic Algorithm (Framework)", optimize_layout_genetic)
    results["Reinforcement Learning"] = test_algorithm("Reinforcement Learning (Framework)", optimize_layout_reinforcement)

    print(f"\n{'='*60}")
    print("SUMMARY COMPARISON")
    print(f"{'='*60}\n")

    print(f"{'Algorithm':<30} {'Utilization':<15} {'Retrieval':<15}")
    print("-" * 60)

    for name, metrics in results.items():
        if metrics:
            print(f"{name:<30} {metrics.space_utilization:>6.2f}%{'':<7} {metrics.average_retrieval_time:>6.2f} min")

    best_algo = max(
        ((name, m) for name, m in results.items() if m),
        key=lambda x: x[1].space_utilization - (x[1].average_retrieval_time * 0.5),
        default=(None, None),
    )

    if best_algo[0]:
        print(f"\n[OK Best] {best_algo[0]} achieved optimal balance")

    print(f"\n{'='*60}")
    print("[OK] ALL TESTS COMPLETED")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
