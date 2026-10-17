# The CyberiadaML interface tests

* `test_binding.py` runs the libcyberiadamlpp-py test scripts of the provided tiers (`binding/tests/`,
  copied as they are with their documents and expected outputs from the revision in
  `binding/REVISION`) with `cyberiadaml_py.cml` in place of `CyberiadaML`, in a scratch copy;
  a written document is compared with `NN-output.graphml` by the canonical dump;
* `test_writer.py` builds documents: the generated ids, the checks of the factories, the
  options and the refusals of `encode`, the copies, `save` and `save_as`;
* `test_view.py` reads every example of `tests/examples` with `cml` and compares the dumps with
  `binding-view.json`, the binding's dumps recorded by `tools/record_binding_view.py`; the known
  differences are listed in the test and in `docs/CML.md`.

Licences: the scripts and documents of `binding/` come from libcyberiadamlpp-py under the GNU
General Public License (version 3).
