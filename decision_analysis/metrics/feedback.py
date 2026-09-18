"""Feedback and counterfactual analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from decision_analysis.layers.tasks import TaskResult

@dataclass
class TaskFeedback:
    task_id: str
    action_taken: str
    actual_quality: float
    optimal_action: str
    optimal_quality: float
    improvement_advice: str

class FeedbackGenerator:
    """Generates counterfactuals and advice for better outcomes on tasks."""
    
    def generate_feedback(self, task_result: TaskResult) -> TaskFeedback:
        advice: List[str] = []
        optimal_action = "Execute with full context and alignment"
        optimal_quality = 1.0
        
        if task_result.quality < 0.5:
            advice.append("The outcome was suboptimal.")
        
        if task_result.info_quality < 0.7:
            advice.append("Gather more robust information before deciding.")
            optimal_action = "Delay decision to seek better information."
            
        if task_result.alignment < 0.7:
            advice.append("Ensure goals are aligned among agents.")
            
        if not advice:
            advice.append("The action was already near optimal.")
            optimal_quality = task_result.quality
            optimal_action = task_result.action_taken
            
        improvement_advice = " ".join(advice)
        
        return TaskFeedback(
            task_id=task_result.task.id,
            action_taken=task_result.action_taken,
            actual_quality=task_result.quality,
            optimal_action=optimal_action,
            optimal_quality=optimal_quality,
            improvement_advice=improvement_advice
        )
