# cyberiadaml-py Architecture

The library reads and writes CyberiadaML-GraphML documents (PNST 1044-2025) in pure Python. Since
1.5 it is built around a standard-compliant core that depends on the Python standard library only;
the 1.x interface (`CGMLParser`, `CGMLBuilder`, `CGMLElements`) stays as a facade over the core, so
lapki-compiler and other 1.x users keep working. The core also reads the pre-standard Lapki dialect
(see `CyberiadaML-GraphML-1.0-LAPKI-DIALECT.md` of cyberiadaml-compat-tests).

```
       lapki-compiler, 1.x users                         compat driver, tools
                   |                                               |
                   | parse_cgml(text)                              | read(data)
                   | build(elements)                               | write(doc), dump(doc)
                   v                                               v
  cyberiadaml_parser.py, ..._builder.py           core/__init__.py
 +----------------------------------+            +----------------------------------+
 |  1.x facade                      | -- read -> |  core                            |
 |  CGMLParser, CGMLBuilder         | <- model - |  reader: xmlload, dialect,       |
 |  types/ (pydantic, 1.x names)    | -- write ->|    tagtree, model, checks        |
 |                                  |            |  writer, dump, findings, rules   |
 +----------------------------------+            +----------------------------------+
```

The core is a port of `cgmlval` (cyberiadaml-compat-tests), the reference validator of the
standard: the same layers, rules, requirement ids and canonical dump. It is a copy, not a
dependency — the library is LGPL-3 and pip-installable on its own; the conformance tests keep the
two in step (see `TESTING.md`).

## Reading

```
 xmlload.py          dialect.py          tagtree.py          model.py            checks_l3/l4.py
 +--------------+    +--------------+    +--------------+    +--------------+    +--------------+
 |  L1 XML parse|    |  D-1 ... D-9 |    |  L2 tag tree |    |  model build |    |  L3 values   |
 |  bytes > tree| -> |  non-strict  | -> |  walk        | -> |  Document    | -> |  L4 integrity|
 |  line numbers|    |  only        |    |              |    |              |    |              |
 +--------------+    +--------------+    +--------------+    +--------------+    +--------------+
         |                   |                   |                   |                   |
         +-------------------+-------------------+-------------------+-------------------+
                                                 | findings
                                                 v
                               Document.findings, or CGMLError
```

Every check reports a finding — rule name, requirement id (`CGML-<clause>-<n>` or
`LAPKI-D<n>`), layer, severity, message, line. The mode decides what stops reading:

| | strict | permissive (default) |
|---|---|---|
| dialect pass | off | on |
| ERROR finding | `CGMLError`, reading stops at its layer | kept in `Document.findings` |
| fatal finding | `CGMLError` | `CGMLError` |
| WARNING, INFO | kept | kept |

A finding is fatal when no model can be formed: a document that is not well-formed XML, a root
other than `graphml`, no state machine graph, an element without an id, a duplicate id the dialect
pass does not repair. Elements the permissive reader cannot place (a foreign tag, an edge to an
unknown node) are skipped and named in their finding. A document whose only graphs are the
function graphs the dialect pass took out (D-9) reads as an empty model with them.

The ids the dialect pass gives (D-7f, D-7a) map back to the ids as written in
`Document.original_ids`.

The document format label is `Cyberiada-GraphML-1.0`, or `Cyberiada-GraphML-Lapki` when a dialect
repair fired or the metadata has `lapkiVisual`.

## The document model

```
 Document --- format, label, keys[], meta_params[], findings[]
    |
    +-- StateMachine* --- id, name, formal_name, geometry, params, extensions
           |
           +-- children: State | SubmachineState | Vertex | Comment        (top region)
           |     State --- name, data, blocks[], geometry, color, collapsed
           |       +-- Region* --- id, name, formal_name, geometry, children
           |     SubmachineState --- ref, points region (EntryPoint/ExitPoint vertices)
           |     Vertex --- kind, name, geometry, color
           |     Comment --- kind (formal|informal), name, body, markup, geometry, color
           +-- transitions: Transition* --- source, target, data, blocks[], polyline,
           |                                source/target point, label geometry, color
           +-- links: CommentLink* --- source, target (node or edge), pivot, chunk
```

- every element keeps its parent, its source line and its `extensions` — the `data` items of
  declared non-standard keys, in document order, written back as they came;
- `data` keeps the behaviour text verbatim, `blocks` is its parse (§6.8: triggers, guards,
  `propagate`/`block`/`defer`, `entry`/`exit`/`do`, `else`); text that does not parse keeps its
  findings and an empty `blocks`;
- `meta_params` is the ordered parameter list of the document metadata; `StateMachine.params`
  holds the per-machine parameters of the Lapki dialect (D-1), never written by the standard
  writer;
- geometry is `Point` or `Rect` of floats, exactly as read; nothing is invented.

The model covers the whole standard from 1.5 on — it comes with the validator port. The stages of
the development plan concern the writer paths, the 1.x facade and the claimed profiles:

| stage | release | adds |
|---|---|---|
| 1 | 1.5.0 | CORE profile read and write; Lapki dialect; extension elements kept and written back |
| 2 | 1.6.0 | submachines + entry/exit points, collapsed, comment→transition links, full geometry, markup, formal names: writer rules, 1.x fields, all four profiles |
| 3 | 1.7.0 | `cyberiadaml_py.cml` — the libcyberiadamlpp-py interface over the same core |

## Writing

`core/writer.py` writes a model as a standard document:

- `gFormat` `Cyberiada-GraphML-1.0` first, then the document's own key declarations as they came
  and a declaration for every extension key in use without one; a model without declarations
  (built in code) gets those of appendix Б for the keys in use;
