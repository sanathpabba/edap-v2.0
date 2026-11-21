"""Secrets come from Azure Key Vault (az login required). Never hard-code or print values."""
import subprocess

KV = "edap-kv-b777d5"
_cache = {}


def get(name):
    if name not in _cache:
        _cache[name] = subprocess.check_output(
            ["az", "keyvault", "secret", "show", "--vault-name", KV, "--name", name, "--query", "value", "-o", "tsv"],
            text=True).strip()
    return _cache[name]
