"""Authenticated, encrypted PC jobs. Only ciphertext enters the public repository."""
import json
from cryptography.fernet import Fernet

ACTIONS = frozenset({"status", "report", "pair", "agent"})
MAX_JOB_SECONDS = 600


def seal_job(job, key):
    payload = json.dumps(job, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"id": str(job["id"]), "payload": Fernet(key).encrypt(payload).decode("ascii")}


def open_job(envelope, key, expected_chat, now):
    # The authenticated Fernet timestamp also limits lifetime on replay.
    raw = Fernet(key).decrypt_at_time(envelope["payload"].encode("ascii"), ttl=MAX_JOB_SECONDS, current_time=int(now))
    job = json.loads(raw)
    if not isinstance(job, dict) or str(job.get("id", "")) != str(envelope.get("id", "")):
        raise ValueError("invalid id")
    if str(job.get("chat_id", "")) != str(expected_chat):
        raise ValueError("wrong owner")
    if job.get("action") not in ACTIONS:
        raise ValueError("unknown action")
    created = job.get("created_at")
    expires = job.get("expires_at")
    if type(created) is not int or type(expires) is not int:
        raise ValueError("invalid times")
    if not (created <= now + 30 and created < expires <= created + MAX_JOB_SECONDS and now <= expires):
        raise ValueError("expired job")
    text = job.get("text", "")
    if not isinstance(text, str) or len(text) > 6000:
        raise ValueError("invalid text")
    return job
