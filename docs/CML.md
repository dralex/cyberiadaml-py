# The CyberiadaML Interface

`cyberiadaml_py.cml` gives the interface of the `CyberiadaML` module of libcyberiadamlpp-py
(1.0.9) in pure Python, over the core of this library. A program that reads or builds documents
without geometry runs on either:

    try:
        import CyberiadaML
    except ImportError:
        from cyberiadaml_py import cml as CyberiadaML

```
 consumers: hsmd_reader (hsm-dispatcher-py, hsm-to-python), cybersphere-agents check,
            hsm-console-viewer, hsm_robot_ros_generator, the editor polygon tools
        |  the binding's names, signatures, enums, exceptions, dump
        v
 cml/  Document / LocalDocument -------------------------------+
        |  decode()/open()                    encode()/save()   |
        v                                                      ^
 cml/reader.py   core model -> element tree     cml/writer.py   element tree -> core model
        |                                                      ^
        v                                                      |
 core/  read(strict)  - XML, Lapki dialect, checks     write()  - standard document, strict re-read
```

## Tiers

| tier | release | content | needed by |
|---|---|---|---|
| R | 1.7 | reading: `open`, `decode`, the element tree, every getter and query, meta, enums, constants, exceptions, the dump | the readers above |
| W | 1.7 | building: the `new_*` factories, `Action`, edits, copies, comment subjects, meta setters, `encode`, `save`, `save_as` | hsm-console-viewer examples, builders without layout |
| G | later | geometry: the Qt coordinates, bounding rects, `check_geometry`, the derived sizes of `geometry/ short`, the Arena frame, the dump's `bounding rect` | the editor closeness tool |
| — | — | layout (`reconstruct_geometry`, `update_geometry`), yEd formats, isomorphism of different machines, the Lapki writer | raise `NotImplementedException`; hsm-maker and ad-statistics keep the binding |

## Decisions

1. **The binding's behaviour wins** where it is observable — the element tree, the action
   texts, the dump. `cml` raises only where the binding's model cannot hold a standard
   document: several regions in a state, `fork`/`join`, a `do/` block, a guard on `entry`/
   `exit` (`CybMLException`, as the binding).
2. **Geometry formats.** R and W read and write `geometryFormatNone` and
   `geometryFormatCyberiada10` (the values of the file). `geometryFormatQt` stays the default
   of `open` and `decode`; until G it raises `NotImplementedException` for a document with
   geometry — never other coordinates silently.
3. **Exceptions** form the hierarchy of the C++ library under `CyberiadaML.Exception` (the
   binding registers them flat): `FileException`, `FormatException` > `XMLException`,
   `CybMLException` > `ActionException`, `MetainfoException`; `ParametersException` >
   `NotFoundException`; `AssertException`, `NotImplementedException`. The message keeps the
   binding's form (`Parameters Exception: <msg>`) and carries the core finding.
4. **Objects** are plain Python objects; a getter the binding documents as live returns the
   stored object, the copying ones return copies; `find_element_by_id` returns `None`.

## Reading

The core reads the document (permissive, or `strict=True`); `cml/reader.py` builds the tree:

| core | `cml` | rule |
|---|---|---|
| state machine | `StateMachine` | id, name (graph id when unnamed, D-8b); no formal name, no colour |
| state | `State`, `elementSimpleState` | `elementCompositeState` once it has a child (a comment too) |
| region | — | its children go into the state; its rect is the state's region rect; a second region raises |
| submachine state | `SubmachineState` | the reference; its points are its children |
| `initial`, `terminate` / `final` / `choice` | `Initial`, `Terminate` / `Final` / `Choice` | `Choice` has a rect |
| history, entry/exit point | `History`, `ConnectionPoint` | told apart by `ElementType` |
| comment | `Comment` | `elementComment` / `elementFormalComment`; `CGML_META` and `CGML_COMPONENT <id>` are formal comment children in document order |
| comment link | `CommentSubject` of its comment | element / name / data with the fragment; never a transition |
| transition | `Transition` of the state machine | after all vertices and comments, in document order; `transitionLocal` as the binding reads |

