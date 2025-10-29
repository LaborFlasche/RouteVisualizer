import os
from copy import deepcopy
import random
from tqdm import tqdm
import time
from typing import List, Dict, Tuple
import streamlit as st
import numpy as np
from src.utils.utils import logical_round
from src.optimizing.child import Child
from src.optimizing.turn_into_format import OptimizingDataset
from src.optimizing.draw_changes import TourOptimizationComparator

class TourOptimizer:
    """Main module for the optimization of the routes"""

    def __init__(self,
                 distance_matrix: np.ndarray,
                 children: List[Child],
                 school_positions: Dict[int, int],  # school_id -> index in matrix
                 max_capacity: int = 8):
        """
        Args:
            distance_matrix: NxN matrix containing distances between children
            children: list of all children objects
            school_positions: mapping from school_id to index in distance matrix
            max_capacity: max number of children per tour
        """
        self.distance_matrix = distance_matrix
        self.children = children
        self.school_positions = school_positions
        self.max_capacity = max_capacity


        # Generate tours by assigning every child to its corresponding tour
        self.tours = self._organize_tours()

    def _organize_tours(self) -> Dict[int, List[Child]]:
        """Organize Children into tours based on their tour_id"""
        tours = {}
        for child in self.children:
            if child.tour_id not in tours:
                tours[child.tour_id] = []
            tours[child.tour_id].append(child)
        return tours

    def calculate_tour_cost(self, tour: List[Child]) -> float:
        """
        Calculate the total tour costs

        Args:
            tour: Liste von Kindern in der Reihenfolge der Abholung
            metric: 'duration' oder 'distance'
        """
        if "children_to_index" not in st.session_state:
            return 0
        children_to_index = st.session_state["children_to_index"]
        cost = 0
        if len(tour) == 0:
            return cost

        matrix = self.distance_matrix

        # First calculate the cost from the first child to the last one
        for i in range(len(tour) - 1):
            cost += matrix[children_to_index[tour[i].id], children_to_index[tour[i + 1].id]]

        # Add the costs for the last child to the school
        school_idx = self.school_positions[tour[0].school_id]
        cost += matrix[children_to_index[tour[-1].id], school_idx]

        return cost

    def optimize_tour_order_2opt(self, tour_id: int) -> Tuple[List[Child], float]:
        """
        Optimize the intra tour order using 2-opt algorithm

        return:
            optimized tour and the improvement in cost
        """
        tour = self.tours[tour_id].copy()
        if len(tour) <= 2:
            return tour, 0

        initial_cost = self.calculate_tour_cost(tour)
        improved = True

        while improved:
            improved = False
            for i in range(1, len(tour) - 1):
                for j in range(i + 1, len(tour)):
                    new_tour = tour[:i] + tour[i:j][::-1] + tour[j:]
                    new_cost = self.calculate_tour_cost(new_tour)

                    if new_cost < self.calculate_tour_cost(tour):
                        tour = new_tour
                        improved = True
                        break
                if improved:
                    break

        final_cost = self.calculate_tour_cost(tour)
        improvement = initial_cost - final_cost

        return tour, improvement

    def optimize_all_tours_intra(self) -> Dict[str, any]:
        """
        Optimize all tours individually using 2-opt

        Returns:
            dict with total improvement and details per tour
        """
        total_improvement = 0
        optimized_tours = {}
        improvements = []

        for tour_id in self.tours.keys():
            optimized_tour, improvement = self.optimize_tour_order_2opt(tour_id)
            optimized_tours[tour_id] = optimized_tour
            total_improvement += improvement
            improvements.append({
                'tour_id': tour_id,
                'improvement': improvement,
                'original_cost': self.calculate_tour_cost(self.tours[tour_id]),
                'optimized_cost': self.calculate_tour_cost(optimized_tour)
            })

        return {
            'total_improvement': total_improvement,
            'optimized_tours': optimized_tours,
            'details': improvements
        }

    def try_swap_children(self, child1: Child, child2: Child,
                          tour1: List[Child], tour2: List[Child]) -> Tuple[bool, float]:
        """
        Test if swapping two children between two tours improves the cost

        Returns:
            (is_improved, savings)
        """
        if child1.schule_id != tour2[0].schule_id or child2.schule_id != tour1[0].schule_id:
            return False, 0  # Verschiedene Schulen

        current_cost = (self.calculate_tour_cost(tour1) +
                        self.calculate_tour_cost(tour2))

        new_tour1 = [child2 if c.id == child1.id else c for c in tour1]
        new_tour2 = [child1 if c.id == child2.id else c for c in tour2]

        new_tour1, _ = self.optimize_tour_order_2opt_list(new_tour1)
        new_tour2, _ = self.optimize_tour_order_2opt_list(new_tour2)

        new_cost = (self.calculate_tour_cost(new_tour1) +
                    self.calculate_tour_cost(new_tour2))

        improvement = current_cost - new_cost
        return improvement > 0, improvement

    def optimize_tour_order_2opt_list(self, tour: List[Child]) -> Tuple[List[Child], float]:
        """2-opt for a given list of children"""
        if len(tour) <= 2:
            return tour, 0

        initial_cost = self.calculate_tour_cost(tour)
        improved = True

        while improved:
            improved = False
            for i in range(1, len(tour) - 1):
                for j in range(i + 1, len(tour)):
                    new_tour = tour[:i] + tour[i:j][::-1] + tour[j:]
                    new_cost = self.calculate_tour_cost(new_tour)

                    if new_cost < self.calculate_tour_cost(tour):
                        tour = new_tour
                        improved = True
                        break
                if improved:
                    break

        final_cost = self.calculate_tour_cost(tour)
        return tour, initial_cost - final_cost

    def optimize_inter_tour_swaps(self, max_iterations=1000,
                                  temperature=100, cooling_rate=0.995) -> Dict[str, any]:
        """
        Optimize inter-tour swaps using Simulated Annealing

        Args:
            max_iterations: max iteration
            temperature: temperature
            cooling_rate: cooling
        """
        current_tours = deepcopy(self.tours)
        best_tours = deepcopy(current_tours)

        current_cost = sum(self.calculate_tour_cost(tour)
                           for tour in current_tours.values())
        best_cost = current_cost

        swaps_performed = []
        temp = temperature

        for iteration in tqdm(range(max_iterations)):
            tour_ids = list(current_tours.keys())
            tour1_id, tour2_id = random.sample(tour_ids, 2)

            tour1 = current_tours[tour1_id]
            tour2 = current_tours[tour2_id]

            if len(tour1) < 1 or len(tour2) < 1:
                continue

            if tour1[0].school_id != tour2[0].school_id:
                continue

            child1 = random.choice(tour1)
            child2 = random.choice(tour2)

            # Berechne Kosten vor Swap
            old_cost = (self.calculate_tour_cost(tour1) +
                        self.calculate_tour_cost(tour2))

            new_tour1 = [child2 if c.id == child1.id else c for c in tour1]
            new_tour2 = [child1 if c.id == child2.id else c for c in tour2]

            new_tour1, _ = self.optimize_tour_order_2opt_list(new_tour1)
            new_tour2, _ = self.optimize_tour_order_2opt_list(new_tour2)

            new_cost = (self.calculate_tour_cost(new_tour1) +
                        self.calculate_tour_cost(new_tour2))

            delta = new_cost - old_cost

            if delta < 0 or random.random() < np.exp(-delta / temp):
                current_tours[tour1_id] = new_tour1
                current_tours[tour2_id] = new_tour2
                current_cost = current_cost - old_cost + new_cost

                if delta < 0:
                    swaps_performed.append({
                        'iteration': iteration,
                        'tour1_id': tour1_id,
                        'tour2_id': tour2_id,
                        'child1': f"{child1.forname} {child1.surname}",
                        'child2': f"{child2.forname} {child2.surname}",
                        'improvement': -delta
                    })

                if current_cost < best_cost:
                    best_tours = deepcopy(current_tours)
                    best_cost = current_cost

            temp *= cooling_rate

        total_improvement = sum(self.calculate_tour_cost(tour)
                                for tour in self.tours.values()) - best_cost

        return {
            'total_improvement': total_improvement,
            'optimized_tours': best_tours,
            'swaps_performed': swaps_performed,
            'iterations': max_iterations,
            'final_cost': best_cost
        }

    def full_optimization(self, inter_tour_iterations=1000, status_text=None) -> Dict[str, any]:
        """
        Perform a full optimization in three steps:
        1. Intra-Tour-Optimizing (Oder)
        2. Inter-Tour-Optimizing (Swaps)
        3. Another Intra-Tour-Optimizing
        """
        status_text.text("🔄 Starte die erste Intra-Tour-Optimierung...")
        intra_result1 = self.optimize_all_tours_intra()

        # Update tours mit optimierten Reihenfolgen
        status_text.text(f"🔄 Ersparnisse nach der ersten Runde {round(intra_result1['total_improvement'], 2)} Meter")
        self.tours = intra_result1['optimized_tours']

        if len(self.tours) < 2:
            return {
                'total_improvement': intra_result1['total_improvement'],
                'intra_optimization_1': intra_result1,
                'inter_optimization': None,
                'intra_optimization_2': None,
                'final_tours': intra_result1['optimized_tours']
            }

        status_text.text("🔄 Starte die Inter-Tour-Optimierung...")
        inter_result = self.optimize_inter_tour_swaps(
            max_iterations=inter_tour_iterations,
        )
        status_text.text(f"🔄 Ersparnisse nach der Inter-Tour-Optimierung {round(inter_result['total_improvement'], 2)} Meter")
        # Update tours mit Swap-Ergebnissen
        self.tours = inter_result['optimized_tours']

        status_text.text("🔄 Starte die zweite Intra-Tour-Optimierung...")
        intra_result2 = self.optimize_all_tours_intra()

        total_improvement = (intra_result1['total_improvement'] +
                             inter_result['total_improvement'] +
                             intra_result2['total_improvement'])

        return {
            'total_improvement': total_improvement,
            'intra_optimization_1': intra_result1,
            'inter_optimization': inter_result,
            'intra_optimization_2': intra_result2,
            'final_tours': intra_result2['optimized_tours']
        }

