# UI Definition - <Unit name>

> Template. Copy to `docs/specs/ui/<unit>-<name>.md` in the target repo and
> fill in. See `docs/process/ui-definition.md` for the full process. A
> *unit* can be a whole surface or a behavior-bearing component inside a
> surface.

## Agent Index

- **Kind:** template
- **Use with:** `docs/process/ui-definition.md`
- **Copy to:** `docs/specs/ui/<unit>-<name>.md`
- **Purpose:** define the target shape of a UI unit.
- **Feeds:** `docs/templates/behavior-unit-spec.md`
- **Search terms:** UI unit definition, screen spec, component spec,
  widget spec, selector inventory, state matrix

- **Unit type:** screen | component | view | widget | command
- **Address:** <route / component path / view path / command invocation>
- **Implementation target:** <source file path(s), package, or planned path>
- **Parent unit(s):** <screen/view/command specs that compose this unit, or
  `none`>
- **Child unit(s):** <component/widget specs this unit composes, or `none`>
- **Shared unit:** yes | no
- **Design-system inputs:** <tokens, primitives, architecture docs used>
- **Prototype artifacts:** <Claude Design link/export, screenshot path, or
  `none`>
- **Approved variant:** <A | B | C | text sketch>

## User Goal

<The user's job in this unit. Keep this to one or two sentences.>

## Layout Regions

| Region ID | Name | Purpose | Contents |
|-----------|------|---------|----------|
| `<unit>-main` | <Main> | <Primary work area> | <Elements or groups> |

## Element Inventory

Every interactive element needs a stable selector, widget id, or command
arg name. Behavior capture uses these names in observable-output records.

### `<unit>-submit`

- **Label:** <Submit>
- **Role:** button
- **Selector / widget id / arg:** `data-testid="<unit>-submit"`
- **Component:** Button
- **State notes:** enabled when <condition>

## Composition Contract

Fill this in for shared components, widgets, and composed screens. Use
`none` for standalone units.

| Contract item | Owner | Details |
|---------------|-------|---------|
| Props / inputs | <parent or unit> | <state, data, permissions, configuration> |
| Slots / children | <parent or unit> | <regions the parent may fill> |
| Events / callbacks | <unit> | <events emitted to parent> |
| Selector namespace | <unit> | <prefix or naming rule> |
| Context-specific behavior | <parent or unit> | <what changes by parent context> |

## State Matrix

### Empty

- **Visible UI:** <what appears before data exists>
- **Disabled / hidden UI:** <what is unavailable>
- **Required message:** <copy or none>
- **Notes:** <notes>

### Loading

- **Visible UI:** <spinner/progress/skeleton>
- **Disabled / hidden UI:** <what is locked>
- **Required message:** <copy or none>
- **Notes:** <notes>

### Populated

- **Visible UI:** <normal working state>
- **Disabled / hidden UI:** <what remains unavailable>
- **Required message:** <copy or none>
- **Notes:** <notes>

### Error

- **Visible UI:** <error surface>
- **Disabled / hidden UI:** <what is blocked>
- **Required message:** <copy>
- **Notes:** <retry/recovery path>

### Disabled

- **Visible UI:** <disabled controls>
- **Disabled / hidden UI:** <blocked controls>
- **Required message:** <reason>
- **Notes:** <notes>

### Large Data

- **Visible UI:** <overflow, pagination, or virtualization behavior>
- **Disabled / hidden UI:** <none or listed>
- **Required message:** <copy or none>
- **Notes:** <performance notes>

## Interaction Candidates

These are not full behavior records yet. They are the UI triggers and
immediate responses that behavior capture will turn into records.

### `I-<UNIT>-001`

- **Trigger:** <click/type/key/invoke>
- **Preconditions:** <required state>
- **Immediate UI response:** <visible response>
- **Behavior record candidate:** `B-<UNIT>-001`

## Responsive / Accessibility

- **Keyboard path:** <tab order, shortcuts, command usage, or none>
- **Focus behavior:** <initial focus, focus after action, focus trap rules>
- **Screen reader labels:** <labels for icon-only or ambiguous controls>
- **Viewport behavior:** <desktop/mobile/TUI resize behavior>
- **Theme behavior:** <dark/light/high-contrast notes>

## Handoff To Behavior Capture

- **Behavior records to draft:** <B-... list or description>
- **Flow records to draft:** <F-... list or description>
- **Parent records that compose this unit:** <B-... list or `none`>
- **Shared baseline records:** <B-... list or `none`>
- **Context-specific records:** <B-... list or `none`>
- **Known regressions:** <issue/commit references or none>
- **Open questions:** <questions that must be resolved before behavior
  capture, or none>

<!-- Worked example fragment - delete when filling in:

### `home-upload-dropzone`

- Label: Upload scans
- Role: dropzone
- Selector: `data-testid="home-upload-dropzone"`
- Component: UploadDropzone
- State notes: empty and populated; disabled while job starts

### `home-start-job`

- Label: Start OCR
- Role: button
- Selector: `data-testid="home-start-job"`
- Component: Button.primary
- State notes: disabled until files are valid

### `I-HOME-001`

- Trigger: Drop a ZIP on `home-upload-dropzone`.
- Preconditions: no active job.
- Immediate UI response: file list appears; invalid files reject inline.
- Behavior record candidate: `B-HOME-001`.

### `I-HOME-002`

- Trigger: Click `home-start-job`.
- Preconditions: valid files selected.
- Immediate UI response: upload locks; progress route opens.
- Behavior record candidate: `B-HOME-002`.
-->
