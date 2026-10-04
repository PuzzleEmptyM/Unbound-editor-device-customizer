# Windows community add-on 7.2

Implementation references for the Windows improvements discussed in [upstream issue #4](https://github.com/PuzzleEmptyM/Unbound-editor-device-customizer/issues/4).

## Use the prebuilt application

The community fork provides a **Windows preview** at [community-v7.2](https://github.com/lins58308/Unbound-editor-device-customizer/releases/tag/community-v7.2). Download `SpeedEditorCustomizer-Community-v7.2-Windows.zip`, extract it into a writable folder, and run `SpeedEditorCustomizer.exe`. Python is not required. On first launch, the application scans locally installed applications and creates its own configuration. Use the Applications tab to review automatic switching and templates; F1 opens the Traditional Chinese guide.

This is a community build, not an official upstream release. The ZIP contains no personal configuration or account data. Existing users should keep a backup of their own configuration before upgrading.

## Source scope

The `src` directory contains the ten 7.2 add-on modules. They implement consistent mouse bindings, precise pointer/scroll input, momentary common controls, extra-command editing, foreground-context reliability, and the glass interface/guide.

These modules were developed against an earlier extended binary. They refer to earlier extension modules that are **not part of current upstream main**. They are isolated here for review; checking out this branch and running upstream `main.py` does not activate these additions. The existing upstream build workflow does not build the community preview.

The supplied binary-addon builder requires Python 3.12 and a locally supplied verified v6 baseline executable:

```sh
python community/windows-7.2/build.py path/to/v6-baseline.exe path/to/new-output.exe
```

It checks the baseline hash, retains the original archive payloads and appends the addon loader. No baseline binary is committed here. Upstream source integration remains work to be reviewed, rather than a claim that these modules are already integrated.

## Validation

`validation.json` describes the prebuilt 7.2 binary: 107 runtime, 44 UI and 46 extra-editor checks; the native executable also completed its 107-check run and exited with code 0. Desktop operations included overlay click-through/unlock and saving an OBS extra command while switching rows. Physical Speed Editor hardware and every external application command have not been manually tested; automated tests replace HID/OS output. macOS is untested.

The portable pure-module checks can be run without Qt, hardware, or personal configuration:

```sh
python community/windows-7.2/tests/check_uniform_controls.py
python community/windows-7.2/tests/check_precision_input.py
```

The offline guide is `guide.zh-Hant.html`. Original project and authentication-algorithm credits remain in the repository README.
