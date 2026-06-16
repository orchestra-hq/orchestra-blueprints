# Pipeline health sweep

Helper scripts for the daily pipeline health agent.

## classify.py

Classifies pipelines from Orchestra `list_pipelines` JSON and prints an audit log.

```bash
# Save MCP list_pipelines output to /tmp/pipelines.json, then:
python .pipeline-sweep/classify.py /tmp/pipelines.json
```
