# Third-party code and methods

Project integration code is MIT licensed. Dependency licenses remain those of their authors.

- Pi: https://github.com/earendil-works/pi, MIT, npm `@earendil-works/pi-coding-agent` 1.5.0. Provides the agent runtime, model access and TUI. Not original project work.
- gCastle: https://github.com/huawei-noah/trustworthyAI/tree/master/gcastle, dependency 1.0.3, Apache License 2.0. Provides SEM simulation, NOTEARS, GOLEM and DAG-GNN implementations. Retain its distributed license in installations. These algorithms are not original project work.
- Neural-GC: https://github.com/iancovert/Neural-GC, commit `c3263d40433aaf3acc94c27a0c1abf9b8e9fcedf`, MIT (Ian Covert, 2019). Vendored `models/cmlp.py` and `models/model_helper.py` live under `backend/brain_eval/vendor/neural_gc`; the original LICENSE is included. The only code edit is changing the model_helper import to a relative import. Provenance and hashes are saved beside the files. These lines are excluded from original-code counts.
- PyTorch, NumPy, SciPy, pandas, matplotlib, NetworkX, FastAPI and associated packages supply numerical and application infrastructure. See their installed package metadata for licenses.

The Granger adapter implements conditional linear regression with an F test and Bonferroni correction using NumPy/SciPy; it is not copied from Neural-GC. The evaluator's region-level SHD treats an isolated edge reversal as one operation and supports reciprocal directed graphs. It does not silently invoke gCastle's DAG metric on all graph types.

gCastle 1.0.3 uses NetworkX functions removed in NetworkX 3. The project supplies ndarray compatibility aliases inside disposable processes (`brain_eval/compat.py`) without modifying the installed package. This path was checked against the original PyPI wheel as well as the existing Conda environment.
