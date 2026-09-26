from analyzer.runner.test_runner import run_tests
import json

result = run_tests(
    """
def test_generated_dummy():
    assert True
""",
    "sample_repo",
    test_files=["sample_repo/tests/test_timeout_demo.py"],
    source_dirs=["sample_repo/src"],
)

print(json.dumps(result, indent=2))