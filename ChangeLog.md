# cyberiadaml-py project changelog

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
