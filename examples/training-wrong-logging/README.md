# Wrong Logging Example

This example logs a few normal scalars, then intentionally logs artifact payloads
with mismatched helpers and content types. Use it to inspect how the
SDK/backend/UI behave when callers send text as an image, image bytes as text,
invalid JSON text as JSON, and other incorrect combinations.

## Setup

```
cd examples/training-wrong-logging
uv sync
```

Configure the SDK if needed:

```
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

## Run

```
uv run python train.py --project-name "SDK Wrong Logging" --experiment-name "Wrong Artifact Inputs"
```
