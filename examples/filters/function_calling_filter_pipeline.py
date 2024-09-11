import os
from typing import Literal, List, Optional
from datetime import datetime

from blueprints.function_calling_blueprint import Pipeline as FunctionCallingBlueprint

class Pipeline(FunctionCallingBlueprint):
    class Valves(FunctionCallingBlueprint.Valves):
        # Add your custom parameters here if needed
        pass

    class Tools:
        def __init__(self, pipeline) -> None:
            self.pipeline = pipeline

        def get_current_time(self) -> str:
            """
            Get the current time.

            :return: The current time.
            """
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            return f"Current Time = {current_time}"

        def calculator(self, equation: str) -> str:
            """
            Calculate the result of an equation.

            :param equation: The equation to calculate.
            """
            # Avoid using eval in production code
            try:
                result = eval(equation)
                return f"{equation} = {result}"
            except Exception as e:
                print(e)
                return "Invalid equation"

    def __init__(self):
        super().__init__()
        self.name = "My Tools Pipeline"
        self.valves = self.Valves(
            **{
                **self.valves.model_dump(),
                "pipelines": ["*"],  # Connect to all pipelines
            },
        )
        self.tools = self.Tools(self)
