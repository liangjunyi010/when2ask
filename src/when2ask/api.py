"""Small official REST adapters. No SDK retry behavior can bypass our budgets."""
from __future__ import annotations

import json
import math
import ssl
import time
import urllib.error
import urllib.request

from .accounting import Audit, BackendBlocked


class APIError(RuntimeError):
    pass


class SchemaError(ValueError):
    pass


def integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def http_transport(url, headers, payload, timeout):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


class RestClient:
    def __init__(self, config, audit: Audit, transport=None, sleep=time.sleep):
        self.config, self.audit = config, audit
        self.transport, self.sleep = transport or http_transport, sleep

    def _request(self, path, payload, stage, parser):
        config = self.config
        backend = self.backend
        key = config.deepseek_key if backend == "deepseek" else config.typesafe_key
        base = config.deepseek_url if backend == "deepseek" else config.typesafe_url
        model = config.deepseek_model if backend == "deepseek" else config.jev_model
        if not key:
            raise APIError(f"{backend}: credential is not configured")
        last_error = None
        for attempt in range(1, config.max_retries + 2):
            record = self.audit.reserve(backend)
            record.update(stage=stage, configured_model=model, attempt=attempt,
                          request=payload, endpoint=path)
            self.audit.flush()
            start = time.perf_counter()
            schema_error, permanent, transient, body = False, None, True, None
            try:
                status, text = self.transport(base.rstrip("/") + path,
                                               {"Authorization": "Bearer " + key,
                                                "Content-Type": "application/json"},
                                               payload, config.timeout_s)
                record["latency_ms"] = (time.perf_counter() - start) * 1000
                record["http_status"] = status
                if status >= 400:
                    permanent = f"HTTP {status}" if status in (400, 401, 402, 403, 404, 422) else None
                    transient = status in (408, 429) or status >= 500
                try:
                    body = json.loads(text)
                except (json.JSONDecodeError, TypeError) as exc:
                    if status >= 400:
                        raise APIError(f"HTTP {status}: non-JSON response") from exc
                    raise SchemaError("Response body is not JSON") from exc
                record["response"] = config.sanitize(body)
                if status >= 400:
                    raise APIError(f"HTTP {status}: {json.dumps(config.sanitize(body))[:700]}")
                if not isinstance(body, dict):
                    raise SchemaError("Response must be an object")
                record["returned_model"] = body.get("model")
                usage = body.get("usage") or {}
                if not isinstance(usage, dict):
                    raise SchemaError("usage must be an object")
                record["input_tokens"] = integer(usage.get("prompt_tokens" if backend == "deepseek" else "input_tokens"))
                record["output_tokens"] = integer(usage.get("completion_tokens" if backend == "deepseek" else "output_tokens"))
                parsed = parser(body)
                record["status"] = "ok"
                if self.audit.session:
                    self.audit.session.outcome(backend, True)
                return parsed
            except SchemaError as exc:
                schema_error = True
                last_error = exc
                record.update(status="schema_error", error=str(config.sanitize(str(exc))))
                # The next DeepSeek attempt is explicitly a format repair, with
                # the same public state. No private hints are introduced.
                if payload and backend == "deepseek":
                    payload = dict(payload, messages=list(payload["messages"]) + [
                        {"role": "user", "content": f"Your previous response violated the JSON schema: {exc}. "
                         "Return only one valid JSON object matching the requested schema."}])
            except (APIError, urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                record.update(status="api_error", error=config.sanitize(str(exc)))
            finally:
                if record["latency_ms"] is None:
                    record["latency_ms"] = (time.perf_counter() - start) * 1000
                self.audit.flush()
            if self.audit.session:
                self.audit.session.outcome(backend, False, permanent)
            if permanent or not transient or attempt > config.max_retries:
                break
            self.sleep(min(.5 * attempt, 2))
        error_type = SchemaError if isinstance(last_error, SchemaError) else APIError
        raise error_type(str(config.sanitize(str(last_error))))


class DeepSeekClient(RestClient):
    backend = "deepseek"

    def models(self):
        def parse(body):
            if not isinstance(body.get("data"), list):
                raise SchemaError("Missing model data array")
            return body["data"]
        return self._request("/models", None, "models", parse)

    def json(self, system, public, *, stage, validator=lambda x: x, max_tokens=None):
        def parse(body):
            try:
                if not isinstance(body.get("model"), str):
                    raise SchemaError("Missing returned model")
                message = body["choices"][0]["message"]["content"]
                value = json.loads(message)
                if not isinstance(value, dict):
                    raise SchemaError("Completion JSON must be an object")
                return validator(value)
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                raise SchemaError("Invalid DeepSeek completion shape or JSON content") from exc
        payload = dict(model=self.config.deepseek_model,
                       messages=[dict(role="system", content=system),
                                 dict(role="user", content=json.dumps(public, ensure_ascii=False))],
                       thinking={"type": "disabled"}, response_format={"type": "json_object"},
                       temperature=0, stream=False, max_tokens=max_tokens or self.config.max_tokens)
        return self._request("/chat/completions", payload, stage, parse)


class JevClient(RestClient):
    backend = "jev"

    def models(self):
        def parse(body):
            if not isinstance(body.get("models"), list):
                raise SchemaError("Missing models array")
            return body["models"]
        return self._request("/v1/models", None, "models", parse)

    @staticmethod
    def parse_noul(body):
        try:
            answer = body["answers"]["needs_clarification"]
            value = answer["noul"]
            if (answer["type"] != "noul" or isinstance(value, bool)
                    or not isinstance(value, (int, float)) or not math.isfinite(value)
                    or not 0 <= value <= 1 or not isinstance(body.get("model"), str)):
                raise SchemaError("Noul must be a finite number in [0, 1], with a model")
            return float(value)
        except (KeyError, TypeError) as exc:
            raise SchemaError("Missing answers.needs_clarification.noul") from exc

    def noul(self, public, instructions, criteria=None, stage="gate"):
        question = dict(type="noul", instructions=instructions)
        if criteria:
            question["criteria"] = criteria
        return self._request("/v1/systemone", dict(model=self.config.jev_model, state=public,
                              questions={"needs_clarification": question}), stage, self.parse_noul)
