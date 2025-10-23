from __future__ import annotations

from typing import List, Optional, Sequence
from app.cycle_time_strategy import CycleTime, CycleTimeStrategy
from app.simple_cycle_time_strategy import SimpleCycleTimeStrategy
from app.complex_cycle_time_strategy import ComplexCycleTimeStrategy


class CycleTimeCalculator:
    """
    Factory class for calculating cycle times from Jira issue histories.
    
    This class automatically selects the appropriate strategy based on the
    complexity of the issue history:
    - SimpleCycleTimeStrategy for clean, straightforward processes
    - ComplexCycleTimeStrategy for complicated processes with multiple assignees
    
    The calculator separates concerns and makes the cycle time calculation logic
    more maintainable and testable.
    """
    
    def __init__(self, in_progress_names: Sequence[str], done_names: Sequence[str], exclude_statuses: Sequence[str] = ("Acceptance",)):
        """
        Initialize the calculator with status names.
        
        Args:
            in_progress_names: List of status names that indicate work has started
            done_names: List of status names that indicate work is completed
            exclude_statuses: List of status names to exclude from cycle time (e.g., "Acceptance")
        """
        self.in_progress_names = list(in_progress_names)
        self.done_names = list(done_names)
        self.exclude_statuses = list(exclude_statuses)
        
        # Pre-create strategy instances
        self.simple_strategy = SimpleCycleTimeStrategy(
            self.in_progress_names,
            self.done_names,
            self.exclude_statuses
        )
        self.complex_strategy = ComplexCycleTimeStrategy(
            self.in_progress_names,
            self.done_names,
            self.exclude_statuses
        )
    
    def calculate_cycle_times(self, client, issue_keys: List[str], assignee_account_id: Optional[str] = None) -> List[CycleTime]:
        """
        Calculate cycle times for a list of issue keys.
        
        This method automatically selects the appropriate strategy (simple or complex)
        for each issue based on its history complexity.
        
        Args:
            client: Jira client instance
            issue_keys: List of issue keys to process
            assignee_account_id: Optional assignee filter
            
        Returns:
            List of CycleTime objects
        """
        results = []
        
        for issue_key in issue_keys:
            try:
                histories = client.get_issue_changelog(issue_key)
                
                # Select the appropriate strategy based on issue complexity
                strategy = self._select_strategy(histories, assignee_account_id)
                
                # Calculate cycle time using the selected strategy
                cycle_time = strategy.calculate(histories, issue_key, assignee_account_id)
                results.append(cycle_time)
                
            except Exception as e:
                # If we can't process an issue, create a failed cycle time
                results.append(CycleTime(
                    issue_key=issue_key,
                    in_progress_at=None,
                    done_at=None,
                    seconds=None
                ))
        
        return results
    
    def _select_strategy(self, histories: List[dict], assignee_account_id: Optional[str] = None) -> CycleTimeStrategy:
        """
        Select the appropriate calculation strategy based on issue complexity.
        
        Decision criteria:
        - Use ComplexCycleTimeStrategy if:
          * Assignee filter is provided (need to track assignee periods)
          * Multiple assignee changes (> 2)
          * Many status changes (> 5)
        - Otherwise use SimpleCycleTimeStrategy
        
        Args:
            histories: List of history entries from Jira
            assignee_account_id: Optional assignee filter
            
        Returns:
            The appropriate strategy instance
        """
        # Use the strategy's static method to determine complexity
        is_complex = CycleTimeStrategy.should_use_complex_strategy(histories, assignee_account_id)
        
        if is_complex:
            return self.complex_strategy
        else:
            return self.simple_strategy
    
    def get_strategy_info(self, histories: List[dict], assignee_account_id: Optional[str] = None) -> dict:
        """
        Get information about which strategy would be used for a given history.
        
        Useful for debugging and understanding why a particular strategy was selected.
        
        Args:
            histories: List of history entries from Jira
            assignee_account_id: Optional assignee filter
            
        Returns:
            Dictionary with strategy information
        """
        assignee_changes = 0
        status_changes = 0
        
        for history in histories:
            for item in history.get("items", []):
                field = item.get("field")
                if field == "assignee":
                    assignee_changes += 1
                elif field == "status":
                    status_changes += 1
        
        is_complex = CycleTimeStrategy.should_use_complex_strategy(histories, assignee_account_id)
        strategy_name = "ComplexCycleTimeStrategy" if is_complex else "SimpleCycleTimeStrategy"
        
        reasons = []
        if assignee_account_id:
            reasons.append("assignee filter provided")
        if assignee_changes > 2:
            reasons.append(f"multiple assignee changes ({assignee_changes})")
        if status_changes > 5:
            reasons.append(f"many status changes ({status_changes})")
        
        return {
            "strategy": strategy_name,
            "assignee_changes": assignee_changes,
            "status_changes": status_changes,
            "has_assignee_filter": assignee_account_id is not None,
            "reasons": reasons if reasons else ["simple linear process"]
        }
