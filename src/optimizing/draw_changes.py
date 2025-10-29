import pandas as pd
from typing import Dict, Tuple


class TourOptimizationComparator:
    """
    Compares original and optimized tour dictionaries to identify changes.

    Returns:
        - optimized_tour_dict with color information
        - changes dict with textual descriptions of changes for each tour
    """

    def __init__(self):
        self.colors = {
            'unchanged': '#00F531',  # Green
            'position_changed': '#F5E900',  # Yellow
            'tour_changed': '#F50000'  # Red/Pink
        }

    def _is_empty_row(self, row: pd.Series) -> bool:
        """Check if a row represents an empty seat (Platz ist frei!)"""
        return row.get('fornames', '') == 'Platz ist frei!'

    def _create_child_identifier(self, row: pd.Series) -> str:
        """Create a unique identifier for a child based on their data"""
        if self._is_empty_row(row):
            return None
        # Use combination of name and address to identify unique children
        return f"{row.get('fornames', '')}_{row.get('surnames', '')}_{row.get('streets', '')}_{row.get('housenumbers', '')}"

    def _build_index(self, tour_dict: Dict) -> Dict[str, Tuple[str, int]]:
        """
        Build an index mapping child_identifier -> (tour_id, position)

        Args:
            tour_dict: Dictionary with tour_id as keys and tour data as values

        Returns:
            Dictionary mapping child identifiers to (tour_id, position) tuples
        """
        index = {}

        for tour_id, tour_data in tour_dict.items():
            df = tour_data['tour_df']

            for idx, row in df.iterrows():
                if not self._is_empty_row(row):
                    child_id = self._create_child_identifier(row)
                    if child_id:
                        index[child_id] = (tour_id, idx)

        return index

    def compare(self, original_tours: Dict, optimized_tours: Dict) -> Tuple[Dict, Dict]:
        """
        Compare original and optimized tours.

        Args:
            original_tours: Dictionary with original tour data
            optimized_tours: Dictionary with optimized tour data

        Returns:
            Tuple of (optimized_tours_with_colors, changes_dict)
            - optimized_tours_with_colors: Enhanced optimized_tours with color_map for each tour
            - changes_dict: Dictionary with tour_id as keys and change descriptions as values
        """
        # Build indices
        original_index = self._build_index(original_tours)
        optimized_index = self._build_index(optimized_tours)

        # Initialize results
        changes = {}
        optimized_with_colors = {}

        # Process each tour in the optimized tours
        for tour_id, tour_data in optimized_tours.items():
            df = tour_data['tour_df']
            tour_changes = []
            color_map = {}

            # Analyze each row in the optimized tour
            for idx, row in df.iterrows():
                if idx == len(df) - 1:
                    # Skip the last row (school)
                    continue
                if self._is_empty_row(row):
                    # Empty seats are always unchanged (green)
                    color_map[idx] = self.colors['unchanged']
                else:
                    child_id = self._create_child_identifier(row)

                    if not child_id or child_id not in original_index:
                        # New child (shouldn't happen in optimization, but handle it)
                        color_map[idx] = self.colors['unchanged']
                        continue

                    # Get original and optimized positions
                    orig_tour_id, orig_pos = original_index[child_id]
                    opt_tour_id = tour_id  # Current tour we're analyzing
                    opt_pos = idx  # Current position in this tour

                    child_name = f"{row.get('fornames', '')} {row.get('surnames', '')}"

                    # Ensure string comparison for tour_ids
                    if str(orig_tour_id) == str(opt_tour_id) and orig_pos == opt_pos:
                        # No change - GREEN
                        color_map[idx] = self.colors['unchanged']
                        # Don't add to tour_changes
                    elif str(orig_tour_id) == str(opt_tour_id) and orig_pos != opt_pos:
                        # Position changed within same tour - YELLOW
                        color_map[idx] = self.colors['position_changed']
                        tour_changes.append(
                            f"{child_name} - Position geändert: {orig_pos + 1} → {opt_pos + 1}"
                        )
                    else:
                        # Tour changed - RED
                        color_map[idx] = self.colors['tour_changed']
                        orig_symbol = original_tours.get(orig_tour_id, {}).get('symbol', '')
                        opt_symbol = tour_data.get('symbol', '')

                        # Format tour identifiers with fallback to tour_id
                        orig_tour_display = f"{orig_symbol} ({orig_tour_id})" if orig_symbol else f"Tour {orig_tour_id}"
                        opt_tour_display = f"{opt_symbol} ({opt_tour_id})" if opt_symbol else f"Tour {opt_tour_id}"

                        tour_changes.append(
                            f"{child_name} - Tour gewechselt: {orig_tour_display} (Pos. {orig_pos + 1}) → {opt_tour_display} (Pos. {opt_pos + 1})"
                        )

            # Format changes as text (only if there are changes)
            if tour_changes:
                changes_text = "\n".join([f"{i + 1}. {change}" for i, change in enumerate(tour_changes)])
                changes[str(tour_id)] = changes_text
            else:
                changes[str(tour_id)] = "Keine Änderungen für diese Tour gefunden!"  # No changes for this tour

            # Add color_map to optimized tour data
            optimized_with_colors[str(tour_id)] = {
                **tour_data,
                'color_map': color_map
            }

        return optimized_with_colors, changes

    def get_statistics(self, changes: Dict) -> Dict[str, int]:
        """
        Calculate statistics from changes dictionary.

        Args:
            changes: Dictionary with tour_id as keys and change descriptions as values

        Returns:
            Dictionary with statistics about changes
        """
        stats = {
            'total': 0,
            'unchanged': 0,
            'position_changed': 0,
            'tour_changed': 0,
            'empty_seats': 0
        }

        for tour_id, changes_text in changes.items():
            lines = changes_text.split('\n')
            for line in lines:
                stats['total'] += 1
                if 'Platz ist frei' in line:
                    stats['empty_seats'] += 1
                    stats['unchanged'] += 1
                elif 'Keine Änderung' in line:
                    stats['unchanged'] += 1
                elif 'Position geändert' in line:
                    stats['position_changed'] += 1
                elif 'Tour gewechselt' in line:
                    stats['tour_changed'] += 1

        return stats