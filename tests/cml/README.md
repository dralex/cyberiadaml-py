# The CyberiadaML interface tests

* `test_binding.py` runs the libcyberiadamlpp-py test scripts of the provided tiers (`binding/tests/`,
  copied as they are with their documents and expected outputs from the revision in
  `binding/REVISION`) with `cyberiadaml_py.cml` in place of `CyberiadaML`, in a scratch copy;
  a written document is compared with `NN-output.graphml` by the canonical dump;
* `test_writer.py` builds documents: the generated ids, the checks of the factories, the
  options and the refusals of `encode`, the copies, `save` and `save_as`;
* `test_layout.py` runs the geometry scenarios of `tools/record_binding_layout.py` on every
  example (read in the Qt format, saved rounded, laid out, laid out after an edit, updated as
  drawn) and compares them with `binding-layout.json`, the binding's results;
* `test_arrange.py` checks the arrange of the htgeom port as the libhtreegeom tests 54-58 do,
  and the examples arranged as drawn against `binding-arrange.json`, recorded with
  `tools/record_binding_layout.py --arrange` by the binding of libcyberiadamlpp 1.1; a document
  whose full layout the port does not give as that binding (the comment layout of libhtreegeom
  1.3), or whose drawn comments take part in the arrange, is skipped;
* `test_choice.py` checks the choice of the htgeom port as the libhtreegeom tests 59 and 60 do:
  a small square, the transitions at the tips of its rhombus;
* `test_links.py` checks the comment link ends of the htgeom port (the foot on a commented
  transition, beside its label, the fragment links, the stored ends kept) as the libhtreegeom
  tests 49 and 50 do;
* `test_view.py` reads every example of `tests/examples` with `cml` and compares the dumps with
  `binding-view.json`, the binding's dumps recorded by `tools/record_binding_view.py`; the known
  differences are listed in the test and in `docs/CML.md`.

Licences: the scripts and documents of `binding/` come from libcyberiadamlpp-py under the GNU
General Public License (version 3).