- **Order of children**: vertices and comments in document order, depth first, then the
  transitions of the machine.
- **Names** are right-trimmed; `has_name()` tells a present `dName` (even empty) from none;
  qualified names join the names below the machine with `::`.
- **Actions of a state**: one `Action` per block — `entry`/`exit` as `Action(actionEntry|
  actionExit, behavior)`, an event block as `Action(trigger, guard, behavior, propagation)`;
  the guard keeps its escapes as written (`a \[b\] c`), the behaviour its lines, right-trimmed;
  repeated `entry`/`exit` blocks are merged (permissive). A transition has one `Action`;
  `has_action()` ignores the propagation. `skip_empty_actions` drops the state actions without
  guard and behaviour.
- **Metainformation**: `standard_version`; `transition_order` and `event_propagation` are
  `…None` when absent; every other parameter is a string in file order; the `name` parameter
  is the document name. `get_meta_element()` is the `CGML_META` comment; its body is written
  again from the metainformation.
- **Ids** as the core reads them (dialect renames included); `simplify_ids` renumbers like the
  binding (`g0`, `n<k>`, `<parent>::n<k>`, `<src>-<tgt>#<k>`); `skip_meta_format` replaces the
  metainformation by the defaults.
- **Formats**: `formatDetect` gives `formatCyberiada10` for every `Cyberiada-GraphML-*`
  document, `format_str` the core label (`Cyberiada-GraphML-1.0` or `-Lapki`), or
  `-Arena` when the document has a `referenceGraphID` data key (its geometry needs tier G);
  a yEd document raises `NotImplementedException`.
- **Errors**: not well-formed XML → `XMLException`; a metadata finding → `MetainfoException`;
  any other refusing finding → `CybMLException`; a missing or unreadable file → `FileException`.

- **Lenient reading** keeps the standard findings, but refuses what the binding refuses in its
  non-strict mode: broken XML structure and keys, a missing or wrong `gFormat`, dangling ends,
  two initials, bad pivots and chunks, a missing or unparsable `CGML_META`, a bad propagation
  value, foreign tags (`LENIENT_REFUSED` in `cml/reader.py`, found on the conformance examples);
  an event name must be words, spaces and dots with one argument, and a state block needs `/`,
  as the binding's grammar wants. An undeclared extension data key is skipped; a trigger ending
  with `propagate`, `block` or `defer` (`TICK defer/`) gives that propagation, as in the C
  library.

### Differences from the binding

