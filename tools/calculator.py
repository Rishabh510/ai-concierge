from typing import Literal
from livekit.agents import function_tool, RunContext, ToolError


@function_tool()
async def calculator(
    context: RunContext, num1: float, num2: float, operator: Literal["+", "-", "*", "/"]
) -> dict[str, float]:
    """Perform basic arithmetic calculations.

    Args:
        num1: First number for the calculation
        num2: Second number for the calculation
        operator: Mathematical operator - use + for addition, - for subtraction, * for multiplication, / for division

    Returns:
        Dictionary containing the result of the calculation
    """
    try:
        if operator == "+":
            result = num1 + num2
        elif operator == "-":
            result = num1 - num2
        elif operator == "*":
            result = num1 * num2
        elif operator == "/":
            if num2 == 0:
                raise ToolError("Cannot divide by zero")
            result = num1 / num2
        else:
            raise ToolError(f"Unsupported operator: {operator}")

        return {"result": result}

    except Exception as e:
        raise ToolError(f"Calculation error: {str(e)}")