- one `graph` per machine with `edgedefault="directed"`; the metadata node first in the first
  machine and nowhere else; the edges of a machine as one block at its end (§5.8.2);
- the `data` of an element in the appendix А order (`dNote`, `dSubmachineState`, `dVertex` first
  where the standard requires it), extensions after them, child graphs last;
- region graph ids from the model; a region without one gets `<state id>::region`;
- geometry and text as in the model; text escaping by the XML serializer (§5.2).

The writer never repairs: `write()` reads its own output back in the strict mode, and a model
that breaks a MUST rule (e.g. a transition to a missing node) raises `CGMLError` with those
findings. `writer.render()` gives the text without the check — for the 1.x builder's documents of
function graphs only.

## The 1.x facade

`CGMLParser.parse_cgml` reads in permissive mode and fills the 1.x types from the model;
`CGMLBuilder.build` turns 1.x types into a model and writes it. Names and fields stay; what they
now carry:

| 1.x field | from the model |
|---|---|
| `CGMLElements.format` | `Cyberiada-GraphML-1.0` (the dialect label is a core notion) |
| `CGMLElements.keys` | declared keys by `for`, extension keys included |
| `CGMLElements.functions` | the `dFunction` graphs (D-9) |
| `CGMLStateMachine.meta.values`, `platform`, `standard_version` | the document metadata overlaid with the machine parameters (D-1) — every machine gets them |
| `CGMLStateMachine.name` | the machine name; an unnamed machine is named by its graph id (D-8b) |
| element and edge ids | as written, per machine: a dialect rename (D-7f, D-7a) is undone where the id is free in the machine |
| `CGMLStateMachine.states` | states and submachine states by id; `parent` is the enclosing state, `region` its region; `regions` of a state (1.6) |
| `CGMLState.actions`, `CGMLTransition.actions` | the behaviour text, trimmed as 1.4 did (lapki-compiler parses it itself) |
| `CGMLStateMachine.transitions` | transitions only; comment links in `links` (1.6) |
| `CGMLStateMachine.components` | `CGML_COMPONENT <id>` comments by node id: `id`, `type`, the other parameters |
| `CGMLStateMachine.notes` | the other comments, formal and informal; `position` a `Point`, a `Rectangle` or `None` |
| vertex dictionaries | by kind; `data` is the vertex name; entry/exit points in `entry_points` / `exit_points` (1.6) |
| `unknown_datanodes` | the `data` items the 1.x fields do not hold: the extension keys (1.5: also the standard keys of the extension profiles, typed in 1.6) |

`CGMLBuilder` writes the metadata once, from the first machine, and the comments with their own
kind; it maps the standard keys among `unknown_datanodes` back onto the core fields. 1.x ids are
per machine, the standard wants them unique in the document: a node id repeated in a later
machine is written as `<machine id>::<id>`, a repeated edge id as `<id>#<N>`. Function graphs,
outside the standard, are written after the state machines. Errors of both reach the caller as
`CGMLParserException` / `CGMLBuilderException`, never as a pydantic or XML library error.

## The CyberiadaML interface

```
 CyberiadaML-style program --> cml.Document / LocalDocument
                                  | decode/open            encode/save |
                                  v                                    ^
                         cml/reader.py: core model -> element tree     cml/writer.py
                                  ^             |                      ^
                         core.read(strict)      |   convert, layout    |  the file format
                                                v                      |
                         cml/drawing.py --> cml/bridge.py: element tree <-> htgeom trees
                                                |
                                                v
                         htgeom/: the formats, the bounding rects, the layered layout
```

`cml` is a second facade over the same core, with the names and the behaviour of the
libcyberiadamlpp-py binding — the element tree, the action texts, the dump, the geometry; see
`CML.md`. `htgeom` is a port of libhtreegeom: the coordinate formats and the layered layout of
the hierarchical trees, the same arithmetic in the same order.

## Code layout

```
cyberiadaml_py/
  __init__.py              1.x exports
  cyberiadaml_parser.py    CGMLParser — facade
  cyberiadaml_builder.py   CGMLBuilder — facade
  types/                   1.x types (pydantic dataclasses)
  core/
    __init__.py            read(), write(), dump(), CGMLError, the model classes
    findings.py rules.py requirements.py
    xmlload.py dialect.py tagtree.py model.py checks_l3.py checks_l4.py
    actions.py meta.py keys.py
    writer.py dump.py
  cml/                     the CyberiadaML interface (CML.md)
    __init__.py            the binding's names
    enums.py errors.py geometry.py actions.py
    elements.py document.py
    reader.py              core model -> element tree
    writer.py              element tree -> core model
    bridge.py              element tree <-> htgeom trees
    drawing.py             the formats, the layout, the import and the export
  htgeom/                  the geometry of the hierarchical trees (libhtreegeom port)
    types.py segment.py    the trees, the segment and rect crossing
    transform.py           the coordinate formats, the bounding rects, the attachments
    layout.py              the layered layout: P1-P10, the update
```

## Dependencies

The core uses the standard library only (`xml.parsers.expat`, `xml.etree.ElementTree`). The 1.x
types keep `pydantic`; `xmltodict` is no longer used. Python 3.10 or newer.

## Licences

The library is distributed under the LGPL-3 (`LICENSE`), its documentation under the GFDL 1.3.
The core is a port of `cgmlval`, which cyberiadaml-compat-tests distributes under the GPL-3; its
author contributes the port to this library under the LGPL-3. `htgeom` is a port of
libhtreegeom (LGPL-3, the same author). The test examples
(`tests/examples/`) keep the licences of their sources, named in their README files; they are
not part of the package.

## Testing

The test layers, the snapshots of the conformance and dialect corpora and the 1.x contract tests
are described in `TESTING.md`.
