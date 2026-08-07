## 5. Study 2: the locked design

{{val:n_strip}} electrodes per strip, {{val:span}} cm span, {{val:channels}} channels,
{{val:snr}} dB, {{val:freq_khz}} kHz.

{{table:design_motion}}

{{fig:figs_design/d2_motion.png|Performance against motion at the locked design.}}

### 5.1 The multi-event screening rule

VCUG captures one or two forced voids. A passive wearable observes many, and detection compounds.
Simulated as {{val:n_subjects}} children with {{val:k_events}} events each, **anatomy and placement
held fixed per child** so correlated failure would show rather than average away. Per event:
{{val:per_event_sens}} sensitivity at a {{val:per_event_fp}} false-positive rate.

{{table:multievent}}

{{fig:figs_design/d4_multievent.png|Sensitivity and specificity reported separately, with the chance floor.}}

> [!NOTE]
> The coin-flip column exists because an earlier version of this metric pooled healthy and refluxing children and counted a correct negative as a hit. Its chance floor was 89%, *above* the ~80% VCUG line it was being compared against, so a coin-flip detector would have appeared to beat VCUG.

{{methods:design}}
