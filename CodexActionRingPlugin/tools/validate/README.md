# Nine-action release validator

`validate.py` is the single deterministic entrypoint. A full run performs one
isolated clean Release build, all five .NET test suites, the Icon System suite,
validator contract tests, static source/package/privacy checks, exact artifact
size/SHA comparison, and official `LogiPluginTool verify`.

The build copies the immutable inputs into an evidence-owned snapshot, so all
`bin`/`obj` output remains inside the selected evidence directory. Its transient
development link is also redirected there. A local `open` shim suppresses the
generated project's reload URL, and the transient link is removed before the
contamination gate runs. No production package is rebuilt, packed, installed, or
loaded.

Run it once with an isolated official LogiPluginTool 6.1.4.22672:

```sh
python3 tools/validate/validate.py \
  --official-tool /path/to/logiplugintool \
  --official-dotnet-root /path/to/dotnet8 \
  --output ../.scratch/codex-action-ring-implementation/evidence/scope-cleanup/run-1
```

Run it again without rebuilding by supplying the first immutable report. The
entrypoint first requires the complete input manifest to match, reruns all cheap
read-only checks and official verify, then writes an exact PASS/FAIL fact
comparison:

```sh
python3 tools/validate/validate.py \
  --official-tool /path/to/logiplugintool \
  --official-dotnet-root /path/to/dotnet8 \
  --reuse-build-from ../.scratch/codex-action-ring-implementation/evidence/scope-cleanup/run-1/report.json \
  --output ../.scratch/codex-action-ring-implementation/evidence/scope-cleanup/run-2
```

Any failed build, test, source contract, package audit, or official verification
makes the entrypoint exit nonzero. Live Options+/MX Master acceptance is not part of
the nine-action completion gate.
