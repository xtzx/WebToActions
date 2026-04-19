from enum import StrEnum


class ActionKind(StrEnum):
    ACTION_MACRO = "action_macro"
    BUSINESS_ACTION = "business_action"


ExecutableActionKind = ActionKind
