# Evidence-Gated Recovery v2.3

v2.3 keeps the v2.2 recovery policy and adds a narrowly scoped parser repair
for a redundant Qwen coordinate representation observed in the v2.2 smoke
test:

```json
{"type":"click","x":[876,298],"y":298}
```

The parser accepts this representation only when the second item in `x`
exactly equals the separate `y` value. It then normalizes the action to
`{"type":"click","x":876,"y":298}`. A mismatch remains invalid, so the
repair cannot silently choose between conflicting coordinates.

The repair changes syntax handling only. It does not select an action, infer a
target, bypass the repeat guard, or alter the verification and completion
rules. Earlier runners keep the stricter parser behavior.

```bash
python run_settings_evidence_gated_agent_v23.py --seed 1 --max-steps 8 --fault-mode none
python run_settings_evidence_gated_agent_v23.py --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
```
