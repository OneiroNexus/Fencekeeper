# Verification and packaging

The methods paper and original evidence files describe the historical run.
GitHub Actions runs fresh checks on the staging commit and retains receipts
for each environment.

```sh
python tools/validate.py --output new-validation
python tools/check_packaging.py --zipapp dist/fencekeeper-0.1.0.pyz --output new-packaging.json
```

On Windows, add `--allow-windows-symlink-skip` to the validation command to account for
unavailable symbolic-link privileges.
The receipt records any exceptions. The default verifier and Linux CI require
all unit tests to run. Fixtures are synthetic and serve as regression cases.
