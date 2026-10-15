# cyberiadaml-py Interface Specification

The library has two interfaces over one core: the 1.x interface of the package root, kept for
its users, and the core interface `cyberiadaml_py.core`. The reasons and the data flow are in
`ARCHITECTURE.md`.

## The 1.x Interface

    from cyberiadaml_py import CGMLParser, CGMLBuilder
    from cyberiadaml_py.types.elements import CGMLElements

* `CGMLParser().parse_cgml(graphml: str) -> CGMLElements` - reads a document in the permissive
  mode, standard or Lapki dialect; raises `CGMLParserException` with the fatal findings.
* `CGMLBuilder().build(elements: CGMLElements) -> str` - writes a standard document; raises
  `CGMLBuilderException` when the elements break a MUST rule of the standard.

No other exception type leaves these calls.

### Types

`cyberiadaml_py.types.elements` — pydantic dataclasses, the names and fields of 1.4:

* `CGMLElements` - `state_machines: Dict[str, CGMLStateMachine]` by graph id, `format: str`,
  `keys: DefaultDict[str, List[CGMLKeyNode]]` by `for`, `functions: Dict[str, CGMLFunction]`;
* `CGMLStateMachine` - `name`, `platform`, `standard_version`, `meta: CGMLMeta`, `states`,
  `transitions`, `components`, `notes`, `initial_states`, `finals`, `choices`, `terminates`,
  `shallow_history`, `deep_history`, `unknown_vertexes` (dictionaries by element id);
* `CGMLMeta` - `id` of the metadata node, `values: Dict[str, str]` - all parameters;
* `CGMLState` - `name`, `actions` (behaviour text), `parent` (state id), `bounds`, `color`,
  `unknown_datanodes`;
* `CGMLTransition` - `id`, `source`, `target`, `actions` (behaviour text), `color`, `position`
  (polyline points), `label_position`, `unknown_datanodes`, `pivot`;
* `CGMLComponent` - `id`, `type`, `parameters: Dict[str, str]`;
* `CGMLNote` - `name`, `type` (`formal` | `informal`), `text`, `position`, `parent`,
  `unknown_datanodes`;
* `CGMLBaseVertex` and its kinds `CGMLInitialState`, `CGMLFinal`, `CGMLChoice`,
  `CGMLTerminate`, `CGMLShallowHistory`, `CGMLDeepHistory` - `type`, `data` (name), `position`,
  `parent`;
* `CGMLFunction`, `CGMLInput`, `CGMLOutput`, `CGMLBlock` - the `dFunction` graphs (D-9);
* `Point`, `Rectangle` (`types.common`);
* `CGMLDataNode`, `CGMLKeyNode` (`types.cgml_scheme`) - the `data` items and key
  declarations; the raw tree classes of that module (`CGML`, `CGMLGraph`, `CGMLNode`, …) stay
  importable but are no longer produced.

What 1.5 changes in their content:

| field | 1.4 | 1.5 |
|---|---|---|
| `meta`, `platform`, `standard_version` | the metadata node of the same graph; `platform` required | the document metadata over the machine parameters, on every machine; `platform` optional |
| `transitions` | comment links included | transitions only |
| `notes` | informal comments | all comments except `CGML_META` and components, with their `type` |
| `CGMLNote.position` | `Point`; a comment rect became a point; no geometry rejected | `Point`, `Rectangle` or `None` |
| `components` | name `CGML_COMPONENT`, `id/` in the body | name `CGML_COMPONENT <id>`; the old form read as dialect D-2 |
| `CGMLBaseVertex.data` | always `None` | the vertex name |
| `CGMLTransition.position` | read, never written | read and written |
| `format` | `gFormat` as read | `Cyberiada-GraphML-1.0` |

Fields planned for 1.6 (additive, all optional): the submachine reference, `collapsed` and
`formal_name` of states, typed `entry_points` / `exit_points`, the label rect and the source and
target points of transitions, `markup` of comments, `formal_name` of machines.

## The Core Interface

    from cyberiadaml_py import core

* `core.read(data: str | bytes, *, strict: bool = False) -> core.Document` - reads a
  document. Strict: no dialect repairs, any ERROR finding raises. Permissive: dialect repairs,
  only fatal findings raise. Raises `core.CGMLError`.
* `core.write(document: core.Document) -> str` - writes a standard document; raises
  `core.CGMLError` when the result breaks a MUST rule (the writer reads its output back in the
  strict mode).
* `core.dump(document: core.Document) -> str` - the canonical dump of the validator
  specification §7.

Constants:

* `FORMAT_STANDARD = "Cyberiada-GraphML-1.0"`, `FORMAT_LAPKI = "Cyberiada-GraphML-Lapki"`;
* `ERROR`, `WARNING`, `INFO` - the finding severities.

### Errors

* `CGMLError(Exception)` - `findings: list[Finding]`; the message is the first fatal or error
  finding.
* `Finding` - `rule`, `req` (`CGML-<clause>-<n>` or `LAPKI-D<n>`), `layer` (0 for the dialect
  pass, 1-4), `severity`, `message`, `line`, `column`, `path`.

### Model

Dataclasses with the field names of the reference validator (`cgmlval`), so the two stay
comparable. Every element has `id`, `elem` (its source element), `parent`, `line` and
`extensions: list[Extension]`.

* `Document` - `format` (the `gFormat` value after the repairs), `label` (`FORMAT_STANDARD` |
  `FORMAT_LAPKI`), `keys: list[KeyDecl]`, `meta_comment`, `meta_id`, `meta_params:
  list[Param]`, `meta_errors`, `geometry_mode`, `machines: list[StateMachine]`,
  `findings: list[Finding]`, `extension_graphs` (the dialect D-9 graphs); `param(name)`,
  `transition_order()`, `event_propagation()`, `markup_language()`;
* `StateMachine` - `name`, `formal_name`, `geometry: Rect | None`, `marker`, `children`,
  `transitions`, `links`, `params: list[Param]` (dialect D-1 only);
* `Region` - `name`, `formal_name`, `geometry`, `children`;
* `Node` - `name`, `formal_name`, `geometry`, `color`, the base of:
  * `State` - `data` (the behaviour text verbatim), `blocks: list[Block]`, `block_errors`,
    `regions: list[Region]`, `collapsed`;
  * `SubmachineState` - `ref`, `regions` (the one holding the entry/exit points);
  * `Vertex` - `kind` (the `dVertex` value);
  * `Comment` - `kind` (`formal` | `informal`), `body`, `markup`; `component()` returns
    `(id, type, params)` for a `CGML_COMPONENT <id>` comment or `None`;
* `Transition` - `source`, `target`, `data`, `blocks`, `block_errors`, `polyline:
  list[Point]`, `source_point`, `target_point`, `label_geometry: Point | Rect | None`, `color`;
* `CommentLink` - `source`, `target` (node or edge id), `pivot`, `chunk`, `polyline`,
  `source_point`, `target_point`;
* `Block` - `kind` (`entry` | `exit` | `do` | `event`), `trigger`, `param` (`propagate` |
  `block` | `defer`), `guard`, `behaviour` (the lines), `verbatim`;
* `Param` - `name`, `value`, `line`; `KeyDecl` - `id`, `for_kind`, `attr_name`, `attr_type`;
* `Extension` - `key`, `text`, `elem`;
* `Point(x, y)`, `Rect(x, y, width, height)` - floats.

`children` keeps the document order. `write` takes the structure from the containment, not from
the `parent` fields, which `read` fills for navigation.
