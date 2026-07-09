# Python Coding Guidelines

Patterns established through the pdomain-prep-for-pgdp backend quality hardening (2026-05-16).
These are concrete rules, not abstract principles. Each rule has a canonical example from the codebase.

---

## Exception Handling

### Never use a catch-all that swallows the exception silently

```python
# WRONG — error disappears
with contextlib.suppress(Exception):
    do_thing()

# WRONG — wrong status code and no logging
except Exception as e:
    raise HTTPException(status_code=401, detail=str(e)) from e

# RIGHT — log it, then let it propagate or convert with correct semantics
try:
    do_thing()
except OSError as exc:
    log.error("do_thing failed: %s", exc)
    raise
```

### Split HTTP exception types by actual cause

Three-tier split for auth/storage/API dependencies:

```python
except HTTPException:
    raise
except (ConnectionError, TimeoutError, OSError) as e:
    raise HTTPException(status_code=503, detail="service unavailable") from e
except ValueError as e:
    raise HTTPException(status_code=422, detail=f"malformed input: {e}") from e
except Exception as e:
    log.exception("unexpected error")
    raise HTTPException(status_code=500, detail="unexpected error") from e
```

### Narrow `BaseException` only when you mean it

`BaseException` catches `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit`. Only use it
when you genuinely need to intercept those — and re-raise them after any cleanup:

```python
# WRONG — swallows KeyboardInterrupt
except BaseException:
    fut.cancel()

# RIGHT — re-raise non-Exception signals
except Exception as e:
    fut.set_exception(e)
except BaseException:
    fut.cancel()
    raise
```

### `except ImportError` for optional dependency guards — not `except Exception`

```python
# WRONG — hides real bugs
try:
    import layout_detector
except Exception:
    layout_detector = None

# RIGHT
try:
    import layout_detector
except ImportError:
    layout_detector = None
```

### Rollback paths must log, never silently suppress

```python
# WRONG
with contextlib.suppress(OSError):
    path.unlink()

# RIGHT — helper that logs and never re-raises
def _safe_rollback(paths: list[Path], context: str) -> None:
    for p in paths:
        try:
            p.unlink(missing_ok=True)
        except OSError as exc:
            log.error("rollback failed (%s): %s — %s", context, p, exc)
```

---

## Typed API Boundaries

### Never use `getattr` with a fallback to cross a library boundary

When calling pdomain-book-tools (or any external library), use the real API with `isinstance` guards.
A `getattr(obj, "field", 0)` silently produces 0 when the field name is wrong.

```python
# WRONG — wrong field names, produces (0,0,0,0) silently
x = getattr(bbox, "left", 0)
conf = getattr(word, "confidence", 0.0)

# RIGHT — fail loudly on wrong type, use documented API
from pd_book_tools.ocr.word import Word as PdWord

if not isinstance(w, PdWord):
    raise TypeError(f"expected pd_book_tools.ocr.word.Word, got {type(w)!r}")
bb = w.bounding_box
x1, y1, x2, y2 = bb.minX, bb.minY, bb.maxX, bb.maxY
conf = w.ocr_confidence or 0.0
```

### Map enum values with a dict, not substring matching on string representations

```python
# WRONG — fragile, breaks on enum repr changes
if "figure" in str(region.type).lower():
    return "illustration"

# RIGHT
from pd_book_tools.layout.region import RegionType

_REGION_TYPE_MAP: dict[RegionType, str] = {
    RegionType.figure: "illustration",
    RegionType.table: "illustration",
    RegionType.decoration: "decoration",
}

def _map_region_type(rt: RegionType) -> str:
    return _REGION_TYPE_MAP[rt]  # KeyError on unknown — fix the map, don't hide it
```

---

## Sentinel Values

### Use `None`, not a magic integer, as the "unknown" sentinel

```python
# WRONG — caller can't distinguish "zero drops" from "unknown"
dropped_word_count: int = 0
...
except Exception:
    dropped_word_count = -1  # magic number, undocumented contract

# RIGHT
dropped_word_count: int | None = None
...
except Exception:
    log.exception("validate_word_preservation failed; dropped count unknown")
    dropped_word_count = None
```

---

## Circuit Breakers

### Use *consecutive* failure semantics — reset the counter on success

A counter that never resets trips on cumulative failures, not consecutive ones.
Reset on success so a transient error doesn't permanently disable the path.

```python
_failures = 0
_MAX_FAILURES = 3

for item in items:
    if progress_cb is not None:
        try:
            await progress_cb(item)
            _failures = 0          # reset on success — consecutive semantics
        except Exception:
            _failures += 1
            if _failures >= _MAX_FAILURES:
                log.error("progress_cb disabled after %d consecutive failures", _failures)
                progress_cb = None
            else:
                log.exception("progress_cb failed (%d/%d)", _failures, _MAX_FAILURES)
```

### Express the threshold as a named constant at module level

```python
_CIRCUIT_BREAKER_MAX = 5   # module-level, not a magic 5 buried in a loop
```

---

## Pydantic Models

### Use `NonEmptyStr` for optional string fields that represent resource keys

Empty-string keys look valid but fail downstream. Coerce at ingest:

