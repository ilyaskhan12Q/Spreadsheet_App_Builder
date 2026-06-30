from core.blueprint import Blueprint
from core.validator.constraint_checker import (
    check_bounds,
    check_formula_syntax,
    check_merge_conflicts,
)


class BlueprintValidator:
    def validate(self, raw_json: str) -> Blueprint:
        """
        Parses raw_json into a Blueprint model and runs logical constraints/layout checks.
        Raises ValidationError or LayoutConflictError.
        """
        # Parse & Validate basic schema using Pydantic
        # This will raise pydantic.ValidationError if types or required fields are missing/incorrect
        blueprint = Blueprint.model_validate_json(raw_json)
        return self.validate_blueprint(blueprint)

    def validate_blueprint(self, blueprint: Blueprint) -> Blueprint:
        """
        Runs logical constraints/layout checks on an existing Blueprint model.
        Raises LayoutConflictError.
        """
        # Run custom constraint checkers
        check_bounds(blueprint)
        check_merge_conflicts(blueprint)
        check_formula_syntax(blueprint)

        return blueprint