class OptimizerModule:
    def __init__(self, config):
        self.config = config

    def save_optimized_as_og(self, optimized_tour_dict):
        """Save the optimized tour as session state with og tour information."""
        st.session_state["optimized_tour_id_to_df"] = {}
        for tour_id, tour_df in optimized_tour_dict.items():
            og_tour_info = st.session_state["tour_id_to_df"].get(tour_id, {})
            st.session_state["optimized_tour_id_to_df"][tour_id] = {
                "tour_df": tour_df,
                "symbol": og_tour_info.get("symbol", ""),
                "km_besetzt": og_tour_info.get("km_besetzt", 0)
            }
        return st.session_state["optimized_tour_id_to_df"]


    def get_costs_for_tours(self, tour_dict, optimizer):
        optimized_distances = {}
        for tour_id, tour in tour_dict.items():
            if len(tour) > 0:
                distance = optimizer.calculate_tour_cost(tour)
                optimized_distances[str(tour_id)] = logical_round(distance / 1000)
        return optimized_distances

    def optimize(self):
        """Optimize the routes based on the provided configuration.
        return: for every tour_id a set of optimized routes
        return: changes made to the original tour plan as strings
        """
        # Create Progress Bar for Streamlit
        progress_bar = st.progress(0)
        status_text = st.empty()
        start_time = time.time()

        def update_progress(completed_comparison, total_comparisons):
            progress = completed_comparison / total_comparisons
            progress_bar.progress(progress)

            elapsed_time = time.time() - start_time
            avg_time_per_step = elapsed_time / completed_comparison if completed_comparison > 0 else 0
            remaining_steps = total_comparisons - completed_comparison
            estimated_time_left = remaining_steps * avg_time_per_step

            time_left = f'{round(estimated_time_left/60, 2)} Minuten' if estimated_time_left > 60 else f'{round(estimated_time_left, 2)} Sekunden'

            status_text.text(
                f"Erstelle die Distanz-Matrix: {completed_comparison}/{total_comparisons} abgeschlossen. "
                f"Verbleibende Zeit: {time_left}"
            )

        # First turn the tour data into a list of Child objects
        status_text.text("📊 Extrahiere die benötigten Datan aus den Touren...")
        osmr_url = os.getenv("OSMR_URL", None)
        distance_matrix, school_indeces, children, school = OptimizingDataset.generate_optimizing_dataset(update_progress,
                                                                                                          status_text,
                                                                                                          osmr_url)
        if distance_matrix is None or school_indeces is None or children is None:
            st.error("Fehler beim Laden der Optimierungsdaten.")
            return None
        status_text.text("🚀 Starte die Optimierung der Touren...")
        optimizer = TourOptimizer(
            distance_matrix=distance_matrix.to_numpy(), # Optimizer works with numpy arrays
            children=children,
            school_positions=school_indeces,
            max_capacity=self.config.get('max_capacity', 8)
        )
        result_dict = optimizer.full_optimization(
            inter_tour_iterations=self.config.get('inter_tour_iterations', 10000),
            status_text=status_text
        )

        if result_dict is None:
            st.error("Fehler bei der Optimierung der Touren.")
            return {}

        status_text.text("Bringe die optimierten Touren in das korrekte Format...")
        optimized_tour_dict = OptimizingDataset.turn_children_list_into_tour_dict(result_dict['final_tours'], school)

        # Save the optimized tour as session state with og tour information
        optimized_tour_dict = self.save_optimized_as_og(optimized_tour_dict)


        status_text.text("Vergleiche die optimierten Touren mit den Original-Touren...")
        comparator = TourOptimizationComparator()

        optimized_tour_dict, changes = comparator.compare(
            st.session_state["tour_id_to_df"],
            optimized_tour_dict
        )

        optimized_distances = self.get_costs_for_tours(result_dict['final_tours'], optimizer)
        osm_distances = self.get_costs_for_tours(optimizer.tours, optimizer)

        optimization_dict = {
            "total_improvement": {"value": logical_round(result_dict['total_improvement']), "name": "Gesamte Verbesserung (Distanz in Metern)"},
        }
        status_text.text("✅ Optimierung abgeschlossen!")

        return optimized_tour_dict, changes, optimization_dict, optimized_distances, osm_distances