```python
from pydantic import BeforeValidator
from typing import Annotated

def _empty_str_to_none(v: str | None) -> str | None:
    return None if isinstance(v, str) and v == "" else v

NonEmptyStr = Annotated[str | None, BeforeValidator(_empty_str_to_none)]

class PageOutput(ApiModel):
    ocr_text_key: NonEmptyStr = None
    for_zip_image_key: NonEmptyStr = None
```

### New optional fields on response models default to `None` or `False`

Never add a required field to a response model that existing API consumers don't send.

```python
class GetPageTextResponse(ApiModel):
    text: str
    words: list[OcrWord]
    words_partial: bool = False       # new — safe default
    words_error: str | None = None    # new — safe default
```

---

## Protocol Completeness

### Every abstract Protocol method must have a concrete default or be enforced by type checking

When adding a method to a Protocol, add a default implementation that callers can trust:

```python
class IDatabase(Protocol):
    async def list_distinct_owner_ids(self) -> list[str]:
        return ["default"]   # safe default for single-tenant adapters
```

Then override in adapters that need the real behavior:

```python
class SqliteDatabase(IDatabase):
    async def list_distinct_owner_ids(self) -> list[str]:
        rows = await self._db.execute_fetchall(
            "SELECT DISTINCT owner_id FROM jobs"
        )
        return [r[0] for r in rows] or ["default"]
```

### Never use `getattr(obj, "method", None)` to call a Protocol method

It bypasses type checking and produces silent `None` when the method is absent.
If the object doesn't satisfy the Protocol, the `isinstance` check or mypy should catch it.

---

## Observability

### Gate debug tracebacks behind an env flag

```python
# settings.py
debug: bool = Field(default=False, alias="PGDP_DEBUG")

# error_handler.py
def install_error_handlers(app: FastAPI, *, debug: bool = False) -> None:
    @app.exception_handler(Exception)
    async def _handler(request, exc):
        details = traceback.format_exc().splitlines()[-3:] if debug else None
        return JSONResponse(status_code=500, content={"detail": "internal error", "trace": details})
```

### Log shutdown errors explicitly — never suppress them

```python
# WRONG
with contextlib.suppress(Exception):
    job_runner.stop()

# RIGHT
try:
    job_runner.stop()
except Exception:
    log.exception("error stopping job_runner during shutdown")
```

### Propagate new error fields all the way to the log

Adding a field to a dataclass is not enough — trace where the dataclass is *consumed*
and log the field there too:

```python
result = ocr_page(image, predictor)
if result.words_error:
    log.warning("OCR words extraction failed (words.json will be empty): %s", result.words_error)
```

---

## Init Patterns

### Declare instance attributes with their type in `__init__`, even if lazily created

```python
# WRONG — fragile, confuses type checkers
class SingleExecutor:
    async def submit(self):
        if not hasattr(self, "_queue"):
            self._queue = asyncio.PriorityQueue()

# RIGHT — explicit None init; lazy creation at first use is fine
class SingleExecutor:
    def __init__(self):
        self._queue: asyncio.PriorityQueue | None = None

    async def submit(self):
        if self._queue is None:
            self._queue = asyncio.PriorityQueue()
```

---

## Storage

### Reject absolute paths before doing any path join

```python
def _path(self, key: str) -> Path:
    if Path(key).is_absolute():
        raise ValueError(f"storage key must be relative, got: {key!r}")
    return self._root / key.lstrip("/")
```

### Catch only the specific exception that signals "not found"

```python
# WRONG — hides network errors, permission errors, etc.
try:
    await s3.head_object(...)
except Exception:
    return False

# RIGHT — only NoSuchKey means "not found"
try:
    await s3.head_object(...)
except s3.exceptions.NoSuchKey:
    return False
# Everything else propagates
```

---

## Testing

### Test the real API shape, not a mock of it

When testing adapters against pdomain-book-tools, construct real objects — not `MagicMock`:

```python
from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.word import Word

def _make_pd_word(text="hello", left=10, top=20, right=110, bottom=70, confidence=0.95):
    bb = BoundingBox(top_left=Point(left, top), bottom_right=Point(right, bottom))
    return Word(text=text, bounding_box=bb, ocr_confidence=confidence)
```

### Test the error path, not just the happy path

Every `try/except` that was added to fix a silent failure should have a test that
exercises the `except` branch and asserts on the observable side-effect (log line,
return value, raised exception):

```python
def test_disk_cost_scan_logs_first_oserror(tmp_path, caplog):
    good = tmp_path / "good.bin"
    good.write_bytes(b"x" * 100)
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"x" * 50)

    call_count = 0
    real_stat = Path.stat

    def patched_stat(self, **kwargs):
        nonlocal call_count
        if self == bad:
            call_count += 1
            if call_count == 2:   # second call = explicit .stat().st_size in try block
                raise OSError("permission denied")
        return real_stat(self, **kwargs)

    with patch.object(Path, "stat", patched_stat), caplog.at_level(logging.WARNING):
        result = _compute_stage_artifacts_bytes(tmp_path)

    assert result == 100   # partial sum, not zero, not raised
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "disk cost scan" in warnings[0].message
```
