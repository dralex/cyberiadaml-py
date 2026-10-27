# cyberiadaml-py project changelog

## Version 1.8.0 (unreleased)

Added:
- the EXT-FA rules of `cyberiadaml_py.core` (compat-tests testing spec 1.11, 2.9): a
  document with `type/ fa` in its metadata is a deterministic finite automaton diagram and
  `core.read(strict=True)`, `core.write` and the strict `cml` reader refuse it when it
  breaks the `CGML-FA-*` requirements; `core.alphabet` reads the `FA_INPUT`/`FA_OUTPUT`
  alphabet comments and their restricted regular expressions; the standard examples
  re-synced at compat-tests 374e6d0 (the `fa/` examples and the `X-FA-*` negatives).
- the geometry of `cyberiadaml_py.cml`: the Qt, Cyberiada and yEd coordinate formats on reading,
  `convert_geometry` and writing; the bounding rects, `check_geometry`, the sizes of the loose
  rects of `geometry/ short`; `reconstruct_geometry` and `update_geometry`, the layered layout -
  the results of the binding.
- `cyberiadaml_py.htgeom`: the port of libhtreegeom (the coordinate formats, the bounding rects,
  the layered layout and its update).
- the tests: the libcyberiadamlpp-py scripts of the geometry, the binding's geometry results on
  the examples.
- the Debian package `python3-cyberiadaml` (CMake + CPack, `ctest` runs the tests).
- `cml`: `Comment.update_subject`, `Comment.update_subject_geometry` and
  `Document.update_comment_subject`, a comment subject changed in place (libcyberiadamlpp-py
  1.0.9); the binding scripts from libcyberiadamlpp-py 88942fa.
- the layout and the update give the comment links their ends (libhtreegeom 1.3): the links to
  the elements and to the transitions both ends (off the arrow and the label), the links to the
  fragments the source point; a link to a choice ends anywhere on the border of its rhombus.

Changed:
- Python 3.8.1 or newer (was 3.10): the 1.x types without the `X | Y` unions and `TypeAlias`,
  the writers indent without `ElementTree.indent`, `save` without `write_text(newline=)`;
  Python 3.8 takes pydantic 2.10.
- the rounding of `round()` truncates and the `round` option of `encode` rounds the nodes with
  children and the transitions, as the C++ library does.

Fixed:
- the target point of a comment link to a transition is relative to the transition's source
  node (PNST 1044 9.1.1, libcyberiadaml 1.0.9).

## Version 1.7.0 (unreleased)

Added:
- `cyberiadaml_py.cml`: the interface of the `CyberiadaML` module (libcyberiadamlpp-py) in pure
  Python, over the core - reading (`open`, `decode`, the element tree, the queries, the dump),
  building (the `new_*` factories, `Action`, edits, copies, comment subjects) and writing
  (`encode`, `save`, `save_as`) of the documents in the Cyberiada format; the Qt geometry, the
  layout and the yEd formats raise `NotImplementedException` (`docs/CML.md`).
- the tests of the interface: the libcyberiadamlpp-py scripts of these tiers, the binding's
  dumps of the examples, the writer tests.

## Version 1.6.0 (unreleased)

Added:
- the 1.6 fields of the 1.x types, for the elements of the extension profiles: comment links
  (`CGMLStateMachine.links`, also to transitions), `entry_points` and `exit_points`, submachine
  states (`CGMLState.submachine`), regions (`CGMLState.regions`, the `region` of a child),
  `collapsed`, formal names, the `markup` and colour of comments, vertex colours, the machine
  `bounds`, label rects, the source and target points of transitions; the extension data of
  components, vertices, regions, machines and the metadata node.

Changed:
- `unknown_datanodes` keeps the extension keys only: the standard keys of the extension profiles
  have typed fields (the builder still maps them when a caller gives them as data);
- entry and exit points are no longer in `unknown_vertexes`;
- a transition with a `pivot` is written as a comment link.

Fixed:
- the `createdAt` check gives the same result in every Python version (3.10 took a timestamp
  with `Z` for an error).

## Version 1.5.0 (unreleased)

Added:
- `cyberiadaml_py.core`: the standard-compliant core (PNST 1044-2025) - `read()` in the strict
  or the permissive mode, `write()`, `dump()` (the canonical dump), findings with the
  requirement ids; ported from the `cgmlval` validator of cyberiadaml-compat-tests.
- the permissive reading of the pre-standard Lapki dialect (`LAPKI-D<n>` repairs).
- the documentation (`docs/`) and the tests of the conformance examples, the Lapki dialect
  corpus and the lapki-compiler contract.

Changed:
- the package metadata names the licence: LGPL-3.0-or-later.
- `CGMLParser` and `CGMLBuilder` work over the core; the 1.x types keep their names and fields.
- the reader accepts the standard documents: `platform` is optional, a comment may have no
  geometry (`CGMLNote.position` may be `None`), formal comments are notes, comment links are
  no longer transitions, every machine gets the document metadata.
- the builder writes standard documents: one metadata node, `CGML_COMPONENT <id>` components,
  the transition polylines, the comment kinds and rects; ids repeated in a later machine are
  written as `<machine id>::<id>`.
- an unnamed machine is named by its graph id.

Removed:
- the `xmltodict` dependency; the private `CGMLParser._split_graph`.

Fixed:
- duplicate edge ids no longer lose a transition.
