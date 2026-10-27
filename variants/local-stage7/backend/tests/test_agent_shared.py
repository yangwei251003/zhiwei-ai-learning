import pytest

from app.agents.shared import parse_json_object
from app.core.llm import SparkAPIError


def test_parse_json_object_extracts_a_complete_object_wrapped_in_model_prose() -> None:
    content = """下面是学习路径：
```json
{"title":"图遍历路线","goal":"掌握 BFS 与 DFS","steps":[{"title":"基础","description":"理解图结构"}]}
```
请按步骤学习。"""

    result = parse_json_object(content)

    assert result["title"] == "图遍历路线"
    assert result["steps"][0]["title"] == "基础"


def test_parse_json_object_still_rejects_prose_without_a_real_object() -> None:
    with pytest.raises(SparkAPIError, match="valid JSON object"):
        parse_json_object("先学习基础，再完成练习，没有结构化对象。")
