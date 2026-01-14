**Issue 1**: `scripts/setup-test-env.sh` exits with an error if `~/Code/spec-kitty` is missing, but the WP edge case explicitly says this should be a warning (the directory is for reference only). Change this check to emit a warning and continue so the script still passes when the repo is missing.

**Issue 2**: The setup script only warns when spec-kitty is installed from somewhere other than `~/Code/spec-kitty`, yet the WP success criteria requires the environment to be configured with spec-kitty installed from source. Either fail the script when the install is not from `~/Code/spec-kitty` (preferred), or update the output to make it clear the environment is NOT ready and exit non-zero.

**Issue 3**: The uninstall guidance in the non-source install warning uses `pip uninstall spec-kitty`, but the project dependency and the check use `spec-kitty-cli`. Align the uninstall instruction with the actual package name so the fix path is correct.
