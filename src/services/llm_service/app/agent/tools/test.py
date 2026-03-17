from langchain_community.tools import ShellTool
from langchain_core.tools import BaseTool,BaseToolkit
from typing import Any, Type
from pydantic import BaseModel, Field

class MyToolKit(BaseToolkit):
    def get_tools(self) -> list[BaseTool]:
        return super().get_tools()
    
    
class ArgSchema(BaseModel):
    a: int = Field(description="First argument")
    b: int = Field(description="First argument")

class CustomTool(BaseTool):
    name: str = "my tool"
    description: str = "This is a test tool"
    args_schema: Type[ArgSchema] = ArgSchema

    def _run(self,a: int, b: int) -> Any:
        return a + b


seach_tool = ShellTool()
res = seach_tool.invoke("ls")

print(res)