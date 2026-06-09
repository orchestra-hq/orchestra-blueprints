from datetime import datetime, timezone

from pipeline_health.classify import classify_pipeline, schedule_removed_with_healthy_manual

NOW = datetime(2026, 6, 9, 14, 0, 0, tzinfo=timezone.utc)


def _run(trigger_type, status, created_at):
    return {
        "pipelineName": "Test pipeline",
        "envName": "Production",
        "runStatus": status,
        "createdAt": created_at,
        "completedAt": created_at,
        "triggeredBy": [{"triggerType": trigger_type}],
    }


def test_schedule_removed_manual_warning_is_healthy():
    runs = [
        _run("MANUAL", "WARNING", "2026-06-08T08:49:02+00:00"),
        _run("SCHEDULED", "FAILED", "2026-06-05T07:00:43+00:00"),
    ]
    assert schedule_removed_with_healthy_manual(runs, NOW) is True

    result = classify_pipeline("pid", runs, {}, NOW)
    assert result["state"] == "Healthy"


def test_active_schedule_with_manual_latest_stays_degraded():
    runs = [
        _run("MANUAL", "WARNING", "2026-06-08T08:42:42+00:00"),
        _run("SCHEDULED", "FAILED", "2026-06-08T07:00:12+00:00"),
    ]
    assert schedule_removed_with_healthy_manual(runs, NOW) is False

    result = classify_pipeline("pid", runs, {}, NOW)
    assert result["state"] == "Degraded"


def test_scheduled_warning_stays_degraded():
    runs = [
        _run("SCHEDULED", "WARNING", "2026-06-09T07:00:44+00:00"),
        _run("SCHEDULED", "WARNING", "2026-06-08T07:00:44+00:00"),
    ]
    result = classify_pipeline("pid", runs, {}, NOW)
    assert result["state"] == "Degraded"