Checked with the 26 binding test scripts of tiers R and W (`tests/cml/binding/`), with
`tests/cml/binding-view.json` (the binding's dumps of the 131 examples) and with the consumers'
own tests run on both:

| | binding | `cml` |
|---|---|---|
| a Lapki component repaired by the dialect | the rest of the body as written | the body written from its parameters |
| `format_str` of a document | `-Lapki` by its own patterns | `-Lapki` when a dialect repair fired (not the legacy `transitionFirst`, repeated ids or parameters alone) |
| strict mode, `gFormat` not first | read | refused (the core checks it) |
| strict mode, a broken Lapki document | `MetainfoException` (the metadata is checked first) | `CybMLException` |
| a node with a vertex kind and a submachine reference | the submachine state | the vertex |
| a yEd document | read | `NotImplementedException` |
| writing a deferred event with behaviour, a deferred transition | `TICK/ defer` and the behaviour lines | `CybMLException`: 6.8 gives a deferred event no behaviour and no transition |

The consumers: hsm-dispatcher-py (31 scenarios, 39 diagrams), hsm-to-python, the
hsm_robot_ros_generator packages, `cybersphere check` give the same output on every Cyberiada
document; their yEd examples need the binding.

## Writing

`cml/writer.py` turns the tree into a core model and writes it with `core.write` (a strict
re-read). The `new_*` factories follow the binding: the overloads by the number and the type of
the arguments (two strings: id and name; one: the name), the ids `G<k>`, `n<k>`,
`<parent>::n<k>`, `<src>-<tgt>[#<k>]`, the `ParametersException` checks (no parent, empty
name, an id taken, a second initial or history of a kind, a bad transition end, a second
transition into a choice, entry/exit on a transition, an empty transition action, a guard on
entry/exit). `encode` and `save_as` write `formatCyberiada10`; `formatLapki` and the yEd
formats raise `NotImplementedException`; the yEd formats check their preconditions first
(`ParametersException`: one machine, geometry). The text is a standard document, not the
binding's bytes: documents are compared by the canonical dump; what the standard forbids is not
written (`CybMLException`). The options `round`, `check_initial`, `strict_actions` and
`skip_empty_behavior` act only with the geometry, as in the C++ library.

Copies and edits follow the C++ semantics: a copied subtree re-binds the comment subjects that
point inside it and keeps the others; `add_element` takes only an element created for that
parent (`AssertException`); `round()` truncates the coordinates; `update_metainfo_from_comment`
returns `False` (a stub in C++ too); `compare_actions` is a port of the C function;
`check_isomorphism` answers `smiIdentical` for equal machines and raises
`NotImplementedException` otherwise.

## The dump

`repr()` of every element, `Action`, `CommentSubject`, `Point`, `Rect` and `Polyline` follows
the C++ `dump_to_str`: `<Type>: {id: '<id>'[, name: '<n>'][, formal name: '<f>'] …}`, numbers
as `%g`, points `(x; y)`, rects `(x; y; w; h)`, polylines `[ … ]`, texts unescaped. The
document's `bounding rect` part comes with tier G.

## Classes

The names, the signatures and the overloads of the binding. Tier W unless marked R:

| class | content |
|---|---|
| module | R: the enums (`ElementType`, `ActionType`, `EventPropagation`, `TransitionType`, `DocumentFormat`, `DocumentGeometryFormat`, `CommentSubjectType`, `DocumentTransitionOrder`, `DocumentEventPropagation`, `DocumentGeometryDeclaration`) with their members at module level and their values, the `adiff*`/`smi*` ints, `QUALIFIED_NAME_SEPARATOR`, `__version__`, the exceptions, `is_legacy_yed_format`, `cleanup_library` (no-op) |
| `Point`, `Rect`, `Polyline` | R: the values and `repr`; W: setters, `round`, `Rect.expand`, `almost_equal` |
| `Action` | R: getters, `is_empty_transition`; W: constructors, `update`, `clear` |
| `CommentSubject` | R: getters; W: constructors, geometry setters |
| `DocumentMetainformation` | R: the fields, `get_string`, `get_geometry`; W: `set_string`, `remove_string`, `set_geometry` |
| `Element` | R: ids, names, formal names, qualified names, type, parent, index, children counts, `has_geometry`; W: setters, `copy` |
| `ElementCollection` | R: `get_children`, `get_element`, `first_element`, `element_index`, `get_vertexes`, `find_element_by_id`, `find_elements_by_type(s)`, `has_initial`, `get_geometry_rect`, colour; W: `add_element`, `add_first_element`, `remove_element`, `clear`, `rebind_subjects`, `update_geometry` |
| `State`, `SubmachineState` | R: actions, kind, `get_substates`, collapsed, region rect, reference; W: action edits, `set_collapsed`, `set_submachine_reference` |
| `StateMachine` | R: `get_comments`, `get_transitions`; W: the copy constructor, `check_isomorphism` of equal machines |
| vertices, `Choice`, `Comment`, `Transition` | R: the getters of the binding; W: constructors and updates, `add_subject`, `remove_subject`, `update_label` |
| `Document`, `LocalDocument` | R: `decode`, `open`, `get_meta`, `meta`, `get_meta_element`, `get_state_machines`, `get_parent_sm`, `get_geometry_format`, the file identity; W: the factories, `encode`, `save`, `save_as`, `reset`, `set_name`, `set_file`, `update_metainfo_from_comment`, the copy constructors |

The binding's lists are Python lists; the out-parameter forms of `check_isomorphism` are not
provided.
