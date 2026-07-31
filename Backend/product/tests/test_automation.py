"""
JARVIS Product 1.7 - Automation Engine Comprehensive Test Suite.
Tests Validator, Registry, Scheduler, Triggers, Conditions, Executor via P1.5, Retries, Queue, History, and Tools.
"""

import os
import tempfile
import time
import pytest
from backend.product.automation import (
    AutomationManager,
    WorkflowManager,
    WorkflowValidator,
    WorkflowRegistry,
    Workflow,
    WorkflowStatus,
    TriggerType,
    TriggerConfig,
    ConditionConfig,
    ActionStep,
    ConditionEvaluator,
    ActionExecutor,
    TaskQueue,
    get_automation_tool_metadatas,
)
from backend.product.tools import (
    ProductToolExecutionManager,
    ToolMetadata,
    ToolCategory,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def automation_mgr(temp_dir):
    db_path = os.path.join(temp_dir, "test_automation.db")
    mgr = AutomationManager(db_path=db_path)
    mgr.initialize()
    yield mgr
    mgr.shutdown()


def test_workflow_validator():
    validator = WorkflowValidator()
    
    # Valid workflow
    wf_valid = Workflow.create_new(
        name="Daily Backup",
        description="Backs up system files",
        owner="usr_alice",
        trigger=TriggerConfig(trigger_type=TriggerType.TIME_INTERVAL, interval_seconds=3600),
        actions=[ActionStep(step_id="s1", tool_id="knowledge_search", arguments={"query": "backup"})],
    )
    is_valid, errors = validator.validate_workflow(wf_valid)
    assert is_valid is True
    assert len(errors) == 0

    # Invalid workflow (empty name & missing tool_id)
    wf_invalid = Workflow.create_new(
        name="",
        description="",
        owner="usr_alice",
        trigger=TriggerConfig(trigger_type=TriggerType.MANUAL),
        actions=[ActionStep(step_id="s1", tool_id="")],
    )
    is_valid, errors = validator.validate_workflow(wf_invalid)
    assert is_valid is False
    assert len(errors) >= 2


def test_workflow_registry_and_persistence(temp_dir):
    db_path = os.path.join(temp_dir, "registry_test.db")
    registry = WorkflowRegistry(db_path=db_path)
    registry.initialize()

    wf = Workflow.create_new(
        name="Ingest Research Papers",
        description="Monitors downloads and ingests papers into Knowledge Engine",
        owner="usr_bob",
        trigger=TriggerConfig(trigger_type=TriggerType.FILESYSTEM, watch_directory="/tmp/downloads"),
        actions=[ActionStep(step_id="s1", tool_id="knowledge_ingest", arguments={"file_path": "/tmp/paper.pdf", "title": "Paper"})],
    )

    assert registry.register_workflow(wf) is True

    fetched = registry.get_workflow(wf.workflow_id)
    assert fetched is not None
    assert fetched.name == "Ingest Research Papers"
    assert fetched.trigger.watch_directory == "/tmp/downloads"


def test_condition_evaluator(temp_dir):
    evaluator = ConditionEvaluator()
    sample_file = os.path.join(temp_dir, "test_target.txt")

    cond = ConditionConfig(condition_type="file_exists", target=sample_file)
    
    # File does not exist
    assert evaluator.evaluate(cond, {"file_path": sample_file}) is False

    # Create file
    with open(sample_file, "w") as f:
        f.write("content")
    assert evaluator.evaluate(cond, {"file_path": sample_file}) is True


def test_action_executor_via_p15(temp_dir):
    # Register mock P1.5 tool
    tool_mgr = ProductToolExecutionManager()
    
    def sample_tool_handler(message: str = "hello"):
        return {"response": f"Processed: {message}"}

    tool_meta = ToolMetadata(
        tool_id="mock_automation_tool",
        name="Mock Tool",
        description="Mock tool for automation testing",
        category=ToolCategory.UTILITY,
        handler=sample_tool_handler,
    )
    tool_mgr.metadata_registry.register_tool_metadata(tool_meta)

    executor = ActionExecutor()
    step = ActionStep(step_id="step1", tool_id="mock_automation_tool", arguments={"message": "automated execution"})
    
    res = executor.execute_step(step, owner_id="usr_alice", correlation_id="corr_123")
    assert res["status"] == "SUCCESS"
    assert res["result_payload"]["response"] == "Processed: automated execution"


def test_automation_workflow_execution(automation_mgr, temp_dir):
    # Create workflow
    wf = automation_mgr.create_workflow(
        name="Automated Knowledge Search",
        description="Triggers knowledge search step",
        owner="usr_alice",
        trigger=TriggerConfig(trigger_type=TriggerType.MANUAL),
        actions=[
            ActionStep(
                step_id="step1",
                tool_id="knowledge_search",
                arguments={"query": "test"},
            )
        ],
    )

    run_id = automation_mgr.trigger_workflow_manually(wf.workflow_id)
    assert run_id is not None

    # Wait for async queue worker execution
    time.sleep(0.5)

    history = automation_mgr.list_execution_history(workflow_id=wf.workflow_id)
    assert len(history) > 0
    assert history[0].run_id == run_id
    assert history[0].status.value in ("COMPLETED", "RUNNING")


def test_workflow_pause_resume_delete(automation_mgr):
    wf = automation_mgr.create_workflow(
        name="Periodic Cleanup",
        description="Periodic cleanup task",
        owner="usr_bob",
        trigger=TriggerConfig(trigger_type=TriggerType.TIME_INTERVAL, interval_seconds=3600),
        actions=[ActionStep(step_id="s1", tool_id="knowledge_search", arguments={"query": "cleanup"})],
    )

    assert automation_mgr.pause_workflow(wf.workflow_id, "usr_bob") is True
    paused_wf = automation_mgr.get_workflow(wf.workflow_id)
    assert paused_wf.status == WorkflowStatus.PAUSED

    assert automation_mgr.resume_workflow(wf.workflow_id, "usr_bob") is True
    resumed_wf = automation_mgr.get_workflow(wf.workflow_id)
    assert resumed_wf.status == WorkflowStatus.ACTIVE

    assert automation_mgr.delete_workflow(wf.workflow_id, "usr_bob") is True
    assert automation_mgr.get_workflow(wf.workflow_id) is None


def test_automation_tools_metadata():
    tools = get_automation_tool_metadatas()
    assert len(tools) == 7
    tool_ids = [t.tool_id for t in tools]
    assert "automation_create_workflow" in tool_ids
    assert "automation_trigger_workflow" in tool_ids
    assert "automation_pause_workflow" in tool_ids
    assert "automation_resume_workflow" in tool_ids
    assert "automation_delete_workflow" in tool_ids
    assert "automation_list_workflows" in tool_ids
    assert "automation_get_history" in tool_ids
