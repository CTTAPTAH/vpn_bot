from dataclasses import dataclass

@dataclass(frozen=True)
class PlanPresentation:
    emoji: str
    description: str | None = None

PLAN_PRESENTATION_BY_MONTHS = {
    1: PlanPresentation("🔓", "Идеально, чтобы попробовать."),
    3: PlanPresentation("🔥", "Самый популярный."),
    6: PlanPresentation("⚡️", "Максимум выгоды."),
    12: PlanPresentation("👑", "Самая низкая цена за месяц."),
}