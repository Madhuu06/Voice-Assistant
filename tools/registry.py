import inspect

class ToolRegistry:
    def __init__(self):
        self.tools = []
        self.functions = {}

    def register(self, name, description, parameters):
        def decorator(func):
            self.tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            })
            self.functions[name] = func
            return func
        return decorator

    def get_tools_schema(self):
        return self.tools if self.tools else None

    def execute(self, tool_name, kwargs):
        if tool_name in self.functions:
            try:
                result = self.functions[tool_name](**kwargs)
                return str(result)
            except Exception as e:
                return f"Error executing {tool_name}: {e}"
        return f"Tool {tool_name} not found."

registry = ToolRegistry()
